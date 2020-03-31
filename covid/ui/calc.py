from contextlib import contextmanager
from pathlib import Path

import pandas as pd
import streamlit as st

import covid
from covid.models import SEICHARDemographic as SEICHAR
from covid.utils import fmt, pc
from covid.ui.input import Input

COUNTRY = "Brazil"
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
    title = "Pressão assistencial devido à COVID-19"

    def __init__(self, country=COUNTRY):
        st.write(css(), unsafe_allow_html=True)
        st.title(self.title)
        self._info = st.text("")
        self.country = country
        self.input = Input(self.country)

    @contextmanager
    def info(self, st):
        """
        Context manager that displays info text while code inside the with
        block is being executed and clear it afterwards.
        """
        self._info.text(st)
        yield
        self._info.text('')

    def run(self):
        """
        Run streamlit app.
        """
        icon = """
        <div id="sidebar-icon">
        <img src="data:image/svg+xml;base64,
        PD94bWwgdmVyc2lvbj0iMS4wIiA
        /PjxzdmcgaWQ9Il94MzFfLW91dGxpbmUtZXhwYW5kIiBzdHlsZT0iZW5hYmxlLWJhY2tncm91bmQ6bmV3IDAgMCA2NCA2NDsiIHZlcnNpb249IjEuMSIgdmlld0JveD0iMCAwIDY0IDY0IiB4bWw6c3BhY2U9InByZXNlcnZlIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rIj48c3R5bGUgdHlwZT0idGV4dC9jc3MiPgoJLnN0MHtmaWxsOiMzQTQyNDk7fQo8L3N0eWxlPjxwYXRoIGNsYXNzPSJzdDAiIGQ9Ik00Ni4yLDI2LjZjLTAuOS0xLjMtMi40LTAuOC0zLjMtMC42Yy0wLjIsMC4xLTAuNCwwLjEtMC42LDAuMmMwLTAuMiwwLjEtMC40LDAuMi0wLjZjMC4zLTEsMC44LTIuNC0wLjUtMy4zICBjLTEuMi0wLjgtMi40LDAuMS0zLjIsMC43Yy0wLjEsMC4xLTAuMywwLjItMC40LDAuM2MwLTAuMiwwLTAuNCwwLTAuNWMwLTAuOS0wLjEtMi41LTEuNi0yLjljLTEuNC0wLjMtMi4yLDEtMi44LDEuOCAgYy0wLjEsMC4xLTAuMiwwLjMtMC4zLDAuNGMtMC4xLTAuMi0wLjEtMC4zLTAuMi0wLjVjLTAuNC0wLjktMC45LTIuMy0yLjUtMi4yYy0xLjUsMC4yLTEuOCwxLjctMiwyLjZjMCwwLjEtMC4xLDAuMy0wLjEsMC41ICBjLTAuMS0wLjEtMC4yLTAuMy0wLjMtMC40Yy0wLjctMC44LTEuNy0xLjktMy4xLTEuM2MtMS4zLDAuNy0xLjEsMi4yLTEsMy4yYzAsMC4yLDAuMSwwLjQsMC4xLDAuNmMtMC4yLTAuMS0wLjMtMC4yLTAuNS0wLjIgIGMtMC44LTAuNC0yLjMtMS4yLTMuNC0wLjFjLTEsMS4xLTAuMywyLjQsMC4yLDMuM2MwLjEsMC4yLDAuMiwwLjUsMC4zLDAuN2MtMC4yLDAtMC41LDAtMC43LDBjLTEtMC4xLTIuNi0wLjItMy4yLDEuMyAgYy0wLjIsMC41LDAsMS4xLDAuNSwxLjNjMC41LDAuMiwxLjEsMCwxLjMtMC41YzAuMS0wLjIsMC44LTAuMSwxLjItMC4xYzAuOSwwLjEsMiwwLjEsMi42LTAuOGMwLjYtMC45LDAuMS0yLTAuMy0yLjggIGMtMC4xLTAuMy0wLjQtMC44LTAuNC0xYzAuMiwwLDAuNywwLjMsMSwwLjRjMC44LDAuNCwxLjgsMC45LDIuNywwLjNjMC45LTAuNiwwLjgtMS44LDAuNi0yLjdjMC0wLjMtMC4xLTAuOC0wLjEtMSAgYzAuMiwwLjIsMC41LDAuNSwwLjcsMC43YzAuNiwwLjcsMS40LDEuNSwyLjQsMS4yYzEuMS0wLjMsMS4zLTEuNCwxLjUtMi4zYzAuMS0wLjMsMC4yLTAuNywwLjItMC45YzAuMSwwLjIsMC4zLDAuNiwwLjQsMC45ICBjMC4zLDAuOSwwLjgsMS45LDEuOCwyYzEuMSwwLjEsMS43LTAuOSwyLjItMS42YzAuMS0wLjIsMC40LTAuNiwwLjUtMC44YzAuMSwwLjMsMC4xLDAuNywwLjEsMWMwLDAuOSwwLjEsMi4xLDEuMSwyLjUgIGMxLDAuNSwxLjktMC4yLDIuNi0wLjhjMC4yLTAuMiwwLjYtMC41LDAuOC0wLjZjMCwwLjMtMC4yLDAuNy0wLjMsMWMtMC4zLDAuOS0wLjYsMiwwLjEsMi43YzAuOCwwLjgsMS45LDAuNSwyLjcsMC4zICBjMC4zLTAuMSwxLTAuMywxLjEtMC4zYzAsMC4yLTAuNCwwLjctMC42LDFjLTAuNSwwLjctMS4zLDEuNy0wLjgsMi43YzAuMiwwLjQsMC41LDAuNiwwLjksMC42YzAuMSwwLDAuMywwLDAuNC0wLjEgIGMwLjUtMC4yLDAuNy0wLjcsMC41LTEuMmMwLjEtMC4yLDAuMy0wLjYsMC41LTAuOEM0Ni4xLDI5LjEsNDcsMjcuOSw0Ni4yLDI2LjZ6Ii8+PHBhdGggY2xhc3M9InN0MCIgZD0iTTU2LjksNDIuOWMtMS4xLTAuNy0yLjUtMC41LTMuNCwwLjNsLTIuOC0xLjZjMS0yLDEuNy00LjEsMi4xLTYuNGw0LDAuNGwwLjItMmwtNC0wLjRjMC0wLjQsMC4xLTAuOCwwLjEtMS4yICBzMC0wLjgtMC4xLTEuMmw0LTAuNGwtMC4yLTJsLTQsMC40Yy0wLjMtMi4zLTEuMS00LjQtMi4xLTYuNGwyLjgtMS42YzAuOSwwLjgsMi4zLDEsMy40LDAuM2MxLjQtMC44LDEuOS0yLjcsMS4xLTQuMSAgcy0yLjctMS45LTQuMS0xLjFjLTEuMSwwLjctMS43LDEuOS0xLjQsMy4xbC0yLjgsMS42Yy0xLjItMS45LTIuOC0zLjYtNC41LTVsMi40LTMuM2wtMS42LTEuMmwtMi40LDMuM2MtMC43LTAuNC0xLjQtMC44LTIuMS0xLjIgIGwxLjYtMy43bC0xLjgtMC44bC0xLjYsMy43Yy0yLjEtMC44LTQuMy0xLjMtNi42LTEuNFY3LjhjMS4yLTAuNCwyLTEuNSwyLTIuOGMwLTEuNy0xLjMtMy0zLTNzLTMsMS4zLTMsM2MwLDEuMywwLjgsMi40LDIsMi44djMuMiAgYy0yLjMsMC4xLTQuNSwwLjYtNi42LDEuNGwtMS42LTMuN2wtMS44LDAuOGwxLjYsMy43Yy0wLjcsMC40LTEuNCwwLjgtMi4xLDEuMmwtMi40LTMuM2wtMS42LDEuMmwyLjQsMy4zYy0xLjgsMS40LTMuMywzLjEtNC41LDUgIEwxMS42LDE5YzAuMi0xLjItMC4zLTIuNS0xLjQtMy4xQzguNywxNS4xLDYuOCwxNS42LDYsMTdzLTAuMywzLjMsMS4xLDQuMWMxLjEsMC43LDIuNSwwLjUsMy40LTAuM2wyLjgsMS42Yy0xLDItMS43LDQuMS0yLjEsNi40ICBsLTQtMC40bC0wLjIsMmw0LDAuNGMwLDAuNC0wLjEsMC44LTAuMSwxLjJzMCwwLjgsMC4xLDEuMmwtNCwwLjRsMC4yLDJsNC0wLjRjMC4zLDIuMywxLjEsNC40LDIuMSw2LjRsLTIuOCwxLjYgIGMtMC45LTAuOC0yLjMtMS0zLjQtMC4zQzUuNyw0My43LDUuMiw0NS42LDYsNDdzMi43LDEuOSw0LjEsMS4xYzEuMS0wLjcsMS43LTEuOSwxLjQtMy4xbDIuOC0xLjZjMS4yLDEuOSwyLjgsMy42LDQuNSw1bC0yLjQsMy4zICBsMS42LDEuMmwyLjQtMy4zYzAuNywwLjQsMS40LDAuOCwyLjEsMS4ybC0xLjYsMy43bDEuOCwwLjhsMS42LTMuN2MyLjEsMC44LDQuMywxLjMsNi42LDEuNHYzLjJjLTEuMiwwLjQtMiwxLjUtMiwyLjggIGMwLDEuNywxLjMsMywzLDNzMy0xLjMsMy0zYzAtMS4zLTAuOC0yLjQtMi0yLjh2LTMuMmMyLjMtMC4xLDQuNS0wLjYsNi42LTEuNGwxLjYsMy43bDEuOC0wLjhsLTEuNi0zLjdjMC43LTAuNCwxLjQtMC44LDIuMS0xLjIgIGwyLjQsMy4zbDEuNi0xLjJsLTIuNC0zLjNjMS44LTEuNCwzLjMtMy4xLDQuNS01bDIuOCwxLjZjLTAuMiwxLjIsMC4zLDIuNSwxLjQsMy4xYzEuNCwwLjgsMy4zLDAuMyw0LjEtMS4xUzU4LjMsNDMuNyw1Ni45LDQyLjl6ICAgTTQ0LDQ2LjhsLTEuMi0xLjZsLTEuNiwxLjJsMS4yLDEuNmMtMC42LDAuNC0xLjEsMC43LTEuNywxbC0wLjgtMS44TDM4LDQ3LjlsMC44LDEuOEMzNyw1MC40LDM1LDUwLjgsMzMsNTAuOVY0OWgtMnYxLjkgIGMtMi0wLjEtNC0wLjUtNS44LTEuMmwwLjgtMS44bC0xLjgtMC44bC0wLjgsMS44Yy0wLjYtMC4zLTEuMi0wLjYtMS43LTFsMS4yLTEuNmwtMS42LTEuMkwyMCw0Ni44Yy0xLjUtMS4zLTIuOS0yLjctNC00LjRsMS43LTEgIGwtMS0xLjdsLTEuNywxYy0wLjktMS43LTEuNS0zLjYtMS44LTUuNmwxLjktMC4ybC0wLjItMkwxMy4xLDMzYzAtMC4zLTAuMS0wLjctMC4xLTFzMC0wLjcsMC4xLTFsMS45LDAuMmwwLjItMkwxMy4zLDI5ICBjMC4zLTIsMC45LTMuOSwxLjgtNS42bDEuNywxbDEtMS43bC0xLjctMWMxLjEtMS43LDIuNC0zLjIsNC00LjRsMS4yLDEuNmwxLjYtMS4ybC0xLjItMS42YzAuNi0wLjQsMS4xLTAuNywxLjctMWwwLjgsMS44bDEuOC0wLjggIGwtMC44LTEuOGMxLjgtMC43LDMuOC0xLjEsNS44LTEuMlYxNWgydi0xLjljMiwwLjEsNCwwLjUsNS44LDEuMkwzOCwxNi4xbDEuOCwwLjhsMC44LTEuOGMwLjYsMC4zLDEuMiwwLjYsMS43LDFsLTEuMiwxLjZsMS42LDEuMiAgbDEuMi0xLjZjMS41LDEuMywyLjksMi43LDQsNC40bC0xLjcsMWwxLDEuN2wxLjctMWMwLjksMS43LDEuNSwzLjYsMS44LDUuNmwtMS45LDAuMmwwLjIsMmwxLjktMC4yYzAsMC4zLDAuMSwwLjcsMC4xLDEgIHMwLDAuNy0wLjEsMUw0OSwzMi44bC0wLjIsMmwxLjksMC4yYy0wLjMsMi0wLjksMy45LTEuOCw1LjZsLTEuNy0xbC0xLDEuN2wxLjcsMUM0Ni44LDQ0LDQ1LjUsNDUuNSw0NCw0Ni44eiIvPjwvc3ZnPg==">
        <span>OPAS - COVID-19<br>Calculadora Epidêmica</span>
        </div>
        """
        st.sidebar.markdown(icon, unsafe_allow_html=True)
        with self.info("Carregando região..."):
            region = self.input.region()
            self.input.pause()
        with self.info("Carregando parâmetros de simulação..."):
            kwargs = {'region': region, **self.input.params(region)}
        with self.info("Executando a simulação..."):
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

    def card(self, title, data) -> str:
        """
        Render description list element representing a summary card with given
        title and data.
        """
        return f'<dl class="card-box"><dt>{title}</dt><dd>{data}</dd></dl>'

    def cards(self, data: dict) -> str:
        """
        Renders mapping as a list of cards.
        """
        raw = ''.join(self.card(k, v) for k, v in data.items())
        return f"""<div class="card-boxes">{raw}</div>"""

    def summary_cards(self, model: SEICHAR):
        """
        Show list of summary cards for the results of simulation.
        """
        contaminated = model.initial_population - model.susceptible
        h_date = model.hospital_overflow_date or 'Nunca'
        c_date = model.icu_overflow_date or 'Nunca'
        missing_icu = max(int(model.peak_icu_demand - model.icu_capacity), 0)
        missing_hospital = max(
            int(model.peak_hospitalization_demand - model.hospital_capacity), 0)
        entries = {
            'Exaustão dos leitos clínicos': f'{h_date}',
            'Exaustão de leitos de UTI': f'{c_date}',
            'Leitos UTI faltando no dia do pico': f'{fmt(missing_icu)}',
            'Leitos clínicos faltando no dia do pico': f'{fmt(missing_hospital)}',
            'Fatalidades': f'{fmt(int(model.fatalities))} '
                           f'({pc(model.fatalities / model.initial_population)})',
            'Contaminados': f'{fmt(int(contaminated))} '
                            f'({pc(contaminated / model.initial_population)})',
        }
        st.write(self.cards(entries), unsafe_allow_html=True)

    def hospitalizations_plot(self, model):
        """
        Write plot of hospitalization
        """
        st.subheader("Quadros de internação")

        hospitalized = model["hospitalized:total"]
        icu = model["critical:total"]
        fatalities = fatality_rate(model["fatalities:total"], model.dt)
        columns = {
            "Internações clínicas": hospitalized.astype(int),
            "Internações UTI": icu.astype(int),
            "Fatalidades/dia": fatalities,
        }
        df = model.get_dates(pd.DataFrame(columns))

        st.area_chart(df)

    def available_beds_chart(self, model):
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

        columns = {
            "Leitos disponíveis": available_beds,
            "Leitos de UTI disponíveis": available_icu,
        }
        df = model.get_dates(pd.DataFrame(columns))

        st.line_chart(df)

    def write_info(self, model):
        """Write additional information about the model."""
        st.subheader("Informações adicionais")
        entries = {
            'Exaustão dos leitos clínicos': model.hospital_overflow_date,
            'Exaustão de leitos de UTI': model.icu_overflow_date,
            'Leitos UTI faltando no dia do pico': fmt(
                int(model.peak_icu_demand - model.icu_capacity)),
            'Leitos clínicos faltando no dia do pico': fmt(
                int(model.peak_hospitalization_demand - model.hospital_capacity)),
        }
        st.write(self.cards(entries), unsafe_allow_html=True)


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
