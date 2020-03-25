import datetime

import numpy as np
import pandas as pd

from .model import Model
from .plot import RSEICHAPlot
from ..region import as_region
from ..types import delegate, cached
from ..utils import fmt, pc, pm

identity = lambda x: x


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
    _dedup_factor = 1.0
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
    OPTIONS = {
        'seed:int': 'Initial infected population',
        'region:str': 'Country/city used to infer demographic and epidemiological '
                      'parameters',
        'R0': 'Basic reproducibility number',
        'rho': 'Ratio in which asymptomatic infect other people',
        'prob_symptomatic': 'Probability of developing symptoms',
        'hospital_prioritization': 'Fraction of how much we can reduce demand on '
                                   'healthcare system to allocate it to the COVID '
                                   'struggle',
    }
    plot_class = RSEICHAPlot
    region = None
    ref_year = 2020

    # Epidemiological parameters
    sigma = 1 / 5.0
    R0 = 2.74
    rho = 0.4
    prob_symptomatic = 0.14

    gamma_i = 1 / 1.61
    gamma_a = gamma_i
    gamma_h = 1 / 3.3
    gamma_c = 1 / 17.5
    gamma_hr = gamma_h
    gamma_cr = gamma_c

    # Clinical parameters
    prob_hospitalization = 0.18
    prob_icu = 0.05 / prob_hospitalization
    prob_fatality = 0.015 / prob_icu / prob_hospitalization
    prob_no_hospitalization_fatality = 0.25
    prob_no_icu_fatality = 1.00

    # Demography
    vital_dynamics = False
    kappa = 14.65 / 1000 / 365.25
    mu = 6.08 / 1000 / 365.25
    initial_population = None

    # Healthcare statistics
    icu_beds_pm = 0.23
    icu_occupancy_rate = 0.8
    hospital_beds_pm = 2.3
    hospital_occupancy_rate = 0.8
    hospital_prioritization = 0.15
    icu_total_capacity = cached(lambda x: x.icu_beds_pm * x.population / 1000)
    hospital_total_capacity = cached(lambda x: x.hospital_beds_pm * x.population / 1000)

    # Initial state
    seed = 1
    fatalities = 0.0
    hospitalization_days = 0.0
    icu_days = 0.0
    peak_hospitalization_demand = 0.0
    peak_icu_demand = 0.0
    hospital_limit_date = delegate('start_date')
    icu_limit_date = delegate('start_date')
    hospital_limit_time = 0.0
    icu_limit_time = 0.0

    @cached
    def icu_capacity(self):
        rate = 1 - self.icu_occupancy_rate * (1 - self.hospital_prioritization)
        return self.icu_total_capacity * rate

    @cached
    def hospital_capacity(self):
        rate = 1 - self.hospital_occupancy_rate * (1 - self.hospital_prioritization)
        return self.hospital_total_capacity * rate

    @property
    def population(self):
        if self.data.shape[0]:
            return self.data.iloc[-1].sum() * self._dedup_factor - self.fatalities
        else:
            return sum(self.x0) - self.fatalities

    def __init__(self, *args, r0=None, **kwargs):
        if r0:
            kwargs['R0'] = r0
        super().__init__(*args, **kwargs)
        self._watching = {}

        def set_(attr, value):
            x = kwargs.get(attr, value)
            setattr(self, attr, x)
            return x

        # Load data from from region
        if self.region is not None:
            self.region = region = as_region(self.region)

            # Mortality statistics
            p_hospitalization = region.prob_hospitalization / self.prob_symptomatic
            set_('prob_hospitalization', min(1.0, p_hospitalization))
            set_('prob_icu', region.prob_icu)
            set_('prob_fatality', region.prob_fatality)

            # Initial population
            if self.initial_population is None:
                set_('initial_population', region.population_size)

            # Healthcare statistics
            set_('icu_beds_pm', region.icu_beds_pm)
            set_('icu_occupancy_rate', region.icu_occupancy_rate)
            set_('hospital_beds_pm', region.hospital_beds_pm)
            set_('hospital_occupancy_rate', region.hospital_occupancy_rate)

            # R0 via contact matrix
            ...

            # Vital dynamics
            ...

        # Fix population and seed
        if self.initial_population is None:
            self.initial_population = 1.0
            self.seed = 0.01 if self.seed >= 1.0 else self.seed

        # Initial state
        self.x0 = [
            0.0,  # recovered
            self.fatalities,
            self.initial_population - self.seed * (1 + 1 / self.prob_symptomatic),
            self.seed / self.prob_symptomatic,
            self.seed,
            0.0,  # critical,
            0.0,  # hospitalized,
            0.0,  # asymptotic,
        ]
        self.x0 = np.array(self.x0)
        self._mu = self.mu if self.vital_dynamics else 0.0

    def diff(self, x, t):
        r, f, s, e, i, c, h, a = x
        n = r + s + e + i + c + h + a
        beta = self.R0 * self.gamma_i / (1 - (1 - self.rho) * self.prob_symptomatic)
        hplus = max(0, h - self.hospital_capacity)
        hminus = min(h, self.hospital_capacity)
        cplus = max(0, c - self.icu_capacity)
        cminus = min(c, self.icu_capacity)

        lambd = beta * (i + self.rho * a) / n
        ds = self.diff_s(s, n, lambd, t)
        de = self.diff_e(s, e, lambd, t)
        da = self.diff_a(e, a, t)
        di = self.diff_i(e, i, t)
        dh = self.diff_h(i, hminus, hplus, t)
        dc = self.diff_c(h, cminus, cplus, t)
        dr = self.diff_r(a, i, hminus, hplus, cminus, cplus, r, t)
        df = self.diff_f(hplus, cminus, cplus, t)

        return np.array((dr, df, ds, de, di, dc, dh, da))

    def lambd(self, i, a, t):
        pass

    def diff_s(self, s, n, lambd, t):
        if self.vital_dynamics:
            return self.kappa * n - lambd * s - self.mu * s
        else:
            return - lambd * s

    def diff_e(self, s, e, lambd, t):
        p_s = self.prob_symptomatic
        return lambd * s - (1.0 / p_s) * self.sigma * e - self._mu * e

    def diff_i(self, e, i, t):
        return self.sigma * e - self.gamma_i * i - self._mu * i

    def diff_c(self, h, cminus, cplus, t):
        c = cminus + cplus
        return (self.prob_icu * self.gamma_h * h
                - self.gamma_c * cminus
                - self.gamma_cr * cplus
                - self._mu * c)

    def diff_h(self, i, hminus, hplus, t):
        h = hminus + hplus
        return (self.prob_hospitalization * self.gamma_i * i
                - self.gamma_h * hminus
                - self.prob_icu * self.gamma_h * hplus
                - self.gamma_hr * hplus
                - self._mu * h)

    def diff_a(self, e, a, t):
        p_s = self.prob_symptomatic
        return (1 - p_s) / p_s * self.sigma * e - self.gamma_a * a - self._mu * a

    def diff_r(self, a, i, hminus, hplus, cminus, cplus, r, t):
        return (self.gamma_a * a
                + (1 - self.prob_hospitalization) * self.gamma_i * i
                + (1 - self.prob_icu) * self.gamma_h * hminus
                + (1 - self.prob_no_hospitalization_fatality) * self.gamma_hr * hplus
                + (1 - self.prob_fatality) * self.gamma_c * cminus
                + (1 - self.prob_no_icu_fatality) * self.gamma_cr * cplus
                - self._mu * r)

    def diff_f(self, hplus, cminus, cplus, t):
        return (self.prob_fatality * self.gamma_c * cminus
                + self.prob_no_hospitalization_fatality * self.gamma_hr * hplus
                + self.prob_no_icu_fatality * self.gamma_cr * cplus)

    def get_convergence_function(self):
        N = None
        x0 = None
        start = True

        if self.vital_dynamics and (self.kappa != 0 or self.mu != 0):
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
        self.susceptible = self['recovered'].iloc[-1]
        self.fatalities = self['fatalities'].iloc[-1]

        sigma_eff = self.sigma / self.prob_symptomatic
        self.total_exposed = self.integral(self['exposed']) * sigma_eff
        self.total_infected = self.integral(self['infected']) * self.gamma_i
        self.total_asymptomatic = self.integral(self['asymptomatic']) * self.gamma_a
        self.total_hospitalized = self.integral(self['hospitalized']) * self.gamma_h
        self.total_critical = self.integral(self['critical']) * self.gamma_c

    def summary(self):
        sym_name = type(self).__name__
        return '\n\n'.join([
            f"\nSIMULATION PARAMETERS ({sym_name})",
            self.summary_parameters(),
            f"SIMULATION RESULTS ({sym_name})",
            self.summary_demography(),
            self.summary_epidemiology(),
            self.summary_healthcare(),
            self.summary_simulation(),
        ])

    def summary_parameters(self):
        return f"""Parameters
- R0                : {fmt(self.R0)}
- P(is symptomatic) : {pc(self.prob_symptomatic)}
"""

    def summary_demography(self):
        N0 = self.initial_population
        N = self.population + self.fatalities
        p_asympt = self.total_asymptomatic / N

        return f"""Demography
- Total population   : {fmt(N0)}
- Recovered          : {fmt(int(self.recovered))} ({pc(self.recovered / N)})
- Fatalities (total) : {fmt(int(self.fatalities))} ({pc(self.fatalities / N)})
- Infected (max)     : {fmt(int(self.total_infected))} ({pc(self.total_infected / N)})
- Asymptomatic (max) : {fmt(int(self.total_asymptomatic))} ({pc(p_asympt)})
- Exposed (max)      : {fmt(int(self.total_exposed))} ({pc(self.total_exposed / N)})
        """

    def summary_epidemiology(self):
        return f"""Epidemiology
- R0   : {self.R0}
- IFR  : {pc(self.fatalities / self.total_exposed)}
- CFR  : {pc(self.fatalities / self.total_infected)}
- HFR  : {pc(self.fatalities / self.total_hospitalized)}
- HCFR : {pc(self.fatalities / self.total_critical)}
"""

    def summary_healthcare(self):
        N = self.population

        t_hf = self.hospital_limit_time
        dt_hf = self.hospital_limit_date
        t_cf = self.icu_limit_time
        dt_cf = self.icu_limit_date

        h_demand = self.peak_hospitalization_demand
        c_demand = self.peak_icu_demand
        icu_overload = self.peak_icu_demand / self.icu_capacity * (
                1 - self.icu_occupancy_rate)
        h_overload = self.peak_hospitalization_demand / self.hospital_capacity * (
                1 - self.hospital_occupancy_rate)

        return f"""Healthcare parameters
- Hosp. days         : {fmt(int(self.hospitalization_days))}
- ICU days           : {fmt(int(self.icu_days))}
- Peak hosp. demand  : {fmt(int(h_demand))} ({pm(h_demand / N)})
    x surge capacity : {fmt(self.peak_hospitalization_demand / self.hospital_capacity)}
    x total          : {fmt(h_overload)}
- Peak ICU demand    : {fmt(int(c_demand))} ({pm(c_demand / N)})
    x surge capacity : {fmt(self.peak_icu_demand / self.icu_capacity)}
    x total          : {fmt(icu_overload)}
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

    #
    # Statistics
    #
    def health_resources(self, translate=identity):
        _ = translate
        columns = [_('Name'), _('Items/day'), _('Total')]
        N = int(self.hospitalization_days + self.icu_days)
        return pd.DataFrame([
            ['Mask', 25, 25 * N],
            ['Mask N95', 1, N],
            ['Avental impermeável', 25, 25 * N],
            ['Glove', 50, 50 * N],
            ['Faceshield', 1, N],
        ], columns=columns)


if __name__ == '__main__':
    m = RSEICHA.main()
