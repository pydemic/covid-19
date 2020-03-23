import datetime

import numpy as np
import pandas as pd

from covid.types import delegate, CachedProperty
from .model import Model
from .plot import RSEICHAPlot
from ..data import covid_mean_mortality
from ..utils import fmt, pc, pm


class RSEICHA(Model):
    """
    SEICHA model for epidemics.

    This model is a SEIR variant that better tracks the evolution of cases and
    variants through the health system. This is useful to investigate the capacity
    of a health system to respond to epidemic outbreaks such as COVID-19.

    Time units are measured in days and number of cases can be expressed either
    a count or a fraction, often normalized to one.
    """

    # Class configuration
    columns = [
        'Recovered',
        'Fatalities',
        'Susceptible',
        'Exposed',
        'Infected',
        'Critical',
        'Hospitalized',
        'Asymptomatic',
    ]
    RECOVERED, FATALITIES, SUSCEPTIBLE, EXPOSED, INFECTED, CRITICAL, \
    HOSPITALIZED, ASYMPTOMATIC = range(8)
    plot_class = RSEICHAPlot
    region = None
    year = 2020

    # Initial state
    x0 = [0.0, 0.0, 209.3e6, 1000, 0.0, 0.0, 0.0, 0.0]
    total_fatalities = 0.0
    hospitalization_days = 0.0
    icu_days = 0.0
    peak_hospitalization_demand = 0.0
    peak_icu_demand = 0.0
    hospital_limit_date = delegate('start_date')
    icu_limit_date = delegate('start_date')
    hospital_limit_time = 0.0
    icu_limit_time = 0.0

    # Parameters
    kappa = 14.65 / 1000 / 365.25 * 0
    mu = 6.08 / 1000 / 365.25 * 0
    sigma = 1 / 5.0
    rho_a = 0.4
    R0 = 2.74

    icu_rate = 0.23
    icu_occupancy = 0.8
    hospital_rate = 2.3
    hospital_occupancy = 0.8

    @CachedProperty
    def icu_capacity(self):
        return self.icu_rate * self.population / 1000 * (1 - self.icu_occupancy)

    @CachedProperty
    def hospital_capacity(self):
        return self.hospital_rate * self.population / 1000 * (1 - self.hospital_occupancy)

    @property
    def population(self):
        if self.data.shape[0]:
            return self.data.iloc[-1].sum() - self.total_fatalities
        else:
            return sum(self.x0) - self.total_fatalities

    prob_symptomatic = 0.9
    prob_hospitalization = 0.18
    prob_icu = 0.05 / prob_hospitalization
    prob_fatality = 0.015 / prob_icu / prob_hospitalization
    prob_no_hospitalization_fatality = 0.25
    prob_no_icu_fatality = 1.00

    gamma_a = 1 / 1.61
    gamma_i = 1 / 1.61
    gamma_h = 1 / 3.3
    gamma_c = 1 / 17.5

    gamma_hr = gamma_h
    gamma_cr = gamma_c

    beta = R0 * gamma_i * 1 / prob_symptomatic

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.region is not None:
            self.prob_hospitalization, self.prob_icu, self.prob_fatality = \
                covid_mean_mortality(
                    self.region, self.year)
        self._watching = {}

    def diff(self, x, t):
        r, f, s, e, i, c, h, a = x

        mu = self.mu
        sigma = self.sigma

        p_s = self.prob_symptomatic
        p_h = self.prob_hospitalization
        p_c = self.prob_icu
        p_f = self.prob_fatality
        p_hr = self.prob_no_hospitalization_fatality
        p_cr = self.prob_no_icu_fatality

        gamma_a = self.gamma_a
        gamma_i = self.gamma_i
        gamma_h = self.gamma_h
        gamma_c = self.gamma_c
        gamma_hr = self.gamma_hr
        gamma_cr = self.gamma_cr

        # beta = (self.R0 * 2 * np.exp(-t/30) + 1) * gamma_i
        beta = self.R0 * gamma_i

        n = r + s + e + i + c + h + a
        infections = beta * (i + self.rho_a * a) / n * s

        h_extra = max(0, h - self.hospital_capacity)
        c_extra = max(0, c - self.icu_capacity)
        h_ = min(h, self.hospital_capacity)
        c_ = min(c, self.icu_capacity)

        ds = self.kappa * n - infections - mu * s
        de = infections - (1.0 / p_s) * sigma * e - mu * e
        da = (1 - p_s) / p_s * sigma * e - gamma_a * a - mu * a
        di = sigma * e - gamma_i * i - mu * i
        dh = p_h * gamma_i * i \
             - gamma_h * h_ \
             - p_c * gamma_h * h_extra \
             - gamma_hr * h_extra \
             - mu * h
        dc = p_c * gamma_h * h \
             - gamma_c * c_ \
             - gamma_cr * c_extra \
             - mu * c
        dr = gamma_a * a \
             + (1 - p_h) * gamma_i * i \
             + (1 - p_c) * gamma_h * h_ \
             + (1 - p_hr) * gamma_hr * h_extra \
             + (1 - p_f) * gamma_c * c_ \
             + (1 - p_cr) * gamma_cr * c_extra \
             - mu * r
        df = p_f * gamma_c * c_ + p_hr * gamma_hr * h_extra + p_cr * gamma_cr * c_extra

        return np.array((dr, df, ds, de, di, dc, dh, da))

    def get_convergence_function(self):
        N = None
        x0 = None
        start = True

        if self.kappa != 0 or self.mu != 0:
            raise NotImplementedError

        def fn(x, x_, t, dt):
            nonlocal N, x0, start
            N = x.sum() if N is None else N

            if start:
                x0 = x if x0 is None else x0
                if np.abs(x_ - x0).mean() >= N * 1e-3:
                    start = False
                return False
            else:
                return (np.abs(x_ - x) < N * 1e-6).all()

        return fn

    def get_watcher_function(self):
        t_h = float('inf')
        t_c = float('inf')

        self._watching = w = {
            'hospital_limit_time': t_h,
            'icu_limit_time': t_c,
        }

        def watch(x, v, t, dt):
            nonlocal t_h, t_c

            h = np.sum(x[self.HOSPITALIZED])
            c = np.sum(x[self.CRITICAL])
            if h >= self.hospital_capacity:
                t_h = min(t_h, t)
            if c >= self.icu_capacity:
                t_c = min(t_c, t)

            w['hospital_limit_time'] = t_h
            w['icu_limit_time'] = t_c

        return watch

    def _run_post_process(self):
        def advance(t):
            if np.isinf(t):
                return None
            return self.start_date + datetime.timedelta(int(t))

        # Compartments
        h = self['hospitalized']
        c = self['critical']
        r = self['recovered']
        w = self._watching

        # Healthcare statistics
        self.total_fatalities = self['fatalities'].max()
        self.peak_hospitalization_demand = h.max()
        self.peak_icu_demand = c.max()
        self.hospitalization_days = (h * self.dt).sum()
        self.icu_days = (c * self.dt).sum()
        self.hospital_limit_time = w['hospital_limit_time']
        self.icu_limit_time = w['icu_limit_time']
        self.hospital_limit_date = advance(self.hospital_limit_time)
        self.icu_limit_date = advance(self.icu_limit_time)

        # Epidemiology
        self.recovered = r.iloc[-1]

    def summary(self):
        sym_name = type(self).__name__
        return '\n\n'.join([
            f"\nSIMULATION RESULTS ({sym_name})",
            self.summary_demography(),
            self.summary_epidemiology(),
            self.summary_healthcare(),
            self.summary_simulation(),
        ])

    def summary_demography(self):
        N = self.data.iloc[-1].sum()
        N0 = self.data.iloc[0].sum()

        return f"""Demography
- Total population   : {fmt(N0)}
- Recovered          : {fmt(self.recovered)} ({pc(self.recovered / N0)})
- Fatalities (total) : {fmt(self.total_fatalities)} ({pc(self.total_fatalities / N)})
- Infected (max)     :
- Exposed (max)      : 
- Asymptomatic (max) :
        """

    def summary_epidemiology(self):
        return f"""Epidemiology
- R0
- IFR
- CFR
"""

    def summary_healthcare(self):
        N = self.data.iloc[-1].sum()

        t_hf = self.hospital_limit_time
        dt_hf = self.hospital_limit_date
        t_cf = self.icu_limit_time
        dt_cf = self.icu_limit_date

        h_demand = self.peak_hospitalization_demand
        c_demand = self.peak_icu_demand
        return f"""Healthcare parameters
- Hosp. days         : {fmt(int(self.hospitalization_days))}
- ICU days           : {fmt(int(self.icu_days))}
- Peak hosp. demand  : {fmt(h_demand)} ({pm(h_demand / N)})
- Peak ICU demand    : {fmt(c_demand)} ({pm(c_demand / N)})
- Hosp. collapse day : {fmt(t_hf)} days ({dt_hf})
- ICU collapse day   : {fmt(t_cf)} days ({dt_cf})
"""

    def summary_simulation(self):
        N = self.data.iloc[-1].sum()
        fluctuation = self.data.sum(1).std()

        return f"""Invariants
- Sum of compartments: {fmt(N)} ({pc(fluctuation / N)})
"""

    #
    # Column access
    #
    def _get_column(self, col, df):
        return df[col]

    def get_data_total(self, df):
        return df.sum(1)

    def get_data_fatalities(self, df):
        return self._get_column('Fatalities', df)

    def get_data_fatalities_final(self, df):
        return self.get_data_fatalities(df).iloc[-1]

    def get_data_recovered(self, df):
        return self._get_column('Recovered', df)

    def get_data_recovered_final(self, df):
        return self.get_data_recovered(df).iloc[-1]

    def get_data_susceptible(self, df):
        return self._get_column('Susceptible', df)

    def get_data_exposed(self, df):
        return self._get_column('Exposed', df)

    def get_data_infected(self, df):
        return self._get_column('Infected', df)

    def get_data_critical(self, df):
        return self._get_column('Critical', df)

    def get_data_icu(self, df):
        xs = self.get_data_critical(df)
        max_icu = self.icu_capacity
        data = np.data.where(xs > max_icu, max_icu, xs)
        return pd.Series(data, index=xs.index)

    def get_data_critical_demand(self, df):
        return self.get_data_critical(df).max()

    def get_data_hospitalized(self, df):
        return self._get_column('Hospitalized', df)

    def get_data_hospitalized_demand(self, df):
        return self.get_data_hospitalized(df).max()

    def get_data_asymptomatic(self, df):
        return self._get_column('Asymptomatic', df)

    #
    # Track interesting points in the simulation
    #
    def has_burst(self, times, xs):
        if xs[-1, self.EXPOSED] >= xs[-2, self.EXPOSED]:
            return False
        i = xs[:, self.EXPOSED].argmax()
        return len(xs) > 2 * i


if __name__ == '__main__':
    m = RSEICHA.main(region='Brazil')
