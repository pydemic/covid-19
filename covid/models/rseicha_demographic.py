import numpy as np
import pandas as pd

from .rseicha import RSEICHA
from .. import data


class RSEICHADemographic(RSEICHA):
    """
    RSEICHA model for epidemics that uses demography information
    """

    demography: np.ndarray
    mortality: pd.DataFrame
    region = 'Brazil'
    ref_year = 2020
    seed = 1e-3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not hasattr(self, 'demography'):
            demography = data.age_distribution(self.region, self.year, coarse=True)
            self.demography = demography.values / 1000
            self.sub_groups = tuple(demography.index)

        if not hasattr(self, 'mortality'):
            self.mortality = data.covid_mortality()
            self.p_h = self.mortality['hospitalization'].values
            self.p_c = self.mortality['icu'].values
            self.p_f = self.mortality['fatality'].values

        n_groups = len(self.sub_groups)

        if 'x0' not in kwargs:
            empty = self.demography * 0
            self.x0 = np.concatenate([
                empty,
                empty,
                self.demography,
                empty + self.seed / n_groups,
                empty,
                empty,
                empty,
                empty,
            ])
            self._children = self.demography * 0.0
            self._children[0] = 1.0

        self.display_columns = [(x, 'total') for x in self.columns]
        self.RECOVERED, self.FATALITIES, self.SUSCEPTIBLE, self.EXPOSED, \
        self.INFECTED, self.CRITICAL, self.HOSPITALIZED, self.ASYMPTOMATIC = \
            range(0, 8 * n_groups, n_groups)

    def _get_column(self, col, df):
        return df[(col, 'total')]

    def _to_dataframe(self, times, ys) -> pd.DataFrame:
        df = super()._to_dataframe(times, ys)
        for col in self.columns:
            df[(col, 'total')] = df[col,].sum(1)
        return df

    def get_data_total(self, df):
        # Prevent counting twice from "total" columns
        return df.sum(1) / 2

    def diff(self, x, t):
        r, f, s, e, i, c, h, a = np.reshape(x, (-1, len(self.sub_groups)))

        mu = self.mu
        sigma = self.sigma

        p_s = self.prob_symptomatic
        p_h = self.p_h
        p_c = self.p_c
        p_f = self.p_f
        p_hr = self.prob_no_hospitalization_fatality
        p_cr = self.prob_no_icu_fatality

        gamma_a = self.gamma_a
        gamma_i = self.gamma_i
        gamma_h = self.gamma_h
        gamma_c = self.gamma_c
        gamma_hr = self.gamma_hr
        gamma_cr = self.gamma_cr

        beta = self.R0 * gamma_i

        n = r + s + e + i + c + h + a
        N = n.sum()
        err = 1e-50
        infection_force = (beta * (i + self.rho * a) / (N + err)).sum()
        infections = infection_force * s

        H = h.sum()
        C = c.sum()
        H_extra = max(0, H - self.hospital_capacity)
        C_extra = max(0, C - self.icu_capacity)

        if H_extra:
            h_ = h * (self.hospital_capacity / H)
            dh = h - self.hospital_capacity
            h_extra = np.where(dh > 0, dh, 0.0)
        else:
            h_ = h
            h_extra = h * 0

        if C_extra:
            c_ = c * (self.icu_capacity / C)
            dc = c - self.icu_capacity
            c_extra = np.where(dc > 0, dc, 0.0)
        else:
            c_ = c
            c_extra = c * 0

        ds = self.kappa * N * self._children - infections - mu * s
        de = infections - (1.0 / p_s) * sigma * e - mu * e
        da = (1 - p_s) / p_s * sigma * e - gamma_a * a - mu * a
        di = sigma * e - gamma_i * i - mu * i
        dh = (
                p_h * gamma_i * i
                - gamma_h * h
                - p_c * gamma_h * h_extra
                - gamma_hr * h_extra
                - mu * h
        )
        dc = (
                p_c * gamma_h * h
                - gamma_c * c_
                - gamma_cr * c_extra
                - mu * c
        )
        dr = (
                gamma_a * a
                + (1 - p_h) * gamma_i * i
                + (1 - p_c) * gamma_h * h
                + (1 - p_hr) * gamma_hr * h_extra
                + (1 - p_f) * gamma_c * c_
                + (1 - p_cr) * gamma_cr * c_extra
                - mu * r
        )
        df = (
                p_f * gamma_c * c_
                + p_hr * gamma_hr * h_extra
                + p_cr * gamma_cr * c_extra
        )

        return np.concatenate((dr, df, ds, de, di, dc, dh, da))


if __name__ == '__main__':
    RSEICHADemographic.main(region='Brazil')
