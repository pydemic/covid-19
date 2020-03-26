import numpy as np
import pandas as pd

from .seichar import SEICHAR
from .. import data
from ..region import Region


class SEICHARDemographic(SEICHAR):
    """
    RSEICHA model for epidemics that uses demography information
    """

    _dedup_factor = 0.5
    demography: pd.DataFrame
    mortality: pd.DataFrame
    region: Region = 'WORLD'
    contact_matrix = None
    ref_year = 2020
    seed = 1e-3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        def set_(attr, value):
            x = kwargs.get(attr, value)
            setattr(self, attr, x)
            return x

        # Required demographic information
        if not hasattr(self, 'demography'):
            self.demography = self.region.age_coarse
        self.sub_groups = tuple(self.demography.index)

        if not hasattr(self, 'mortality'):
            self.mortality = data.mortality.covid_mortality()

        # Contact matrix
        set_('contact_matrix', self.region.contact_matrix.values)
        if self.contact_matrix is not None:
            M = self.contact_matrix
            self.relative_contact_matrix = (M.T / M.sum(1)).T
        else:
            self.relative_contact_matrix = 1.0

        # Initial state
        n_groups = len(self.sub_groups)
        if 'x0' not in kwargs:
            empty = self.demography.values * 0
            seed = self.seed / n_groups
            self.x0 = np.concatenate([
                empty,
                empty,
                self.demography.values - seed * (1 + 1 / self.prob_symptomatic),
                empty + seed / self.prob_symptomatic,
                empty + seed,
                empty,
                empty,
                empty,
            ])
            self._children = self.demography.values * 0.0
            self._children[0] = 1.0

        # Columns and indexes
        self.display_columns = [(x, 'total') for x in self.columns]

        self.SUSCEPTIBLE, \
        self.EXPOSED, \
        self.INFECTED, \
        self.CRITICAL, \
        self.HOSPITALIZED, \
        self.ASYMPTOMATIC, \
        self.RECOVERED, \
        self.FATALITIES = range(0, 8 * n_groups, n_groups)

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

        err = 1e-50
        h_hat = h / (h.sum() + err)
        c_hat = c / (c.sum() + err)
        hplus = h_hat * max(0, h.sum() - self.hospital_capacity)
        hminus = h_hat * min(h.sum(), self.hospital_capacity)
        cplus = c_hat * max(0, c.sum() - self.icu_capacity)
        cminus = c_hat * min(c.sum(), self.icu_capacity)

        diff = self.diff_seichar(s, e, i, cminus, cplus, hminus, hplus, a, r, f, t)
        return np.array(diff)

    def lambd(self, n, i, a, t):
        return np.dot(self.beta(t) * self.relative_contact_matrix, (i + self.rho * a) / n)


if __name__ == '__main__':
    SEICHARDemographic.main(region='Brazil')
