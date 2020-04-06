from pathlib import Path
from types import SimpleNamespace

import altair as alt
import streamlit as st

import covid
from covid.utils import fmt


#
# Assets
#
@st.cache
def asset(name, mode="r"):
    path = Path(covid.__file__).parent / "ui" / "assets" / name
    with path.open(mode) as fd:
        return fd.read()


#
# Components that render HTML
#
def html(html, where=st):
    """
    Renders raw HTML string.

    Args:
        html:
            Input HTML string.
        where:
            Can be None, st or st.sidebar. If it is None, return the raw string.
    """
    mod = _mod(where)
    try:
        return mod.write(html, unsafe_allow_html=True)
    except st.StreamlitAPIException:
        return mod.markdown(html, unsafe_allow_html=True)


def card(title, data, where=st):
    """
    Render description list element representing a summary card with given
    title and datasets.
    """
    st = f'<dl class="card-box"><dt>{title}</dt><dd>{data}</dd></dl>'
    return html(st, where)


def cards(entries, where=st):
    """
    Renders mapping as a list of cards.
    """
    entries = getattr(entries, "items", lambda: entries)()
    raw = "".join(card(k, v, None) for k, v in entries)
    st = f"""<div class="card-boxes">{raw}</div>"""
    return html(st, where)


def icon(title, subtitle, where=st):
    st = f"""
<div id="sidebar-icon">
<img src="datasets:image/svg+xml;base64,
PD94bWwgdmVyc2lvbj0iMS4wIiA
/PjxzdmcgaWQ9Il94MzFfLW91dGxpbmUtZXhwYW5kIiBzdHlsZT0iZW5hYmxlLWJhY2tncm91bmQ6bmV3IDAgMCA2NCA2NDsiIHZlcnNpb249IjEuMSIgdmlld0JveD0iMCAwIDY0IDY0IiB4bWw6c3BhY2U9InByZXNlcnZlIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rIj48c3R5bGUgdHlwZT0idGV4dC9jc3MiPgoJLnN0MHtmaWxsOiMzQTQyNDk7fQo8L3N0eWxlPjxwYXRoIGNsYXNzPSJzdDAiIGQ9Ik00Ni4yLDI2LjZjLTAuOS0xLjMtMi40LTAuOC0zLjMtMC42Yy0wLjIsMC4xLTAuNCwwLjEtMC42LDAuMmMwLTAuMiwwLjEtMC40LDAuMi0wLjZjMC4zLTEsMC44LTIuNC0wLjUtMy4zICBjLTEuMi0wLjgtMi40LDAuMS0zLjIsMC43Yy0wLjEsMC4xLTAuMywwLjItMC40LDAuM2MwLTAuMiwwLTAuNCwwLTAuNWMwLTAuOS0wLjEtMi41LTEuNi0yLjljLTEuNC0wLjMtMi4yLDEtMi44LDEuOCAgYy0wLjEsMC4xLTAuMiwwLjMtMC4zLDAuNGMtMC4xLTAuMi0wLjEtMC4zLTAuMi0wLjVjLTAuNC0wLjktMC45LTIuMy0yLjUtMi4yYy0xLjUsMC4yLTEuOCwxLjctMiwyLjZjMCwwLjEtMC4xLDAuMy0wLjEsMC41ICBjLTAuMS0wLjEtMC4yLTAuMy0wLjMtMC40Yy0wLjctMC44LTEuNy0xLjktMy4xLTEuM2MtMS4zLDAuNy0xLjEsMi4yLTEsMy4yYzAsMC4yLDAuMSwwLjQsMC4xLDAuNmMtMC4yLTAuMS0wLjMtMC4yLTAuNS0wLjIgIGMtMC44LTAuNC0yLjMtMS4yLTMuNC0wLjFjLTEsMS4xLTAuMywyLjQsMC4yLDMuM2MwLjEsMC4yLDAuMiwwLjUsMC4zLDAuN2MtMC4yLDAtMC41LDAtMC43LDBjLTEtMC4xLTIuNi0wLjItMy4yLDEuMyAgYy0wLjIsMC41LDAsMS4xLDAuNSwxLjNjMC41LDAuMiwxLjEsMCwxLjMtMC41YzAuMS0wLjIsMC44LTAuMSwxLjItMC4xYzAuOSwwLjEsMiwwLjEsMi42LTAuOGMwLjYtMC45LDAuMS0yLTAuMy0yLjggIGMtMC4xLTAuMy0wLjQtMC44LTAuNC0xYzAuMiwwLDAuNywwLjMsMSwwLjRjMC44LDAuNCwxLjgsMC45LDIuNywwLjNjMC45LTAuNiwwLjgtMS44LDAuNi0yLjdjMC0wLjMtMC4xLTAuOC0wLjEtMSAgYzAuMiwwLjIsMC41LDAuNSwwLjcsMC43YzAuNiwwLjcsMS40LDEuNSwyLjQsMS4yYzEuMS0wLjMsMS4zLTEuNCwxLjUtMi4zYzAuMS0wLjMsMC4yLTAuNywwLjItMC45YzAuMSwwLjIsMC4zLDAuNiwwLjQsMC45ICBjMC4zLDAuOSwwLjgsMS45LDEuOCwyYzEuMSwwLjEsMS43LTAuOSwyLjItMS42YzAuMS0wLjIsMC40LTAuNiwwLjUtMC44YzAuMSwwLjMsMC4xLDAuNywwLjEsMWMwLDAuOSwwLjEsMi4xLDEuMSwyLjUgIGMxLDAuNSwxLjktMC4yLDIuNi0wLjhjMC4yLTAuMiwwLjYtMC41LDAuOC0wLjZjMCwwLjMtMC4yLDAuNy0wLjMsMWMtMC4zLDAuOS0wLjYsMiwwLjEsMi43YzAuOCwwLjgsMS45LDAuNSwyLjcsMC4zICBjMC4zLTAuMSwxLTAuMywxLjEtMC4zYzAsMC4yLTAuNCwwLjctMC42LDFjLTAuNSwwLjctMS4zLDEuNy0wLjgsMi43YzAuMiwwLjQsMC41LDAuNiwwLjksMC42YzAuMSwwLDAuMywwLDAuNC0wLjEgIGMwLjUtMC4yLDAuNy0wLjcsMC41LTEuMmMwLjEtMC4yLDAuMy0wLjYsMC41LTAuOEM0Ni4xLDI5LjEsNDcsMjcuOSw0Ni4yLDI2LjZ6Ii8+PHBhdGggY2xhc3M9InN0MCIgZD0iTTU2LjksNDIuOWMtMS4xLTAuNy0yLjUtMC41LTMuNCwwLjNsLTIuOC0xLjZjMS0yLDEuNy00LjEsMi4xLTYuNGw0LDAuNGwwLjItMmwtNC0wLjRjMC0wLjQsMC4xLTAuOCwwLjEtMS4yICBzMC0wLjgtMC4xLTEuMmw0LTAuNGwtMC4yLTJsLTQsMC40Yy0wLjMtMi4zLTEuMS00LjQtMi4xLTYuNGwyLjgtMS42YzAuOSwwLjgsMi4zLDEsMy40LDAuM2MxLjQtMC44LDEuOS0yLjcsMS4xLTQuMSAgcy0yLjctMS45LTQuMS0xLjFjLTEuMSwwLjctMS43LDEuOS0xLjQsMy4xbC0yLjgsMS42Yy0xLjItMS45LTIuOC0zLjYtNC41LTVsMi40LTMuM2wtMS42LTEuMmwtMi40LDMuM2MtMC43LTAuNC0xLjQtMC44LTIuMS0xLjIgIGwxLjYtMy43bC0xLjgtMC44bC0xLjYsMy43Yy0yLjEtMC44LTQuMy0xLjMtNi42LTEuNFY3LjhjMS4yLTAuNCwyLTEuNSwyLTIuOGMwLTEuNy0xLjMtMy0zLTNzLTMsMS4zLTMsM2MwLDEuMywwLjgsMi40LDIsMi44djMuMiAgYy0yLjMsMC4xLTQuNSwwLjYtNi42LDEuNGwtMS42LTMuN2wtMS44LDAuOGwxLjYsMy43Yy0wLjcsMC40LTEuNCwwLjgtMi4xLDEuMmwtMi40LTMuM2wtMS42LDEuMmwyLjQsMy4zYy0xLjgsMS40LTMuMywzLjEtNC41LDUgIEwxMS42LDE5YzAuMi0xLjItMC4zLTIuNS0xLjQtMy4xQzguNywxNS4xLDYuOCwxNS42LDYsMTdzLTAuMywzLjMsMS4xLDQuMWMxLjEsMC43LDIuNSwwLjUsMy40LTAuM2wyLjgsMS42Yy0xLDItMS43LDQuMS0yLjEsNi40ICBsLTQtMC40bC0wLjIsMmw0LDAuNGMwLDAuNC0wLjEsMC44LTAuMSwxLjJzMCwwLjgsMC4xLDEuMmwtNCwwLjRsMC4yLDJsNC0wLjRjMC4zLDIuMywxLjEsNC40LDIuMSw2LjRsLTIuOCwxLjYgIGMtMC45LTAuOC0yLjMtMS0zLjQtMC4zQzUuNyw0My43LDUuMiw0NS42LDYsNDdzMi43LDEuOSw0LjEsMS4xYzEuMS0wLjcsMS43LTEuOSwxLjQtMy4xbDIuOC0xLjZjMS4yLDEuOSwyLjgsMy42LDQuNSw1bC0yLjQsMy4zICBsMS42LDEuMmwyLjQtMy4zYzAuNywwLjQsMS40LDAuOCwyLjEsMS4ybC0xLjYsMy43bDEuOCwwLjhsMS42LTMuN2MyLjEsMC44LDQuMywxLjMsNi42LDEuNHYzLjJjLTEuMiwwLjQtMiwxLjUtMiwyLjggIGMwLDEuNywxLjMsMywzLDNzMy0xLjMsMy0zYzAtMS4zLTAuOC0yLjQtMi0yLjh2LTMuMmMyLjMtMC4xLDQuNS0wLjYsNi42LTEuNGwxLjYsMy43bDEuOC0wLjhsLTEuNi0zLjdjMC43LTAuNCwxLjQtMC44LDIuMS0xLjIgIGwyLjQsMy4zbDEuNi0xLjJsLTIuNC0zLjNjMS44LTEuNCwzLjMtMy4xLDQuNS01bDIuOCwxLjZjLTAuMiwxLjIsMC4zLDIuNSwxLjQsMy4xYzEuNCwwLjgsMy4zLDAuMyw0LjEtMS4xUzU4LjMsNDMuNyw1Ni45LDQyLjl6ICAgTTQ0LDQ2LjhsLTEuMi0xLjZsLTEuNiwxLjJsMS4yLDEuNmMtMC42LDAuNC0xLjEsMC43LTEuNywxbC0wLjgtMS44TDM4LDQ3LjlsMC44LDEuOEMzNyw1MC40LDM1LDUwLjgsMzMsNTAuOVY0OWgtMnYxLjkgIGMtMi0wLjEtNC0wLjUtNS44LTEuMmwwLjgtMS44bC0xLjgtMC44bC0wLjgsMS44Yy0wLjYtMC4zLTEuMi0wLjYtMS43LTFsMS4yLTEuNmwtMS42LTEuMkwyMCw0Ni44Yy0xLjUtMS4zLTIuOS0yLjctNC00LjRsMS43LTEgIGwtMS0xLjdsLTEuNywxYy0wLjktMS43LTEuNS0zLjYtMS44LTUuNmwxLjktMC4ybC0wLjItMkwxMy4xLDMzYzAtMC4zLTAuMS0wLjctMC4xLTFzMC0wLjcsMC4xLTFsMS45LDAuMmwwLjItMkwxMy4zLDI5ICBjMC4zLTIsMC45LTMuOSwxLjgtNS42bDEuNywxbDEtMS43bC0xLjctMWMxLjEtMS43LDIuNC0zLjIsNC00LjRsMS4yLDEuNmwxLjYtMS4ybC0xLjItMS42YzAuNi0wLjQsMS4xLTAuNywxLjctMWwwLjgsMS44bDEuOC0wLjggIGwtMC44LTEuOGMxLjgtMC43LDMuOC0xLjEsNS44LTEuMlYxNWgydi0xLjljMiwwLjEsNCwwLjUsNS44LDEuMkwzOCwxNi4xbDEuOCwwLjhsMC44LTEuOGMwLjYsMC4zLDEuMiwwLjYsMS43LDFsLTEuMiwxLjZsMS42LDEuMiAgbDEuMi0xLjZjMS41LDEuMywyLjksMi43LDQsNC40bC0xLjcsMWwxLDEuN2wxLjctMWMwLjksMS43LDEuNSwzLjYsMS44LDUuNmwtMS45LDAuMmwwLjIsMmwxLjktMC4yYzAsMC4zLDAuMSwwLjcsMC4xLDEgIHMwLDAuNy0wLjEsMUw0OSwzMi44bC0wLjIsMmwxLjksMC4yYy0wLjMsMi0wLjksMy45LTEuOCw1LjZsLTEuNy0xbC0xLDEuN2wxLjcsMUM0Ni44LDQ0LDQ1LjUsNDUuNSw0NCw0Ni44eiIvPjwvc3ZnPg==">
<span>{title}<br>{subtitle}</span>
</div>"""
    return html(st, where)


