import datetime

import streamlit as st

import covid
from covid import gettext as _
from covid.data import countries
from covid.models import SEICHAR
from covid.utils import fmt, pc
from covid.data import age_distribution

TODAY = datetime.datetime.now()
TODAY = datetime.date(TODAY.year, TODAY.month, TODAY.day)

# Adjust demography to 2020. We only have citywise and statewise datasets
# from the Brazilian Census of 2010.
DEMOGRAPHY_CORRECTION = age_distribution("Brazil", 2020, coarse=True) / age_distribution(
    "Brazil", 2010, coarse=True
)


class Input:
    def __init__(self, country, display_country=None, target=None):
        self.country = country
        self.display_country = display_country or country.title()
        self.target = target or st.sidebar

    def run(self):
        """
        Return a dictionary of keyword arguments from user input.

        This dictionary can be passed to the model constructor with minimal
        modifications.
        """
        region = self.region()
        self.pause()
        return {"region": region, **self.params(region)}

    def pause(self):
        """
        Separator between commands.
        """
        st.sidebar.markdown("` `")

    def region(self):
        """
        Return a region instance from user input.
        """

        # Select a state
        st.sidebar.header(_("Location"))
        df = states(self.country)
        choices = [self.display_country, *df["name"]]
        choice = st.sidebar.selectbox(_("State"), choices)
        if choice == choices[0]:
            return get_region(self.country)
        state_id = state_code(self.country, choice)

        # State selected, now ask for sub-region
        df = sub_regions(self.country, state_id)
        if len(df) == 1:
            choice = df["name"].iloc[0]
        else:
            choices = [_("All"), *df["name"]]
            choice = st.sidebar.selectbox(_("Region"), choices)
            if choice == choices[0]:
                return get_region(f"{self.country}/{state_id}")
        sub_region_id = sub_region_code(self.country, state_id, choice)

        # Sub-region selected, now ask for a city
        df = cities(self.country, sub_region_id)
        if len(df) == 1:
            choice = df["name"].iloc[0]
        else:
            choices = [_("All"), *df["name"]]
            choice = st.sidebar.selectbox(_("City"), choices)
            if choice == choices[0]:
                return get_region(f"{self.country}/{sub_region_id}")
        city_id = df[df["name"] == choice].index[0]
        return get_region(f"{self.country}/{city_id}")

    def params(self, region):
        """
        Return a dictionary with simulation parameters from user input.
        """

        simulation = self.simulation(region)
        self.pause()
        healthcare = self.healthcare(region)
        self.pause()
        epidemiology = self.epidemiology(region)
        self.pause()
        intervention = self.intervention(region)

        return {**simulation, **healthcare, **epidemiology, **intervention}

    def simulation(self, region: covid.Region):
        """
        Return a dictionary with basic simulation parameters from user input.

        Returns:
              period (int): Simulation period in days.
              start_date (date): Initial date.
              seed (int): Initial number of cases.
        """
        st.sidebar.header(_("Simulation options"))
        seed = int(max(5e-6 * region.population_size, 1))
        return {
            "period": st.sidebar.slider(_("Duration (weeks)"), 1, 30, value=10) * 7,
            "start_date": st.sidebar.date_input(_("Simulation date")),
            "seed": st.sidebar.number_input(
                _("Number of detected cases"), 1, int(region.population_size), value=seed
            ),
        }

    def healthcare(self, region: covid.Region):
        """
        Return a dictionary with hospital and icu capacities from user input.

        Returns:
            icu_capacity, hospital_capacity (float): maximum system capacity
        """
        st.sidebar.header(_("Hospital capacity"))

        def get(msg, capacity, rate, key=None):
            st.sidebar.subheader(msg)
            msg = _(
                "Location has {n} beds, but only {rate} are typically available in a given day."
            )
            st.sidebar.markdown(msg.format(n=fmt(int(capacity)), rate=pc(1 - rate)))
            total = st.sidebar.number_input(
                _("Beds dedicated exclusively to COVID-19"),
                min_value=0,
                value=int((1 - rate) * capacity),
                key=key + "_total",
            )
            return (1 - rate) * total

        h_total = region.hospital_total_capacity
        h_rate = max(region.hospital_occupancy_rate, 0.75)
        c_total = region.icu_total_capacity
        c_rate = max(region.icu_occupancy_rate, 0.75)
        return {
            "hospital_capacity": get(_("Clinical beds"), h_total, h_rate, key="hospital"),
            "icu_capacity": get(_("ICU beds"), c_total, c_rate, key="icu"),
        }

    def epidemiology(self, region: covid.Region):
        """
        Return a dictionary with additional simulation parameters from user input.
        Those parameters are related to basic epidemiology assumptions such as
        the value of R0, incubation period, etc.
        """

        e = 1e-50
        st.sidebar.header(_("Epidemiology"))
        std, fast, slow, custom = scenarios = [_("Standard"), _("Fast"), _("Slow"), _("Advanced")]
        scenario = st.sidebar.selectbox(_("Scenario"), scenarios)

        if scenario == std:
            return {"R0": 2.74}
        if scenario == fast:
            return {"R0": 3.5}
        elif scenario == slow:
            return {"R0": 2.0}

        # Custom
        st.sidebar.subheader(_("Epidemiological parameters"))
        R0 = SEICHAR.R0
        msg = _("Newly infected people for each infection (R0)")
        R0 = st.sidebar.slider(msg, min_value=0.0, max_value=5.0, value=R0)

        incubation_period = 1 / SEICHAR.sigma
        msg = _("Virus incubation period")
        incubation_period = st.sidebar.slider(
            msg, min_value=1.0, max_value=10.0, value=incubation_period
        )

        infectious_period = 1 / SEICHAR.gamma_i
        msg = _("Infectious period")
        infectious_period = st.sidebar.slider(
            msg, min_value=1.0, max_value=14.0, value=infectious_period
        )

        prob_symptomatic = 100 * SEICHAR.prob_symptomatic
        msg = _("Fraction of symptomatic cases")
        prob_symptomatic = 0.01 * st.sidebar.slider(
            msg, min_value=0.0, max_value=100.0, value=prob_symptomatic
        )

        st.sidebar.subheader(_("Clinical parameters"))
        prob_hospitalization = 200 * region.prob_hospitalization
        prob_hospitalization = st.sidebar.slider(
            _("Fraction of hospitalized cases"),
            min_value=0.0,
            max_value=100.0,
            value=prob_hospitalization,
        )
        hospitalization_bias = prob_hospitalization / (100 * region.prob_hospitalization)

        hospitalization_period = 1 / SEICHAR.gamma_h
        msg = _("Hospitalization period (days)")
        hospitalization_period = st.sidebar.slider(
            msg, min_value=0.0, max_value=30.0, value=hospitalization_period
        )

        icu_period = 1 / SEICHAR.gamma_c
        msg = _("Hospitalization period for ICU patients (days)")
        icu_period = st.sidebar.slider(msg, min_value=0.0, max_value=30.0, value=icu_period)

        return {
            "R0": R0,
            "sigma": 1.0 / (incubation_period + e),
            "gamma_i": 1.0 / (infectious_period + e),
            "gamma_h": 1.0 / (hospitalization_period + e),
            "gamma_c": 1.0 / (icu_period + e),
            "prob_symptomatic": prob_symptomatic,
            "hospitalization_bias": hospitalization_bias,
        }

    def intervention(self, region: covid.Region):
        """
        Return a dictionary with intervention parameters.

        Returns:
            icu_capacity, hospital_capacity (float): maximum system capacity
        """

        st.sidebar.header(_("Intervention"))
        baseline, social_distance = interventions = [_("None"), _("Social distancing")]
        intervention = st.sidebar.selectbox(_("Scenario"), interventions)
        if intervention == baseline:
            return {}
        elif intervention == social_distance:
            st.sidebar.markdown(
                _(
                    """
This intervention simulates a situation in which everyone reduces
the average number of encounters throughout the day. Small reductions (~15%) are
possible through small behavioral changes. Larger reductions require implementation
of many non-pharmacological measures.
"""
                )
            )
            week = TODAY + datetime.timedelta(days=7)
            date = st.sidebar.date_input(_("Date of intervention"), value=week)
            rate = st.sidebar.slider(_("Reduction in the number of contacts"), value=15)
            return {"intervention": social_distance_intervention(date, 1 - rate / 100)}


