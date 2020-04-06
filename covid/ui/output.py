import os

import pandas as pd
import streamlit as st
from babel.dates import format_date

import covid
from covid import gettext as _
from covid.models import SEICHARDemographic as SEICHAR
from covid.ui.components import (
    cards,
    md_description,
    asset,
    double_bar_chart,
    html,
    footnote_disclaimer,
)
from covid.utils import fmt, pc

naturaldate = lambda d: format_date(d, format="short") if d else _("Not soon...")


class Output:
    def __init__(self, model):
        self.model = model

    def run(self):
        """
        Show all outputs for the given simulated model.
        """
        model = self.model
        self.summary_cards(model)
        self.hospitalizations_chart(model)
        self.available_beds_chart(model)
        self.write_population_info(model)
        self.write_age_distribution_chart(model)
        self.write_fatalities_chart(model)
        self.write_healthcare_parameters(model)
        self.write_protection_equipment_demand(model)
        self.write_epidemiological_parameters(model)
        self.write_footnotes(model)

    def summary_cards(self, model: SEICHAR):
        """
        Show list of summary cards for the results of simulation.
        """

        # Which one?
        df = model.data["infectious"] * model.gamma_i * model.prob_hospitalization
        hospitalized = df.apply(model.integral).sum()

        h_date = model.hospital_overflow_date
        c_date = model.icu_overflow_date
        missing_icu = max(int(model.peak_icu_demand - model.icu_capacity), 0)
        missing_hospital = max(int(model.peak_hospitalization_demand - model.hospital_capacity), 0)
        fatalities_pc = pc(model.fatalities / model.initial_population)
        hospitalized_pc = pc(hospitalized / model.initial_population)

        entries = {
            _("Deaths"): f"{fmt(int(model.fatalities))} ({fatalities_pc})",
            _("Hospitalizations"): f"{fmt(int(hospitalized))} ({hospitalized_pc})",
            _("Required extra ICU beds"): f"{fmt(missing_icu)}",
            _("Required extra hospital beds"): f"{fmt(missing_hospital)}",
            _("No more ICU beds available by"): f"{naturaldate(c_date)}",
            _("No more hospital beds available by"): f"{naturaldate(h_date)}",
        }
        cards(entries)

    def hospitalizations_chart(self, model):
        """
        Write plot of hospitalization
        """
        st.subheader(_("Hospital demand"))

        hospitalized = model["hospitalized:total"]
        icu = model["critical:total"]
        fatalities = fatality_rate(model["fatalities:total"], model.dt)
        columns = {
            _("Deaths/day"): fatalities,
            _("Required hospital beds"): hospitalized.astype(int),
            _("Required ICU beds"): icu.astype(int),
        }
        df = model.get_dates(pd.DataFrame(columns))

        st.area_chart(df)

    def available_beds_chart(self, model):
        """
        Write plot of available beds.
        """
        st.subheader(_("Available hospital beds"))

        hospitalized = model["hospitalized:total"]
        icu = model["critical:total"]

        available_beds = model.hospital_capacity - hospitalized
        available_beds[available_beds < 0] = 0

        available_icu = model.icu_capacity - icu
        available_icu[available_icu < 0] = 0

        columns = {_("Regular"): available_beds, _("ICU"): available_icu}
        df = model.get_dates(pd.DataFrame(columns))

        st.line_chart(df)

    def write_population_info(self, model: SEICHAR):
        """Write additional information about the model."""

        # Demography
        st.subheader(_("Population"))
        seniors = model.demography.loc["60-69":].sum()
        total = model.population
        entries = {_("Total"): fmt(total), _("Age 60+"): f"{fmt(seniors)} ({pc(seniors / total)})"}
        cards(entries)

    def write_age_distribution_chart(self, model):
        st.subheader(" ")
        st.subheader(_("Population pyramid"))
        data = model.region.detailed_demography
        data.columns = ["left", "right"]
        double_bar_chart(data, _("Female"), _("Male"))

    def write_fatalities_chart(self, model):
        st.subheader(" ")
        st.subheader(_("Anticipated age distribution of COVID deaths"))
        data = model.data.loc[model.time, "fatalities"]
        data = pd.DataFrame(
            {
                "fatalities": data.astype(int),
                "pc": (1e5 * data.values / model.demography.values).astype(int),
            }
        )
        data.columns = ["left", "right"]
        double_bar_chart(data, _("Total deaths"), _("Mortality per 100k"))

    def write_healthcare_parameters(self, model):
        st.markdown("---")
        st.subheader(_("Healthcare system"))

        r = model.region
        md_description(
            {
                _("COVID ICUs"): fmt(int(model.icu_capacity)),
                _("COVID hospital beds"): fmt(int(model.hospital_capacity)),
                _("ICUs"): _("{n} (source: CNES)").format(n=fmt(r.icu_total_capacity)),
                _("Hospital beds"): _("{n} (source: CNES)").format(
                    n=fmt(r.hospital_total_capacity)
                ),
            }
        )

        if model.region.icu_total_capacity == 0:
            msg = _(
                """
The location does not have any ICU beds. At peak demand, it needs to reserve {n}
beds from neighboring cities.
"""
            )
            msg = msg.format(n=fmt(model.peak_icu_demand))
        elif model.icu_overflow_date:
            msg = _(
                """
The location will **run out of ICU beds at {date}**. At peak demand, it will need **{n}
new ICUs**. This demand corresponds to **{surge} times** the number of beds dedicated
to COVID-19 and {total} of the total number of ICU beds.
"""
            )
            msg = msg.format(
                date=naturaldate(model.icu_overflow_date),
                n=fmt(int(model.peak_icu_demand - model.icu_capacity)),
                surge=fmt(model.peak_icu_demand / model.icu_capacity),
                total=fmt(model.peak_icu_demand / model.icu_total_capacity),
            )
        else:
            msg = _(
                """
The number of ICU beds is sufficient for the expected demand in this scenario.
"""
            )

        st.markdown(msg)

    def write_protection_equipment_demand(self, model):
        st.markdown("---")
        st.subheader(_("Protection equipment"))
        df = model.health_resources(translate=_)

        df[df.columns[1]] = df[df.columns[1]].apply(fmt)
        st.table(df)

    def write_epidemiological_parameters(self, model):
        st.markdown("---")
        st.subheader(_("Advanced epidemiological information"))

        mortality = fmt(1e5 * model.fatalities / model.population)
        fatality = pc(model.CFR())
        infected = pc(model.total_exposed / model.population)
        symptomatic = pc(model.prob_symptomatic)

        md_description(
            {
                _("Number of cases generated by a single case"): fmt(model.R0_average),
                _("Mortality (deaths per 100k population)"): mortality,
                _("Letality ({pc} of deaths among the ill)").format(pc="%"): fatality,
            }
        )
        lang = os.environ.get("LANGUAGE", "en_US")
        footnote_disclaimer(**locals())

    def write_footnotes(self, *args):
        """Write footnotes"""

        template = '<a href="{href}">{name}</a>'
        institutions = [
            template.format(href=_("https://www.paho.org/hq/index.php?lang=en"), name=_("PAHO")),
            template.format(href="https://saude.gov.br/", name="MS/SVS"),
            template.format(href="https://lappis.rocks", name="UnB/LAPPIS"),
            template.format(href="http://medicinatropical.unb.br/", name="UnB/NMT"),
            template.format(href="http://fce.unb.br/", name="UnB/FCE"),
            template.format(href="http://www.butantan.gov.br/", name="Butantã"),
            template.format(href="http://www.matogrossodosul.fiocruz.br/", name="Fiocruz"),
            template.format(href="https://famed.ufms.br/", name="FAMED"),
        ]
        links = _("Support: {institutions}").format(institutions=", ".join(institutions))
        styles = "text-align: center; margin: 5rem 0 -5rem 0;"
        html(f'<div style="{styles}">{links}</div>')


def fatality_rate(fs, dt=1):
    fs = fs.copy()
    fs.iloc[:-1] -= fs.values[1:]
    fs /= -dt
    fs.iloc[-1] = fs.iloc[-2]
    return fs.apply(lambda x: round(x, 1))


def write_css():
    html(asset("custom.html"))


if __name__ == "__main__":
    region = covid.region("Brazil")
    model = SEICHAR(region=region, prob_symptomatic=0.5, seed=1000)
    model.run(180)

    write_css()
    app = Output(model)
    app.run()
