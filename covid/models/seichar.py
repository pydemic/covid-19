import datetime

import numpy as np
import pandas as pd

from .model import Model
from .plot import SEICHARPlot
from ..region import region as as_region
from ..types import delegate, cached, alias, computed
from ..utils import fmt, pc, pm

identity = lambda x: x


# noinspection PyUnusedLocal
class SEICHAR(Model):
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
        "susceptible",
        "exposed",
        "infectious",
        "critical",
        "hospitalized",
        "asymptomatic",
        "recovered",
        "fatalities",
    ]
    (
        SUSCEPTIBLE,
        EXPOSED,
        INFECTIOUS,
        CRITICAL,
        HOSPITALIZED,
        ASYMPTOMATIC,
        RECOVERED,
        FATALITIES,
    ) = range(8)

    SUSCEPTIBLE_ALL = cached(lambda x: x._idx_all(x.SUSCEPTIBLE))
    EXPOSED_ALL = cached(lambda x: x._idx_all(x.EXPOSED))
    INFECTIOUS_ALL = cached(lambda x: x._idx_all(x.INFECTIOUS))
    CRITICAL_ALL = cached(lambda x: x._idx_all(x.CRITICAL))
    HOSPITALIZED_ALL = cached(lambda x: x._idx_all(x.HOSPITALIZED))
    ASYMPTOMATIC_ALL = cached(lambda x: x._idx_all(x.ASYMPTOMATIC))
    RECOVERED_ALL = cached(lambda x: x._idx_all(x.RECOVERED))
    FATALITIES_ALL = cached(lambda x: x._idx_all(x.FATALITIES))
    _idx_all = lambda self, i: [i]

    OPTIONS = {
        "seed:int": "Initial infectious population",
        "region:str": "Country/city used to infer demographic and epidemiological " "parameters",
        "R0": "Basic reproducibility number",
        "rho": "Ratio in which asymptomatic infect other people",
        "prob_symptomatic": "Probability of developing symptoms",
        "sigma": "Rate of infection for exposed individuals",
        "hospitalization_bias": "Speculative multiplicative factor to account for "
        "errors in hospitalization "
        "rates statistics",
        "hospital_prioritization": "Fraction of how much we can reduce demand on "
        "healthcare system to allocate "
        "it to the COVID struggle",
    }
    plot_class = SEICHARPlot
    plot: SEICHARPlot
    region = None
    ref_year = 2020

    # Epidemiological parameters
    R0 = 2.74
    rho = 0.55
    prob_symptomatic = 0.14
    import_rate = 0.0
    import_asymptomatic = True

    @property
    def K(self):
        g = self.gamma_i
        s = self.sigma
        R0 = self.R0
        return 0.5 * (s + g) * (np.sqrt(1 + 4 * (R0 - 1) * s * g / (s + g) ** 2) - 1)

    @computed
    def asympt_import_rate(self):
        if self.import_asymptomatic:
            return self.import_rate / self.prob_symptomatic
        else:
            return 0.0

    @property
    def R0_average(self):
        if callable(self.R0):
            fn = self.R0
            return sum(fn(t) for t in self.data.index) / len(self.data)
        else:
            return self.R0

    # Old parameters
    # sigma = 1 / 5.0
    # gamma_i = 1 / 1.61
    # gamma_h = 1 / 3.3
    # gamma_c = 1 / 17.5

    # Revised values
    sigma = 1 / 3.69
    gamma_i = 1 / 3.47
    gamma_a = gamma_i
    gamma_h = 1 / 10.0
    gamma_c = 1 / 7.5
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
    hospital_overflow_date = delegate("start_date")
    icu_overflow_date = delegate("start_date")
    hospital_overflow_time = 0.0
    icu_overflow_time = 0.0

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
            return self.data.iloc[-1].sum() - self.fatalities
        else:
            return sum(self.state) - self.fatalities

    @classmethod
    def _main(cls, *args, hospitalization_bias=1.0, **kwargs):
        m = super()._main(*args, **kwargs)
        m.prob_hospitalization *= hospitalization_bias or 1.0
        return m

    @classmethod
    def main(cls, *args, r0=None, **kwargs):
        if r0:
            kwargs["R0"] = r0
        return super().main(*args, **kwargs)

    # Deprecated properties
    x0 = alias("state")

    def __init__(self, *args, x0=None, **kwargs):
        if x0 is not None:
            kwargs["state"] = x0
        super().__init__(*args, **kwargs)
        self._watching = {}

        def set_(attr, value):
            x = kwargs.get(attr, value)
            setattr(self, attr, x)
            return x

        # Load datasets from from region
        if self.region is not None:
            self.region = region = as_region(self.region)

            # Mortality statistics
            set_("prob_hospitalization", region.prob_hospitalization)
            set_("prob_icu", region.prob_icu)
            set_("prob_fatality", region.prob_fatality)

            # Initial population
            if self.initial_population is None:
                set_("initial_population", region.population_size)

            # Healthcare statistics
            set_("icu_beds_pm", region.icu_beds_pm)
            set_("icu_occupancy_rate", region.icu_occupancy_rate)
            set_("hospital_beds_pm", region.hospital_beds_pm)
            set_("hospital_occupancy_rate", region.hospital_occupancy_rate)

            # R0 via contact matrix
            ...

            # Vital dynamics
            ...

        # Fix population and seed
        if self.initial_population is None:
            self.initial_population = 1.0
            self.seed = 0.01 if self.seed >= 1.0 else self.seed

        # Initial state
        if "state" not in kwargs:
            p_s = self.prob_symptomatic
            i = self.seed
            a = i * (1 - p_s) / p_s
            e = i * (self.gamma_i + self.K) / self.sigma / self.prob_symptomatic
            s = self.initial_population - (i + e + a)
            self.state = [
                s,
                e,
                i,
                0,  # critical
                0,  # hospitalized
                a,
                0,  # recovered
                self.fatalities,
            ]
        self.state = np.array(self.state)
        self._mu = self.mu if self.vital_dynamics else 0.0

        assert 0.0 <= self.prob_symptomatic <= 1.0
        assert 0.0 <= self.prob_hospitalization <= 1.0
        assert 0.0 <= self.prob_icu <= 1.0, self.prob_icu
        assert 0.0 <= self.prob_no_hospitalization_fatality <= 1.0
        assert 0.0 <= self.prob_no_icu_fatality <= 1.0

    def get_total(self, col):
        return self[col] if isinstance(col, str) else col

    def rk4_step(self, x, t, dt, watcher=None):
        x_ = super().rk4_step(x, t, dt, watcher)
        return np.where(x_ > 0, x_, 0.0)

    def diff(self, x, t):
        s, e, i, c, h, a, r, f = x
        hplus = max(0, h - self.hospital_capacity)
        hminus = min(h, self.hospital_capacity)
        cplus = max(0, c - self.icu_capacity)
        cminus = min(c, self.icu_capacity)

        assert hplus >= 0 and hminus >= 0 and cplus >= 0 and cminus >= 0, locals()
        assert np.all(x >= 0), locals()

        diff = self.diff_seichar(s, e, i, cminus, cplus, hminus, hplus, a, r, f, t)
        return np.array(diff)

    def diff_seichar(self, s, e, i, cminus, cplus, hminus, hplus, a, r, f, t):
        n = s + e + i + cminus + cplus + hminus + hplus + a + r
        lambd = self.lambd(n, i, a, t)
        return [
            self.diff_s(s, n, lambd, t),
            self.diff_e(s, e, lambd, t),
            self.diff_i(e, i, t),
            self.diff_c(hminus + hplus, cminus, cplus, t),
            self.diff_h(i, hminus, hplus, cminus, t),
            self.diff_a(e, a, t),
            self.diff_r(a, i, hminus, hplus, cminus, cplus, r, t),
            self.diff_f(hplus, cminus, cplus, t),
        ]

    def beta(self, t):
        p_s = self.prob_symptomatic
        R0 = self.R0(t) if callable(self.R0) else self.R0
        return (
            R0
            * (self.gamma_i + self._mu)
            * (self.sigma + p_s * self._mu)
            / self.sigma
            / (p_s + (1 - p_s) * self.rho)
        )

    def lambd(self, n, i, a, t):
        return self.beta(t) * (i + self.rho * a) / n

    def diff_s(self, s, n, lambd, t):
        infections = self._infections(lambd, s)

        if self.vital_dynamics:
            # FIXME: prevent S from being negative due to import rate
            return self.kappa * n - infections - self.mu * s - self.import_rate
        else:
            return -infections - self.import_rate

    def _infections(self, lambd, s):
        return lambd * s

    def diff_e(self, s, e, lambd, t):
        infections = self._infections(lambd, s)
        return infections - self.sigma * e - self._mu * e

    def diff_i(self, e, i, t):
        p_s = self.prob_symptomatic
        return p_s * self.sigma * e - self.gamma_i * i - self._mu * i + self.import_rate

    def diff_c(self, h, cminus, cplus, t):
        c = cminus + cplus
        return (
            self.prob_icu * self.gamma_h * h
            - self.gamma_c * cminus
            - self.gamma_cr * cplus
            - self._mu * c
        )

    def diff_h(self, i, hminus, hplus, cminus, t):
        h = hminus + hplus
        return (
            self.prob_hospitalization * self.gamma_i * i
            - self.gamma_h * hminus
            - self.prob_icu * self.gamma_h * hplus
            - self.gamma_hr * hplus
            + (1 - self.prob_fatality) * self.gamma_c * cminus
            - self._mu * h
        )

    def diff_a(self, e, a, t):
        p_s = self.prob_symptomatic
        return (
            (1 - p_s) * self.sigma * e - self.gamma_a * a - self._mu * a + self.asympt_import_rate
        )

    def diff_r(self, a, i, hminus, hplus, cminus, cplus, r, t):
        return (
            self.gamma_a * a
            + (1 - self.prob_hospitalization) * self.gamma_i * i
            + (1 - self.prob_icu) * self.gamma_h * hminus
            + (1 - self.prob_no_hospitalization_fatality) * self.gamma_hr * hplus
            + (1 - self.prob_no_icu_fatality) * self.gamma_cr * cplus
            - self._mu * r
        )

    def diff_f(self, hplus, cminus, cplus, t):
        return (
            self.prob_fatality * self.gamma_c * cminus
            + self.prob_no_hospitalization_fatality * self.gamma_hr * hplus
            + self.prob_no_icu_fatality * self.gamma_cr * cplus
        )

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
        t_h = float("inf")
        t_c = float("inf")

        self._watching = w = {"hospital_overflow_t": t_h, "icu_overflow_t": t_c}

        def watch(x, v, t, dt):
            nonlocal t_h, t_c

            h = np.sum(x[self.HOSPITALIZED_ALL])
            c = np.sum(x[self.CRITICAL_ALL])
            if h >= self.hospital_capacity:
                t_h = min(t_h, t)
            if c >= self.icu_capacity:
                t_c = min(t_c, t)

            w["hospital_overflow_t"] = t_h
            w["icu_overflow_t"] = t_c
            self._watch_simulation(w, x, v, t, dt)

        return watch

    def _watch_simulation(self, w, x, v, t, dt):
        pass

    def _run_post_process(self):
        def advance(t):
            if np.isinf(t):
                return None
            return self.start_date + datetime.timedelta(int(t))

        # Compartments
        r = self["recovered:total"]
        f = self["fatalities:total"]
        s = self["susceptible:total"]
        e = self["exposed"]
        i = self["infectious"]
        c = self["critical"]
        h = self["hospitalized"]
        a = self["asymptomatic"]
        total = self.get_total
        integral = self.integral
        w = self._watching

        # Healthcare statistics
        self.peak_hospitalization_demand = total(h).max()
        self.peak_icu_demand = total(c).max()
        self.hospitalization_days = total(integral(h))
        self.icu_days = total(integral(c))
        self.hospital_overflow_time = w["hospital_overflow_t"]
        self.icu_overflow_time = w["icu_overflow_t"]
        self.hospital_overflow_date = advance(self.hospital_overflow_time)
        self.icu_overflow_date = advance(self.icu_overflow_time)

        # Epidemiology
        self.susceptible = s.iloc[-1]
        self.recovered = r.iloc[-1]
        self.fatalities = f.iloc[-1]

        self.total_exposed = total(integral(e) * self.sigma)
        self.total_infectious = total(integral(i) * self.gamma_i)
        self.total_asymptomatic = total(integral(a) * self.gamma_a)
        self.total_hospitalized = total(integral(h) * self.gamma_h)
        self.total_critical = total(integral(c) * self.gamma_c)

    def mortality_rate(self):
        """Return the infection fatality ratio so far"""
        return self.fatalities / self.population

    def IFR(self):
        """Return the infection fatality ratio so far"""
        return self.fatalities / self.total_exposed

    def CFR(self):
        """Return the case fatality ratio so far"""
        return self.fatalities / self.total_infectious

    def summary(self):
        sym_name = type(self).__name__
        return "\n\n".join(
            [
                f"\nSIMULATION PARAMETERS ({sym_name})",
                self.summary_parameters(),
                f"SIMULATION RESULTS ({sym_name})",
                self.summary_demography(),
                self.summary_epidemiology(),
                self.summary_healthcare(),
                self.summary_simulation(),
            ]
        )

    def summary_parameters(self):
        return f"""Parameters
- R0                : {fmt(self.R0_average)}
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
- Infectious (max)   : {fmt(int(self.total_infectious))} ({pc(self.total_infectious / N)})
- Asymptomatic (max) : {fmt(int(self.total_asymptomatic))} ({pc(p_asympt)})
- Exposed (max)      : {fmt(int(self.total_exposed))} ({pc(self.total_exposed / N)})
"""

    def summary_epidemiology(self):
        return f"""Epidemiology
- R0   : {self.R0}
- IFR  : {pc(self.fatalities / self.total_exposed)}
- CFR  : {pc(self.fatalities / self.total_infectious)}
"""

    # - HFR: {pc(self.fatalities / self.total_hospitalized)}
    # - HCFR: {pc(self.fatalities / self.total_critical)}

    def summary_healthcare(self):
        N = self.population

        t_hf = self.hospital_overflow_time
        dt_hf = self.hospital_overflow_date
        t_cf = self.icu_overflow_time
        dt_cf = self.icu_overflow_date

        h_demand = self.peak_hospitalization_demand
        c_demand = self.peak_icu_demand
        icu_overload = self.peak_icu_demand / self.icu_capacity * (1 - self.icu_occupancy_rate)
        h_overload = (
            self.peak_hospitalization_demand
            / self.hospital_capacity
            * (1 - self.hospital_occupancy_rate)
        )

        return f"""Healthcare parameters
- Hosp. days         : {fmt(int(self.hospitalization_days))}
- ICU days           : {fmt(int(self.icu_days))}
- Peak hosp. demand  : {fmt(int(h_demand))} ({pm(h_demand / N)})
    x surge capacity : {fmt(self.peak_hospitalization_demand / self.hospital_capacity)}
    x total          : {fmt(h_overload)}
- Peak ICU demand    : {fmt(int(c_demand))} ({pm(c_demand / N)})
    x surge capacity : {fmt(self.peak_icu_demand / self.icu_capacity)}
    x total          : {fmt(icu_overload)}
- Hosp. overflow     : {fmt(t_hf)} days ({dt_hf})
- ICU overflow       : {fmt(t_cf)} days ({dt_cf})
"""

    def summary_simulation(self):
        N = self.data.iloc[0].sum()
        fluctuation = self.data.values.sum(1).std()
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
        return self._get_column("fatalities", df)

    def get_data_fatalities_final(self, df):
        return self.get_data_fatalities(df).iloc[-1]

    def get_data_recovered(self, df):
        return self._get_column("recovered", df)

    def get_data_recovered_final(self, df):
        return self.get_data_recovered(df).iloc[-1]

    def get_data_susceptible(self, df):
        return self._get_column("susceptible", df)

    def get_data_exposed(self, df):
        return self._get_column("exposed", df)

    def get_data_infectious(self, df):
        return self._get_column("infectious", df)

    def get_data_critical(self, df):
        return self._get_column("critical", df)

    def get_data_icu(self, df):
        xs = self.get_data_critical(df)
        max_icu = self.icu_capacity
        data = np.data.where(xs > max_icu, max_icu, xs)
        return pd.Series(data, index=xs.index)

    def get_data_critical_demand(self, df):
        return self.get_data_critical(df).max()

    def get_data_hospitalized(self, df):
        return self._get_column("hospitalized", df)

    def get_data_hospitalized_demand(self, df):
        return self.get_data_hospitalized(df).max()

    def get_data_asymptomatic(self, df):
        return self._get_column("asymptomatic", df)

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
        columns = [_("Name"), _("Items/patient/day"), _("Total")]
        N = int(self.hospitalization_days + self.icu_days)
        a = 1  # / 5
        b = 1  # / 15
        df = pd.DataFrame(
            [
                [_("Cirurgical masks"), 25, 25 * N],
                [_("N95 mask"), a, a * N],
                [_("Waterproof apron"), 25, 25 * N],
                [_("Non-sterile glove"), 50, 50 * N],
                [_("Faceshield"), b, b * N],
            ],
            columns=columns,
        )
        df.index = df.pop(columns[0])
        return df


if __name__ == "__main__":
    SEICHAR()
    m = SEICHAR.main()
