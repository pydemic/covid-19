from contextlib import contextmanager

import streamlit as st

import covid
from covid import gettext as _
from covid.models import SEICHARDemographic as SEICHAR
from covid.ui import components
from covid.ui.components import asset
from covid.ui.input import Input
from covid.ui.output import Output

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
    title = _("COVID-19 Hospital Pressure")

    def __init__(self, country=COUNTRY, display_country=DISPLAY_COUNTRY):
        st.write(asset("custom.html"), unsafe_allow_html=True)
        self._title = st.title(self.title)
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
        components.icon(_("COVID-19"), _("Epidemic Calculator"), where=st.sidebar)
        with self.info(_("Loading region...")):
            region = self.input.region()
            self.input.pause()
            self._title = f"{self.title} - {region}"
        with self.info(_("Loading simulation parameters...")):
            kwargs = {"region": region, **self.input.params(region)}
        with self.info(_("Performing simulation...")):
            self.run_simulation(**kwargs)

    def run_simulation(
        self,
        period,
        hospital_capacity,
        icu_capacity,
        hospitalization_bias=2.0,
        intervention=None,
        **kwargs,
    ):
        """
        Initialize class with given arguments and run simulation.
        """
        kwargs = {"prob_symptomatic": 0.14, "hospital_prioritization": 0.0, **kwargs}
        model = self.simulation_class(**kwargs)

        # FIXME: should be able to setup on the constructor
        model.hospital_capacity = hospital_capacity
        model.icu_capacity = icu_capacity
        model.prob_hospitalization *= hospitalization_bias
        if intervention:
            model = intervention(model)
        model.run(period)

        out = Output(model)
        out.run()


# @st.cache
def region(name):
    return covid.region(name)


def rename_data_header(name):
    return SEIR_HUMANIZED_NAMES.get(name, name)


# Start main script
if __name__ == "__main__":
    ui = CalcUI()
    ui.run()
