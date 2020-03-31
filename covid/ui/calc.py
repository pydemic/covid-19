from contextlib import contextmanager
from pathlib import Path

import pandas as pd
import streamlit as st

import covid
from covid.data import countries
from covid.models import SEICHARDemographic as SEICHAR
from covid.utils import fmt, pc

COUNTRY = "Brazil"
DEFAULT_CITY = "Tudo"
DEFAULT_STATE = "Brasil"
DEFAULT_SUB_REGION = "Tudo"
SEIR_HUMANIZED_NAMES = {
    "susceptible": "suscetíveis",
    "exposed": "expostos",
    "infectious": "infecciosos",
    "critical": "críticos",
    "hospitalized": "hospitalizados",
    "asymptomatic": "assintomáticos",
    "recovered": "recuperados",
    "fatalities": "fatalidades",
}
e = 1e-50


class CalcUI:
    """
    Renders Streamlit UI.
    """

    simulation_class = SEICHAR
    title = "Calculadora de pressão assistencial em decorrência da COVID-19"

    def __init__(self, country=COUNTRY):
        st.write(css(), unsafe_allow_html=True)
        st.title(self.title)
        self._info = st.text("")
        self.info_text = self._info.text
        self.country = COUNTRY

    def info_text(self, st):
        """Display info text."""
        self._info.text(st)

    def clear_info(self):
        """Clears info text."""
        self.info_text("")

    @contextmanager
    def info(self, st):
        """
        Context manager that displays info text while code inside the with
        block is being executed and clear it afterwards.
        """
        self.info_text(st)
        yield
        self.clear_info()

    def run(self):
        """
        Run streamlit app.
        """
        with self.info("Carregando região..."):
            region = self.fetch_region()
        with self.info("Carregando parâmetros de simulação..."):
            kwargs = self.fetch_params(region)
        with self.info("Executando a simulação..."):
            self.run_simulation(region=region, **kwargs)

    def fetch_region(self):
        """
        Return a region instance from user input.
        """

        # Select a state
        st.sidebar.header("Região")
        states_ = states(self.country)
        choices = [DEFAULT_STATE, *states_["name"]]
        state = st.sidebar.selectbox("Estado", choices)
        if state == choices[0]:
            return region("Brazil")
        state = state_code(self.country, state)

        # State selected, now ask for sub-region
        sub_regions_ = sub_regions(self.country, state)
        choices = ["Tudo", *sub_regions_["name"]]
        sub_region = st.sidebar.selectbox("Região", choices)
        if sub_region == choices[0]:
            return region(f"Brazil/{state}")

        # Sub-region selected, now ask for a city
        choices = ["Tudo", *cities(self.country, state, sub_region)["name"]]
        city = st.sidebar.selectbox("Cidades", choices)
        if city == choices[0]:
            return region(f"Brazil/{sub_region} (metro)")
        else:
            return region(f"Brazil/{city}")

    def fetch_params(self, region):
        """
        Return a dictionary with simulation parameters from user input.
        """
        return {
            **self.fetch_simulation_params(region),
            **self.fetch_healthcare_system_params(region),
            **self.fetch_epidemiology_params(region),
            **self.fetch_intervention_params(region),
        }

    def run_simulation(self, *args, period, hospital_capacity, icu_capacity, **kwargs):
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

        self.write_cards(model)
        self.write_hospitalizations_plot(model)
        self.write_available_beds_plot(model)
        self.write_info(model)

    def fetch_simulation_params(self, region: covid.Region):
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

    def fetch_healthcare_system_params(self, region: covid.Region):
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

    def fetch_epidemiology_params(self, region: covid.Region):
        """
        Return a dictionary with additional simulation parameters from user input.
        Those parameters are related to basic epidemiology assumptions such as
        the value of R0, incubation period, etc.
        """

        st.sidebar.header("Epidemiologia")
        std, fast, slow, custom = scenarios = ["Padrão", "Rápido", "Lento", "Personalizado"]
        scenario = st.sidebar.selectbox("Cenário", scenarios)

        if scenario == std:
            return {"R0": 2.74}
        if scenario == fast:
            return {"R0": 3.5}
        elif scenario == slow:
            return {"R0": 2.0}

        # Custom
        R0 = self.simulation_class.R0
        R0 = st.sidebar.slider("Fator de contágio (R0)", min_value=0.0, max_value=5.0, value=R0,)
        incubation_period = 1 / self.simulation_class.sigma
        incubation_period = st.sidebar.slider(
            "Período de incubação do vírus", min_value=1.0, max_value=10.0, value=incubation_period
        )

        infectious_period = 1 / self.simulation_class.gamma_i
        infectious_period = st.sidebar.slider(
            "Período infeccioso", min_value=1.0, max_value=14.0, value=infectious_period
        )

        prob_fatality = 100 * region.prob_fatality
        prob_fatality = st.sidebar.slider(
            "Taxa de mortalidade média", min_value=0.0, max_value=100.0, value=prob_fatality,
        )
        return {
            "R0": R0,
            "sigma": 1.0 / (incubation_period + e),
            "gamma_i": 1.0 / (infectious_period + e),
            # 'prob_fatality': 0.01 * prob_fatality,
        }

    def fetch_intervention_params(self, region: covid.Region):
        """
        Return a dictionary with intervention parameters.

        Returns:
            icu_capacity, hospital_capacity (float): maximum system capacity
        """

        st.sidebar.header("Intervenção")
        baseline, social_distance = interventions = ["Nenhuma", "Redução de contato social"]
        intervention = st.sidebar.selectbox("Cenário", interventions)
        if intervention == baseline:
            return {}
        elif intervention == social_distance:
            # TODO: Use params
            date = st.sidebar.slider("Dias após data inicial para início de intervenção")
            rate = st.sidebar.slider("Redução do fator de contágio (RO) após intervenção")
            return {}

    def write_hospitalizations_plot(self, model):
        """
        Write plot of hospitalization
        """
        st.subheader("Quadros de internação")

        hospitalized = model["hospitalized:total"]
        icu = model["critical:total"]
        fatalities = fatality_rate(model["fatalities:total"], model.dt)
        df = model.get_dates(
            pd.DataFrame(
                {
                    "Internações clínicas": hospitalized.astype(int),
                    "Internações UTI": icu.astype(int),
                    "Fatalidades/dia": fatalities,
                }
            )
        )

        st.area_chart(df)

    def write_available_beds_plot(self, model):
        """
        Write plot of available beds.
        """
        st.subheader("Leitos disponíveis")

        hospitalized = model["hospitalized:total"]
        icu = model["critical:total"]

        available_beds = model.hospital_capacity - hospitalized
        available_beds[available_beds < 0] = 0

        available_icu = model.icu_capacity - icu
        available_icu[available_icu < 0] = 0

        df = model.get_dates(
            pd.DataFrame(
                {"Leitos disponíveis": available_beds, "Leitos de UTI disponíveis": available_icu,}
            )
        )

        st.line_chart(df)

    def write_cards(self, model: SEICHAR):
        contaminated = model.initial_population - model.susceptible
        st.write(
            f"""
<div class="card-boxes">
<dl class="card-box">
    <dt>Exaustão dos leitos clínicos</dt>
    <dd>{model.hospital_overflow_date or 'Nunca'}</dd>
</dl>
<dl class="card-box">
    <dt>Exaustão de leitos de UTI</dt>
    <dd>{model.icu_overflow_date or 'Nunca'}</dd>
</dl>
<dl class="card-box">
    <dt>Leitos UTI faltando no dia do pico</dt>
    <dd>{fmt(max(int(model.peak_icu_demand - model.icu_capacity), 0))}</dd>
</dl>
<dl class="card-box">
    <dt>Leitos clínicos faltando no dia do pico</dt>
    <dd>{fmt(max(int(model.peak_hospitalization_demand - model.hospital_capacity), 0))}</dd>
</dl>
<dl class="card-box">
    <dt>Fatalidades</dt>
    <dd>{fmt(int(model.fatalities))} ({pc(model.fatalities / model.initial_population)})</dd>
</dl>
<dl class="card-box">
    <dt>Contaminados</dt>
    <dd>{fmt(int(contaminated))} ({pc(contaminated / model.initial_population)})</dd>
</dl>
</div>
""",
            unsafe_allow_html=True,
        )

    def write_info(self, model):
        st.subheader("Informações adicionais")
        st.write(
            f"""
<dl class="card-boxes">
    <dt>Exaustão dos leitos clínicos</dt>
    <dd>{model.hospital_overflow_date}</dd>
</dl><dl>
    <dt>Exaustão de leitos de UTI</dt>
    <dd>{model.icu_overflow_date}</dd>
</dl><dl>
    <dt>Leitos UTI faltando no dia do pico</dt>
    <dd>{fmt(int(model.peak_icu_demand - model.icu_capacity))}</dd>
</dl><dl>
    <dt>Leitos clínicos faltando no dia do pico</dt>
    <dd>
    {fmt(int(model.peak_hospitalization_demand - model.hospital_capacity))}</dd>
</dl>
""",
            unsafe_allow_html=True,
        )


@st.cache
def states(country):
    return countries.states(country.lower())


@st.cache
def sub_regions(country, state_code):
    sub_regions = countries.sub_regions(country.lower())
    return sub_regions[sub_regions["state"] == state_code]


@st.cache
def cities(country, state, sub_region):
    cities = countries.cities(country.lower())
    return cities[(cities["state"] == state) & (cities["sub_region"] == sub_region)]


@st.cache
def state_code(country, state):
    states_ = states(country)
    return states_[states_["name"] == state].index[0]


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
