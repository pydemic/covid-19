import pandas as pd
import streamlit as st

import covid
from covid.models import SEICHARDemographic as SEICHAR
from covid.ui.components import cards, md_description, css
from covid.utils import fmt, pc


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
        h_date = model.hospital_overflow_date or "Nunca"
        c_date = model.icu_overflow_date or "Nunca"
        missing_icu = max(int(model.peak_icu_demand - model.icu_capacity), 0)
        missing_hospital = max(int(model.peak_hospitalization_demand - model.hospital_capacity), 0)

        entries = {
            "Exaustão dos leitos clínicos": f"{h_date}",
            "Exaustão de leitos de UTI": f"{c_date}",
            "Leitos UTI faltando no dia do pico": f"{fmt(missing_icu)}",
            "Leitos clínicos faltando no dia do pico": f"{fmt(missing_hospital)}",
            "Fatalidades": f"{fmt(int(model.fatalities))} "
            f"({pc(model.fatalities / model.initial_population)})",
            "Contaminados": f"{fmt(int(contaminated))} "
            f"({pc(contaminated / model.initial_population)})",
        }
        cards(entries, st.write)

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

        columns = {"Leitos disponíveis": available_beds, "Leitos de UTI disponíveis": available_icu}
        df = model.get_dates(pd.DataFrame(columns))

        st.line_chart(df)

    def write_info(self, model: SEICHAR):
        """Write additional information about the model."""

        # Demography
        st.subheader("População")
        seniors = model.demography.loc["60-69":].sum()
        total = model.population
        entries = {
            "Total": fmt(total),
            "60 anos ou mais": f"{fmt(seniors)} ({pc(seniors / total)})",
        }
        cards(entries, st.write)
        st.markdown("`_`\n\n**Distribuição de idades**")
        st.bar_chart(model.demography)
        st.markdown("` `\n\n**Fatalidades por idade**")
        st.bar_chart(model.data.loc[model.time, "fatalities"].astype(int))

        # Epidemiological parameters
        st.subheader("Epidemiologia")
        md_description(
            {
                "R0 médio": fmt(model.R0_average),
                "Fatalidade (infectados, IFR)": pc(model.IFR()),
                "Fatalidade (casos, CFR)": pc(model.CFR()),
            },
            st.write,
        )

        # Healthcare parameters
        fpc = lambda x: "x " + fmt(x) if x > 1.0 else pc(x)
        icu_surge_overload = model.peak_icu_demand / model.icu_capacity
        icu_overload = model.peak_icu_demand / model.icu_total_capacity
        surge_overload = model.peak_hospitalization_demand / model.hospital_capacity
        overload = model.peak_hospitalization_demand / model.hospital_total_capacity

        st.subheader("Sistema de saúde")
        md_description(
            {
                "Sobrecarga de UTI": fpc(icu_surge_overload),
                "Da capacidade total de UTI": fpc(icu_overload),
                "Sobrecarga de Leitos": fpc(surge_overload),
                "Da capacidade total de leitos": fpc(overload),
            },
            st.write,
        )


def fatality_rate(fs, dt=1):
    fs = fs.copy()
    fs.iloc[:-1] -= fs.values[1:]
    fs /= -dt
    fs.iloc[-1] = fs.iloc[-2]
    return fs.apply(lambda x: round(x, 1))


def write_css():
    st.write(css(), unsafe_allow_html=True)


if __name__ == "__main__":
    region = covid.region("Brazil")
    model = SEICHAR(region=region, prob_symptomatic=0.5, seed=1000)
    model.run(180)

    write_css()
    app = Output(model)
    app.run()