def md_description(data, where=st):
    """
    Renders a dictionary or sequence of tuples as a markdown string of associations.
    """
    data = getattr(data, "items", lambda: data)()
    md = "\n\n".join(f"**{k}**: {v}" for k, v in data)
    return _mod(where).markdown(md)


def footnote_disclaimer(lang="en_US", where=st, **kwargs):
    """
    Renders the footnote text for given language.
    """
    md = asset(f"footnote_disclaimer.{lang}.md")
    md = md.format(**kwargs)
    return _mod(where).markdown(md)


_fake_mod = SimpleNamespace(markdown=lambda x, **kwargs: x, write=lambda x, **kwargs: x)


def _mod(where):
    return where or _fake_mod


#
# Charts
#
def double_bar_chart(data, left="left", right="right", hleft=fmt, hright=fmt):
    """
    A Population pyramid chart.

    Args:
        data:
            Input dataframe
        left:
            Name of the column that will be displayed to the left.
        right:
            Name of the column that will be displayed to the right.
        hleft:
            Humanized left column or function.
        hright:
            Humanized right column or function.
    """
    cols = ["left", "right"]
    titles = [left, right]
    directions = ["descending", "ascending"]
    h_cols = [left, right]

    # Transform datasets
    data = data.copy()
    data["index"] = data.index
    data["color_left"] = "A"
    data["color_right"] = "B"

    if callable(hleft):
        data[h_cols[0]] = data["left"].apply(hleft)
    else:
        data[h_cols[0]] = hleft

    if callable(hright):
        data[h_cols[1]] = data["right"].apply(hright)
    else:
        data[h_cols[1]] = hright
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
