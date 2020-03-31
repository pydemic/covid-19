import matplotlib.pyplot as plt
import streamlit as st
from datetime import datetime

import covid
from covid.data import countries
from covid.models import SEICHARDemographic as SEICHAR

COUNTRY = "brazil"
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


@st.cache
def get_cities(country):
    return countries.cities(country)


@st.cache
def get_states(country):
    return countries.states(country)


@st.cache
def get_sub_regions(country):
    return countries.sub_regions(country)


def rename_data_header(name):
    return SEIR_HUMANIZED_NAMES.get(name, name)


class CalcUI:
    # Base Data
    base_cities = []
    base_states = []
    base_sub_regions = []

    # Composite data
    cities = []
    region: covid.Region = None
    state_code = None
    sub_regions = []

    # Input
    # Region
    city = DEFAULT_CITY
    state = DEFAULT_STATE
    sub_region = DEFAULT_SUB_REGION

    # Simulation
    period = 60
    t0 = datetime.today()
    seed = 1

    # Healthcare system
    icu_beds_total = 0
    hospital_beds_total = 0
    icu_beds_occupancy_rate = 0.5
    hospital_beds_occupancy_rate = 0.5

    # Epidemiology
    scenario = "Rápido"
    R0 = 3.5
    sigma = 1.0 / (5.0 + e)
    gamma = 1.0 / (4.0 + e)
    prob_fatality = 0.02

    # Misc
    info = None

    def run(self):
        self.sidebar()
        self.body()

    def sidebar(self):
        pass

    def body(self):
        st.title("Calculadora de pressão assistencial em decorrência da COVID-19")
        self.info = st.text("")

    def fetch(self):
        self.fetch_region_data()
        st.sidebar.header("Região")
        self.state = st.sidebar.selectbox("Estado",
                                          [DEFAULT_STATE, *self.base_states["name"]])
        self.handle_state()

    def run_simulation(self):
        if self.is_ready():
            self.info.text("Carregando simulação...")
            kwargs = {"region": self.region, "seed": self.seed, "R0": self.R0}
            kwargs.setdefault("prob_symptomatic", 0.5)
            if self.scenario == "Personalizado":
                kwargs.update(
                    {
                        "sigma": self.sigma, "gamma_i": self.gamma,
                        "prob_fatality": self.prob_fatality
                    }
                )
            # TODO: Generate custom graphs
            model = SEICHAR(**kwargs)
            model.run(self.period)
            model.plot.healthcare_overflow()
            st.pyplot()
            st.text(str(model))
            st.button("Atualizar")
            st.write(model.data.rename(columns=rename_data_header))
            self.info.text("")

    def is_ready(self):
        message = None
        if self.state == DEFAULT_STATE:
            message = "selecione um estado"
        elif self.sub_region == DEFAULT_SUB_REGION:
            message = "selecione uma região"
        elif self.city == DEFAULT_CITY:
            message = "selecione uma cidade"

        if message is not None:
            self.info.text(f"Por favor, {message} no menu lateral.")
            return False
        else:
            return True

    def fetch_region_data(self):
        self.info.text("Carregando dados...")
        self.base_states = get_states(COUNTRY)
        self.base_sub_regions = get_sub_regions(COUNTRY)
        self.base_cities = get_cities(COUNTRY)
        self.info.text("")

    def handle_state(self):
        if self.state == DEFAULT_STATE:
            self.region = covid.region("Brazil")
        else:
            self.state_code = self.base_states[self.base_states.name == self.state].index[
                0]
            # TODO Fetch cities from other states.
            # See `covid/databases/countries/brazil/sub-regions.csv`
            self.sub_regions = self.base_sub_regions[
                self.base_sub_regions.state == self.state_code]
            self.sub_region = st.sidebar.selectbox(
                "Região", [DEFAULT_SUB_REGION, *self.sub_regions["name"]]
            )
            self.handle_sub_region()

    def handle_sub_region(self):
        if self.sub_region == DEFAULT_SUB_REGION:
            # FIXME: Fails with any self.state_code: KeyError: 'DF' ('DF' is
            #  self.state_code)
            try:
                self.region = covid.region(f"Brazil/{self.state_code} (metro)")
            except KeyError:
                pass
        else:
            self.cities = self.base_cities[self.base_cities.sub_region == self.sub_region]
            self.city = st.sidebar.selectbox(
                "Cidade ou município", [DEFAULT_CITY, *self.cities["name"]]
            )
            self.fetch_region()

    def fetch_region(self):
        # TODO: Handle self.city == DEFAULT_CITY
        if self.city != DEFAULT_CITY:
            self.region = covid.region(f"Brazil/{self.city}")
            self.fetch_simulation_params()
            self.fetch_healthcare_system_params()
            self.fetch_epidemiology_params()
            self.fetch_intervention_params()

    def fetch_simulation_params(self):
        st.sidebar.header("Opções da simulação")
        self.period = st.sidebar.slider("Dias de simulação", 0, 180, value=60)
        self.t0 = st.sidebar.date_input("Data inicial")
        self.seed = st.sidebar.number_input("Número de casos detectados", min_value=1)

    def fetch_healthcare_system_params(self):
        st.sidebar.header("Capacidade hospitalar")
        self.fetch_clinical_beds_params()
        self.fetch_icu_beds_params()

    def fetch_clinical_beds_params(self):
        st.sidebar.subheader("Leitos clínicos")
        self.hospital_beds_total = st.sidebar.number_input(
            "Total", min_value=0, value=int(self.region.hospital_total_capacity)
        )
        self.hospital_beds_occupancy_rate = 0.01 * st.sidebar.slider(
            "Ocupados (%)",
            min_value=0.0,
            max_value=100.0,
            value=100 * self.region.hospital_occupancy_rate,
        )

    def fetch_icu_beds_params(self):
        st.sidebar.subheader("Leitos de UTI")
        self.icu_beds_total = st.sidebar.number_input(
            "Total", min_value=0, value=int(self.region.icu_total_capacity),
            key="icu_total"
        )
        self.icu_beds_occupancy_rate = 0.01 * st.sidebar.slider(
            "Ocupados (%)",
            min_value=0.0,
            max_value=100.0,
            value=100 * self.region.icu_occupancy_rate,
            key="icu_used",
        )

    def fetch_epidemiology_params(self):
        st.sidebar.header("Epidemiologia")
        scenarios = ["Rápido", "Lento", "Personalizado"]
        self.scenario = st.sidebar.selectbox("Cenário", scenarios)

        if self.scenario == "Rápido":
            self.R0 = 3.5
        elif self.scenario == "Lento":
            self.R0 = 2.5
        else:
            self.R0 = st.sidebar.slider(
                "Fator de contágio (R0)", min_value=0.0, max_value=5.0, value=2.74
            )
            period = st.sidebar.slider(
                "Período de incubação do vírus", min_value=1.0, max_value=10.0, value=5.0
            )

            self.sigma = 1.0 / (period + e)
            period = st.sidebar.slider(
                "Período infeccioso", min_value=1.0, max_value=14.0, value=4.0
            )
            self.gamma = 1.0 / (period + e)
            self.prob_fatality = 0.01 * st.sidebar.slider(
                "Taxa de mortalidade média", min_value=0.0, max_value=100.0, value=2.0
            )

    def fetch_intervention_params(self):
        st.sidebar.header("Intervenção")
        baseline, social_distance = interventions = [
            "Nenhuma intervenção",
            "Redução de contato social",
        ]
        self.intervention = st.sidebar.selectbox("Cenário", interventions)
        if self.intervention == baseline:
            pass
        elif self.intervention == social_distance:
            # TODO: Use params
            st.sidebar.slider("Dias após data inicial para início de intervenção")
            st.sidebar.slider("Redução do fator de contágio (RO) após intervenção")

    def write_cards(self):
        st.write("""
<style>
.card-boxes dl {
}
</style>

<div class="card-boxes">
<dl>
    <dt>Data da exaustão de leitos clínicos</dt>
    <dd>16/05</dd>
</dl><dl>
    <dt>Data da exaustão de leitos de UTI com respirador</dt>
    <dd>26/04</dd>
</dl><dl>
    <dt>Respiradores faltando no dia do pico</dt>
    <dd>6946</dd>
</dl><dl>
    <dt>Leitos clínicos necessários no dia do pico</dt>
    <dd>21750</dd>
</dl><dl>
    <dt>Leitos clínicos faltando no dia do pico</dt>
    <dd>20421</dd>
</dl><dl>
    <dt>Leitos UTI com respirador necessários no dia do pico</dt>
    <dd>7099</dd>
</dl><dl>
    <dt>Leitos UTI com respirador faltando no dia do pico</dt>
    <dd>7040</dd>
</dl>
</div>
""",
        unsafe_allow_html=True,
    )

ui = CalcUI()
ui.run()