def social_distance_intervention(date, rate):
    """
    Multiply R0 by the given rate after some days of simulation.
    """

    def fn(model):
        if date < model.start_date:
            st.warning(_("Intervention starts prior to simulation"))
            model.R0 *= rate
            return model
        else:
            delta = date - model.start_date
            R0_initial = model.R0
            R0_final = model.R0 * rate
            t_intervention = delta.days

            def Rt(t):
                return R0_initial if t < t_intervention else R0_final

            model.R0 = Rt
            return model

    return fn


@st.cache
def states(country):
    return countries.states(country.lower())


@st.cache
def sub_regions(country, state_id):
    sub_regions = countries.sub_regions(country.lower())
    return sub_regions[sub_regions["state_id"] == state_id]


@st.cache
def cities(country, sub_region):
    cities = countries.cities(country.lower())
    return cities[cities["sub_region"] == sub_region]


@st.cache
def state_code(country, state):
    names = states(country)["name"]
    return names[names == state].index[0]


@st.cache
def sub_region_code(country, state_code, sub_region):
    regions = sub_regions(country, state_code)
    return regions[regions["name"] == sub_region].index[0]


@st.cache(allow_output_mutation=True)
def get_region(ref):
    region = covid.region(ref)
    if ref.lower().startswith("brazil/"):
        region.demography = DEMOGRAPHY_CORRECTION
    return region


if __name__ == "__main__":
    from pprint import pformat

    app = Input("brazil", _("Brazil"), st.sidebar)
    res = app.run()
    st.text(pformat(res))
