import numpy as np
import pandas as pd

from .seichar import SEICHAR
from .. import data
from ..region import Region


class SEICHARDemographic(SEICHAR):
    """
    RSEICHA model for epidemics that uses demography information
    """

    demography: pd.DataFrame
    mortality: pd.DataFrame
    region: Region = "WORLD"
    contact_matrix = None
    ref_year = 2020
    seed = 1e-3
    asymptomatic_contact_matrix = None
    _idx_all = lambda self, i: np.array(range(i, i + len(self.sub_groups)))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        def set_(attr, value):
            x = kwargs.get(attr, value)
            setattr(self, attr, x)
            return x

        # Required demographic information
        if not hasattr(self, "demography"):
            self.demography = self.region.demography
        self.sub_groups = tuple(self.demography.index)

        # Mortality parameters
        if not hasattr(self, "mortality"):
            self.mortality = data.covid_mortality()
        self.prob_hospitalization = self.mortality["hospitalization"].values
        self.prob_icu = self.mortality["icu"].values
        self.prob_fatality = (
            self.mortality["fatality"].values / self.prob_icu / self.prob_hospitalization
        )

        # Contact matrix
        set_("contact_matrix", np.asarray(self.region.contact_matrix.values))
        if self.contact_matrix is not None:
            M = np.asarray(self.contact_matrix)
            eig = np.linalg.eigvals(M)
            self.relative_contact_matrix = M / eig.real.max()
        else:
            self.relative_contact_matrix = 1.0

        # Import rate must be a vector, unless zero
        if isinstance(self.import_rate, (int, float)) and self.import_rate != 0.0:
            pop = self.demography.values
            self.import_rate = pop * (self.import_rate / pop.sum())

        # Initial state
        n_groups = len(self.sub_groups)
        if "state" not in kwargs:
            empty = self.demography.values * 0
            p_s = self.prob_symptomatic
            i = empty + self.seed / n_groups
            a = i * (1 - p_s) / p_s
            e = i * (self.gamma_i + self.K) / self.sigma / self.prob_symptomatic
            s = self.demography.values - (i + e + a)

            self.x0 = np.concatenate(
                [
                    s,
                    e,
                    i,
                    empty,  # critical
                    empty,  # hospitalized
                    a,
                    empty,  # recovered
                    self.fatalities + empty,
                ]
            )
        self.x0 = np.asarray(self.x0)
        self._children = self.demography.values * 0.0
        self._children[0] = 1.0
        if np.any(self.x0 < 0):
            raise ValueError("invalid initial condition (negative population).")

        # Columns and indexes
        (
            self.SUSCEPTIBLE,
            self.EXPOSED,
            self.INFECTIOUS,
            self.CRITICAL,
            self.HOSPITALIZED,
            self.ASYMPTOMATIC,
            self.RECOVERED,
            self.FATALITIES,
        ) = range(0, 8 * n_groups, n_groups)

    def get_total(self, col):
        data = super().get_total(col)
        return data.sum(len(data.shape) - 1)

    def diff(self, x, t):
        x = np.reshape(x, (-1, len(self.sub_groups)))
        s, e, i, c, h, a, r, f = x

        # assert (x >= 0).all(), f"Invalid value at t={t}: {x}"

        err = 1e-50
        h_hat = h / (h.sum() + err)
        c_hat = c / (c.sum() + err)
        hplus = h_hat * max(0, h.sum() - self.hospital_capacity)
        hminus = h_hat * min(h.sum(), self.hospital_capacity)
        cplus = c_hat * max(0, c.sum() - self.icu_capacity)
        cminus = c_hat * min(c.sum(), self.icu_capacity)

        diff = self.diff_seichar(s, e, i, cminus, cplus, hminus, hplus, a, r, f, t)
        return np.concatenate(diff)

    def lambd(self, n, i, a, t):
        tol = 1e-50
        beta = self.beta(t)

        if self.contact_matrix is None:
            return beta * (i + self.rho * a) / (n + tol)
        elif self.asymptomatic_contact_matrix is None:
            fractions = (i + self.rho * a) / (n + tol)
            return self.relative_contact_matrix * beta * fractions
        else:
            beta_i = self.relative_contact_matrix * beta * i / (n + tol)
            beta_a = self.relative_contact_matrix * beta * a / (n + tol)
            return beta_i + self.rho * beta_a

    def _infections(self, lambd, s):
        res = np.dot(lambd, s)
        # res = np.where(res > s * self.dt, res, s * self.dt)
        return res

    def summary_demography(self):
        st = super().summary_demography()
        fatalities = self.data["fatalities"].iloc[-1]
        exposed = self.data["exposed"].apply(self.integral, 0) * self.sigma
        infectious = self.data["infectious"].apply(self.integral, 0) * self.gamma_i
        data = pd.DataFrame(
            {
                "fatalities": fatalities.apply(int),
                "fatalities (%)": 100 * fatalities / self.demography,
                "IFR (%)": 100 * fatalities / exposed,
                "CFR (%)": 100 * fatalities / infectious,
            }
        )
        data.loc["total", :] = [
            int(fatalities.sum()),
            100 * fatalities.sum() / self.demography.sum(),
            100 * fatalities.sum() / exposed.sum(),
            100 * fatalities.sum() / infectious.sum(),
        ]
        data["fatalities"] = data["fatalities"].apply(int)
        lines = str(data).splitlines()
        data = "\n".join("    " + ln for ln in lines)
        st += f"- Fatalities demography: \n{data}"
        return st


if __name__ == "__main__":
    SEICHARDemographic.main(region="Brazil")
