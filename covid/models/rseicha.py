import numpy as np

from .model import Model
from ..data import covid_mean_mortality


class RSeicha(Model):
    """
    RF_SEICHA model for epidemics.

    This model is a SEIR variant that better tracks the evolution of cases and
    variants through the health system. This is useful to investigate the capacity
    of a health system to respond to epidemic outbreaks such as COVID-19.

    Time units are measured in days and number of cases can be expressed either
    a count or a fraction, often normalized to one.
    """
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

    x0 = [0.0, 0.0, 209.3, 1000 / 1e6, 0.0, 0.0, 0.0, 0.0]

    kappa = 14.65 / 1000 / 365.25 * 0
    mu = 6.08 / 1000 / 365.25 * 0
    sigma = 1 / 5.0
    rho_a = 0.4
    R0 = 2.74
    icu_capacity = 209.3 * (2.3 / 1e4) * 0.5
    hospital_capacity = 209.3 * (2.4 / 1e3) * 0.5
    region = None
    year = 2020

    p_s = 0.4
    p_h = 0.18
    p_c = 0.05 / p_h
    p_f = 0.015 / p_c / p_h
    p_hr = 0.25
    p_cr = 1.00

    gamma_a = 1 / 1.61
    gamma_i = 1 / 1.61
    gamma_h = 1 / 3.3
    gamma_c = 1 / 17.5

    gamma_hr = gamma_h
    gamma_cr = gamma_c

    beta = R0 * gamma_i * 1 / p_s

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.region is not None:
            self.p_h, self.p_c, self.p_f = covid_mean_mortality(self.region, self.year)

    def diff(self, x, t):
        r, f, s, e, i, c, h, a = x

        mu = self.mu
        sigma = self.sigma

        p_s = self.p_s
        p_h = self.p_h
        p_c = self.p_c
        p_f = self.p_f
        p_hr = self.p_hr
        p_cr = self.p_cr

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

    def summary_map(self, run):
        df = run.data
        recovered = self.get_data_recovered(df).iloc[-1]
        fatalities = self.get_data_fatalities(df).iloc[-1]
        critical = self.get_data_critical(df).max()
        hospitalized = self.get_data_hospitalized(df).max()
        total = self.get_data_total(df).iloc[-1]

        fluctuation = df.sum(1).std()

        return {
            "Fatalities": f"{fatalities:.3f}mi",
            "Pop fatalities": f"{100 * fatalities / total:.2f}%",
            "IRF": f"{100 * fatalities / (recovered + fatalities):.2f}%",
            "Req. ICU": f"{critical:.3f}mi",
            "ICU overload": f"x {critical / self.icu_capacity:.3f}",
            "Req. beds": f"{hospitalized:.3f}mi",
            "Hospital overload": f"x {hospitalized / self.hospital_capacity:.3f}",
            "Recovered": f"{100 * recovered / total:.2f}%",
            "Fluctuation": f"{fluctuation}",
        }

    #
    # Column access
    #
    def _get_column(self, col, df):
        return df[col]

    def get_data_total(self, df):
        return df.sum(1)

    def get_data_fatalities(self, df):
        return self._get_column('Fatalities', df)

    def get_data_recovered(self, df):
        return self._get_column('Recovered', df)

    def get_data_susceptible(self, df):
        return self._get_column('Susceptible', df)

    def get_data_exposed(self, df):
        return self._get_column('Exposed', df)

    def get_data_infected(self, df):
        return self._get_column('Infected', df)

    def get_data_critical(self, df):
        return self._get_column('Critical', df)

    def get_data_hospitalized(self, df):
        return self._get_column('Hospitalized', df)

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
    m = RSeicha.main(region='Brazil')
