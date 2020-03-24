from functools import lru_cache

import pandas as pd

from .cia_factbook import age_distribution
from .data import DATA


@lru_cache(1)
def covid_mortality():
    """
    Return a dataframe with COVID-19 mortality data from Neil M Ferguson, et. al.
    """
    path = DATA / 'covid-mortality-imperial-college.csv'
    return pd.read_csv(path, index_col=0) / 100


def covid_mean_mortality(region, year=2020):
    """
    Uses demography and mortality rates from NM Ferguson et. al. to infer mean
    mortality ratios for a population. Values can be plugged directly on the
    p_h, p_c and p_f parameters of a RSEICHA simulation.

    Args:
        region:
            String with country or region name or a data frame with compatible
            demography.
        year:
            Reference year (1950-2020).

    Returns:
        p_h:
            Fraction of patients that require hospitalization.
        p_c:
            Fraction of hospitalized patients that require ICUs.
        p_f:
            Fraction of critical patients that die.
    """
    if isinstance(region, str):
        df = age_distribution(region, year, coarse=True)
    else:
        df = region
    dm = covid_mortality()
    total = df.sum()

    h = dm['hospitalization']
    c = dm['icu']
    f = dm['fatality']

    p_h = (h * df).sum() / total
    p_c = (c * df).sum() / total
    p_f = (f / h / c * df).sum() / total
    return p_h, p_c, p_f
