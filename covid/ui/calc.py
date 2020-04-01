from contextlib import contextmanager
from pathlib import Path

import pandas as pd
import streamlit as st

import covid
from covid import gettext as _
from covid.models import SEICHARDemographic as SEICHAR
from covid.utils import fmt, pc
from covid.ui import components
from covid.ui.input import Input


COUNTRY = "Brazil"
DISPLAY_COUNTRY = _("Brazil")

SEIR_HUMANIZED_NAMES = {
    "susceptible": _("susceptible"),
    "exposed": _("exposed"),
    "infectious": _("infectious"),
    "critical": _("critical"),
    "hospitalized": _("hospitalized"),
    "asymptomatic": _("asymptomatic"),
    "recovered": _("recovered"),
    "fatalities": _("fatalities"),
}
e = 1e-50


class CalcUI:
    """
    Renders Streamlit UI.
    """

    simulation_class = SEICHAR
    title = _("COVID-19 assistance pressure")

    def __init__(self, country=COUNTRY, display_country=DISPLAY_COUNTRY):
        st.write(css(), unsafe_allow_html=True)
        st.title(self.title)
        self._info = st.text("")
        self.country = country
        self.input = Input(self.country, display_country=DISPLAY_COUNTRY)

    @contextmanager
    def info(self, st):
        """
        Context manager that displays info text while code inside the with
        block is being executed and clear it afterwards.
        """
        self._info.text(st)
        yield
        self._info.text("")

    def run(self):
        """
        Run streamlit app.
        """
        components.icon(_("OPAS - COVID-19"), _("Epidemic Calculator"), fn=st.sidebar.markdown)
        with self.info(_("Loading region...")):
            region = self.input.region()
            self.input.pause()
        with self.info(_("Loading simulation parameters...")):
            kwargs = {"region": region, **self.input.params(region)}
        with self.info(_("Performing simulation...")):
            self.run_simulation(**kwargs)

    def run_simulation(self, period, hospital_capacity, icu_capacity, **kwargs):
        """
        Initialize class with given arguments and run simulation.
        """
        kwargs = {
            "prob_symptomatic": 0.5,
            "hospital_prioritization": 0.0,
            **kwargs,
        }
        model = self.simulation_class(**kwargs)

        # FIXME: should be able to setup on the constructor
        model.hospital_capacity = hospital_capacity
        model.icu_capacity = icu_capacity
        model.run(period)

        out = Output(model)
        out.run()


class Output:
    def __init__(self, model):
        self.model = model

    def run(self):
        """
        Show all outputs for the given simulated model.
        """
        model = self.model
        self.summary_cards(model)
        self.hospitalizations_plot(model)
        self.available_beds_chart(model)
        self.write_info(model)

    def summary_cards(self, model: SEICHAR):
        """
        Show list of summary cards for the results of simulation.
        """
        contaminated = model.initial_population - model.susceptible
        h_date = model.hospital_overflow_date or _("Never")
        c_date = model.icu_overflow_date or _("Never")
        missing_icu = max(int(model.peak_icu_demand - model.icu_capacity), 0)
        missing_hospital = max(int(model.peak_hospitalization_demand - model.hospital_capacity), 0)
        entries = (
            (_("Clinical beds exhaustion"), f"{h_date}"),
            (_("ICU beds exhaustion"), f"{c_date}"),
            (_("Missing clinical beds on peak date"), f"{fmt(missing_hospital)}"),
            (_("Missing ICU beds on peak date"), f"{fmt(missing_icu)}"),
            (
                _("Contaminated"),
                f"{fmt(int(contaminated))} ({pc(contaminated / model.initial_population)})",
            ),
            (
                _("Deaths"),
                f"{fmt(int(model.fatalities))} ({pc(model.fatalities / model.initial_population)})",
            ),
        )
        components.cards(entries, fn=st.write)

    def hospitalizations_plot(self, model):
        """
        Write plot of hospitalization
        """
        st.subheader(_("Hospitalization chart"))

        hospitalized = model["hospitalized:total"]
        icu = model["critical:total"]
        fatalities = fatality_rate(model["fatalities:total"], model.dt)
        columns = {
            _("Clinical hospitalizations"): hospitalized.astype(int),
            _("ICU hospitalizations"): icu.astype(int),
            _("Deaths/day"): fatalities,
        }
        df = model.get_dates(pd.DataFrame(columns))

        st.area_chart(df)

    def available_beds_chart(self, model):
        """
        Write plot of available beds.
        """
        st.subheader(_("Available beds"))

        hospitalized = model["hospitalized:total"]
        icu = model["critical:total"]

        available_beds = model.hospital_capacity - hospitalized
        available_beds[available_beds < 0] = 0

        available_icu = model.icu_capacity - icu
        available_icu[available_icu < 0] = 0

        columns = {
            _("Available beds"): available_beds,
            _("Available ICU beds"): available_icu,
        }
        df = model.get_dates(pd.DataFrame(columns))

        st.line_chart(df)

    def write_info(self, model):
        """Write additional information about the model."""
        st.subheader("Additional info")
        entries = (
            (_("Clinical beds exhaustion"), model.hospital_overflow_date or _("Never")),
            (_("ICU beds exhaustion"), model.icu_overflow_date or _("Never")),
            (
                _("Missing clinical beds on peak date"),
                fmt(int(model.peak_hospitalization_demand - model.hospital_capacity)),
            ),
            (
                _("Missing ICU beds on peak date"),
                fmt(int(model.peak_icu_demand - model.icu_capacity)),
            ),
        )
        components.cards(entries, fn=st.write)


# @st.cache
def css():
    from covid import ui

    path = Path(ui.__file__).parent / "custom.html"
    with path.open() as fd:
        return fd.read()


def region(name):
    # TODO: Cache this later.
    return covid.region(name)


def rename_data_header(name):
    return SEIR_HUMANIZED_NAMES.get(name, name)


def fatality_rate(fs, dt=1):
    fs = fs.copy()
    fs.iloc[:-1] -= fs.values[1:]
    fs /= -dt
    fs.iloc[-1] = fs.iloc[-2]
    return fs.apply(lambda x: round(x, 1))


# Start main script
if __name__ == "__main__":
    ui = CalcUI()
    ui.run()
