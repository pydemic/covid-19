import altair as alt
import pandas as pd
import streamlit as st
from babel.dates import format_date

import covid
from covid import gettext as _
from covid.models import SEICHARDemographic as SEICHAR
from covid.ui.components import cards, md_description, css
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
            _("No more ICUs by"): f"{naturaldate(c_date)}",
            _("No more hospital beds by"): f"{naturaldate(h_date)}",
        }
        cards(entries, st.write)

    def hospitalizations_chart(self, model):
        """
        Write plot of hospitalization
        """
        st.subheader(_("Hospital demand"))

        hospitalized = model["hospitalized:total"]
        icu = model["critical:total"]
        fatalities = fatality_rate(model["fatalities:total"], model.dt)
        columns = {
            _("Required hospital beds"): hospitalized.astype(int),
            _("Required ICUs"): icu.astype(int),
            _("Deaths/day"): fatalities,
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
        entries = {
            _("Total"): fmt(total),
            _("60 or more"): f"{fmt(seniors)} ({pc(seniors / total)})",
        }
        cards(entries, st.write)

    def write_age_distribution_chart(self, model):
        st.subheader(" ")
        st.subheader(_("Population pyramid"))
        data = model.region.detailed_demography
        data.columns = ["left", "right"]
        double_bar_chart(data, _("Female"), _("Male"))

    def write_fatalities_chart(self, model):
        st.subheader(" ")
        st.subheader(_("Age distribution of deaths"))
        data = model.data.loc[model.time, "fatalities"]
        data = pd.DataFrame(
            {"fatalities": data.astype(int), "pc": data.values / model.demography.values}
        )
        data.columns = ["left", "right"]
        double_bar_chart(data, _("Total deaths"), _("Mortality"), fmt, pc)

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
            },
            st.write,
        )

        if model.region.icu_total_capacity == 0:
            msg = _(
                """
The region does not have any ICU beds. At peak demand, it needs to reserve {n}
beds from neighboring cities.
"""
            )
            msg = msg.format(n=fmt(model.peak_icu_demand))
        elif model.icu_overflow_date:
            msg = _(
                """
The region will **run out of ICU beds at {date}**. At peak demand, it will need **{n}
new ICUs**. This demand corresponds to **{surge} times** the number of beds dedicated
to COVID19 and
{total} of the total number of ICU beds."""
            )
            msg = msg.format(
                date=naturaldate(model.icu_overflow_date),
                n=fmt(int(model.peak_icu_demand - model.icu_capacity)),
                surge=fmt(model.peak_icu_demand / model.icu_capacity),
                total=fmt(model.peak_icu_demand / model.icu_total_capacity),
            )
        else:
            msg = _(
                "The number of ICU beds is sufficient for the expected demand in this " "scenario."
            )

        st.markdown(msg)

    def write_epidemiological_parameters(self, model):
        st.markdown("---")
        st.subheader(_("Advanced epidemiological information"))
        mortality = pc(model.fatalities / model.population)
        fatality = pc(model.CFR())
        infected = pc(model.total_exposed / model.population)
        symptomatic = pc(model.prob_symptomatic)
        md_description(
            {
                _("Number of cases generated by a single case"): fmt(model.R0_average),
                _("Mortality ({pc} of deaths in population)").format(pc="%"): mortality,
                _("Letality ({pc} of deaths among the ill)").format(pc="%"): fatality,
            },
            st.write,
        )
        st.markdown(
            _(
                """
This scenario predicts that **{mortality}** of the whole population will die from
COVID-19. This number corresponds to **{fatality}** of those that became ill.
The model also predicts that **{infected}** of the population will become
infected, but only **{symptomatic}** of those will develop visible symptoms. People who
do not exhibit symptoms are still able to infect others.

**IMPORTANT:** Models are simplifications and are highly dependent on good
parameters and good data. There are many aspects of COVID epidemiology that are
yet not very well understood and scientists are still looking for more accurate
values for many important parameters. The choices made here are best guesses
based on the current scientific knowledge about the epidemic. Changing
parameters to absurd values will create absurd predictions, so use with care.

The course of the epidemic also depends crucially on how communities react. This is
encoded in a very simplified way in by the "intervention options" in the simulator.
We do not try to anticipate communities respond to the epidemic, but rather it
must be entered as an explicit input to the model. That is why we say this calculator
computes scenarios rather than trying to predict the future.
"""
            ).format(**locals())
        )

    def write_footnotes(self, *args):
        """Write footnotes"""

        template = '<a href="{href}">{name}</a>'
        links = _("Kind support: {paho}, {lappis}, {nmt}, {fce}").format(
            paho=template.format(
                href=_("https://www.paho.org/hq/index.php?lang=en"), name=_("PAHO")
            ),
            lappis=template.format(href=_("https://lappis.rocks"), name=_("UnB/LAPPIS")),
            nmt=template.format(href=_("http://medicinatropical.unb.br/"), name=_("UnB/NMT")),
            fce=template.format(href=_("http://fce.unb.br/"), name=_("UnB/FCE")),
        )
        styles = "text-align: center; margin: 5rem 0 -5rem 0;"
        st.write(f'<div style="{styles}">{links}</div>', unsafe_allow_html=True)


def fatality_rate(fs, dt=1):
    fs = fs.copy()
    fs.iloc[:-1] -= fs.values[1:]
    fs /= -dt
    fs.iloc[-1] = fs.iloc[-2]
    return fs.apply(lambda x: round(x, 1))


def write_css():
    st.write(css(), unsafe_allow_html=True)


def double_bar_chart(data, left, right, hleft=fmt, hright=fmt):
    cols = ["left", "right"]
    titles = [left, right]
    directions = ["descending", "ascending"]
    h_cols = [left, right]

    # Transform data
    data = data.copy()
    data["index"] = data.index
    data["color_left"] = "A"
    data["color_right"] = "B"
    data[h_cols[0]] = data["left"].apply(hleft)
    data[h_cols[1]] = data["right"].apply(hright)
    data = data.loc[::-1]

    # Chart
    base = alt.Chart(data)
    height = 250
    width = 300

    def piece(i):
        return (
            base.mark_bar()
            .encode(
                x=alt.X(cols[i], title=None, sort=alt.SortOrder(directions[i])),
                y=alt.Y("index", axis=None, title=None, sort=alt.SortOrder("descending")),
                tooltip=alt.Tooltip([h_cols[i]]),
                color=alt.Color(f"color_{cols[i]}:N", legend=None),
            )
            .properties(title=titles[i], width=width, height=height)
            .interactive()
        )

    st.altair_chart(
        alt.concat(
            piece(0),
            base.encode(
                y=alt.Y("index", axis=None, sort=alt.SortOrder("descending")),
                text=alt.Text("index"),
            )
            .mark_text()
            .properties(width=50, height=height),
            piece(1),
            spacing=5,
        ),
        use_container_width=False,
    )


if __name__ == "__main__":
    region = covid.region("Brazil")
    model = SEICHAR(region=region, prob_symptomatic=0.5, seed=1000)
    model.run(180)

    write_css()
    app = Output(model)
    app.run()
