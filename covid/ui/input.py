import streamlit as st

import covid
from covid.data import countries
from covid.models import SEICHAR


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
        return {'region': region, **self.params(region)}

    def pause(self):
        """
        Separator between commands.
        """
        st.sidebar.markdown('` `')

    def region(self):
        """
        Return a region instance from user input.
        """

        # Select a state
        st.sidebar.header("Região")
        df = states(self.country)
        choices = [self.display_country, *df["name"]]
        choice = st.sidebar.selectbox("Estado", choices)
        if choice == choices[0]:
            return covid.region("Brazil")
        state_id = state_code(self.country, choice)

        # State selected, now ask for sub-region
        df = sub_regions(self.country, state_id)
        if len(df) == 1:
            choice = df["name"].iloc[0]
        else:
            choices = ["Tudo", *df["name"]]
            choice = st.sidebar.selectbox("Região", choices)
            if choice == choices[0]:
                return covid.region(f"Brazil/{state_id}")
        sub_region_id = sub_region_code(self.country, state_id, choice)

        # Sub-region selected, now ask for a city
        df = cities(self.country, sub_region_id)
        if len(df) == 1:
            choice = df["name"].iloc[0]
        else:
            choices = ["Tudo", *df["name"]]
            choice = st.sidebar.selectbox("Cidades", choices)
            if choice == choices[0]:
                return covid.region(f"Brazil/{sub_region_id}")
        city_id = df[df["name"] == choice].index[0]
        return covid.region(f"Brazil/{city_id}")

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

        return {
            **simulation,
            **healthcare,
            **epidemiology,
            **intervention,
        }

    def simulation(self, region: covid.Region):
        """
        Return a dictionary with basic simulation parameters from user input.

        Returns:
              period (int): Simulation period in days.
              start_date (date): Initial date.
              seed (int): Initial number of cases.
        """
        st.sidebar.header("Opções da simulação")
        return {
            "period": st.sidebar.slider("Dias de simulação", 0, 180, value=60),
            "start_date": st.sidebar.date_input("Data inicial"),
            "seed": st.sidebar.number_input("Número de casos detectados", min_value=1),
        }

    def healthcare(self, region: covid.Region):
        """
        Return a dictionary with hospital and icu capacities from user input.

        Returns:
            icu_capacity, hospital_capacity (float): maximum system capacity
        """
        st.sidebar.header("Capacidade hospitalar")

        def get(msg, capacity, rate, key=None):
            st.sidebar.subheader(msg)
            total = st.sidebar.number_input(
                "Total", min_value=0, value=int(capacity), key=key + "_total"
            )
            rate = 0.01 * st.sidebar.slider(
                "Ocupados (%)",
                min_value=0.0,
                max_value=100.0,
                value=100 * float(rate),
                key=key + "_rate",
            )
            return (1 - rate) * total

        h_total = region.hospital_total_capacity
        h_rate = region.hospital_occupancy_rate
        c_total = region.icu_total_capacity
        c_rate = region.icu_occupancy_rate
        return {
            "hospital_capacity": get("Leitos clínicos", h_total, h_rate, key="hospital"),
            "icu_capacity": get("Leitos UTI", c_total, c_rate, key="icu"),
        }

    def epidemiology(self, region: covid.Region):
        """
        Return a dictionary with additional simulation parameters from user input.
        Those parameters are related to basic epidemiology assumptions such as
        the value of R0, incubation period, etc.
        """

        e = 1e-50
        st.sidebar.header("Epidemiologia")
        std, fast, slow, custom = scenarios = \
            ["Padrão", "Rápido", "Lento", "Personalizado"]
        scenario = st.sidebar.selectbox("Cenário", scenarios)

        if scenario == std:
            return {"R0": 2.74}
        if scenario == fast:
            return {"R0": 3.5}
        elif scenario == slow:
            return {"R0": 2.0}

        # Custom
        R0 = SEICHAR.R0
        R0 = st.sidebar.slider("Fator de contágio (R0)", min_value=0.0, max_value=5.0,
                               value=R0, )
        incubation_period = 1 / SEICHAR.sigma
        incubation_period = st.sidebar.slider(
            "Período de incubação do vírus", min_value=1.0, max_value=10.0,
            value=incubation_period
        )

        infectious_period = 1 / SEICHAR.gamma_i
        infectious_period = st.sidebar.slider(
            "Período infeccioso", min_value=1.0, max_value=14.0, value=infectious_period
        )

        prob_fatality = 100 * region.prob_fatality
        prob_fatality = st.sidebar.slider(
            "Taxa de mortalidade média", min_value=0.0, max_value=100.0,
            value=prob_fatality,
        )
        return {
            "R0": R0,
            "sigma": 1.0 / (incubation_period + e),
            "gamma_i": 1.0 / (infectious_period + e),
            # 'prob_fatality': 0.01 * prob_fatality,
        }

    def intervention(self, region: covid.Region):
        """
        Return a dictionary with intervention parameters.

        Returns:
            icu_capacity, hospital_capacity (float): maximum system capacity
        """

        st.sidebar.header("Intervenção")
        baseline, social_distance = interventions = ["Nenhuma",
                                                     "Redução de contato social"]
        intervention = st.sidebar.selectbox("Cenário", interventions)
        if intervention == baseline:
            return {}
        elif intervention == social_distance:
            # TODO: Use params
            date = st.sidebar.slider("Dias após data inicial para início de intervenção")
            rate = st.sidebar.slider("Redução do fator de contágio (RO) após intervenção")
            return {}


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


if __name__ == '__main__':
    from pprint import pformat

    app = Input('brazil', 'Brasil', st.sidebar)
    res = app.run()
    st.text(pformat(res))
