"""
Import data sets from various sources.
"""
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA = Path(__file__).parent / 'datasets'


@lru_cache(8)
def cia_factbook(which):
    """
    Import dataset from CIA factbook spreadsheets.

    Valid datasets:
    * 'age distributions'
    """
    if which == 'age distribution':
        df = pd.read_csv(DATA / 'cia_factbook-age_distribution.csv', index_col=0)
        return df
    else:
        raise ValueError(f'invalid dataset: {which}')


@lru_cache(8)
def age_distribution(region: str, year: int, coarse: bool = False) -> pd.Series:
    """
    Load a series object with age distribution for given country in the given
    year.

    Examples:
        >>> series = age_distribution('Brazil', 2020)
        >>> series.sum() > 209_000
        True

    Args:
        region:
            String with country or region name.
        year:
            Reference year (1950-2020).
        coarse:
            If True, reduce the number of bins to be compatible with data from
            :func:`covid_mortality` function.
    """
    df = cia_factbook('age distribution')
    data = df[(df.region == region) & (df.ref_date == year)]
    if data.shape[0] == 0:
        raise ValueError(f'Invalid country/year: {region!r} / {year!r}')
    data = data.loc[:, '0-4':].T
    data.index.name = 'age'
    data = data.iloc[:, 0].apply(int)

    return coarse_age_distribution(data) if coarse else data


@lru_cache(1)
def hospital_bed_density(country=None):
    """
    Return a data frame with hospital bed density per country or a single number
    with hospital bed density for a given country.

    >>> hospital_bed_density('Brazil')
    2.3
    >>> hospital_bed_density()
    ...
    """
    path = DATA / 'cia_factbook-hospital_bed_density.csv'
    df = pd.read_csv(path, index_col=0, sep=';')
    df['density'] /= 1000
    if country:
        return df.loc[country, 'density']
    return df


def coarse_age_distribution(df: pd.Series) -> pd.Series:
    """
    Convert the CIA factbook age distribution dataframe to a coarser form
    that is compatible with the output of :func:`covid_mortality`.

    Args:
        df: Input age distribution data set.
    """
    xs = list(df.index)
    ranges = list(zip(xs[::2], xs[1::2]))
    last = ranges.pop()
    ranges[-1] = (*ranges[-1], *last, xs[-1])

    data = {}
    for cat in map(list, ranges):
        total = df.T[cat].sum()
        start = cat[0].split('-')[0]
        end = cat[-1].split('-')[-1]
        data[f'{start}-{end}'] = total

    data['80+'] = data.pop('80-100+')
    data = pd.Series(data)
    data.index.name = 'age'

    return data


def covid_mortality():
    """
    Return a dataframe with COVID-19 mortality data from Neil M Ferguson, et. al.
    """
    path = DATA / 'covid-mortality-imperial-college.csv'
    return pd.read_csv(path, index_col=0) / 100


def covid_mean_mortality(region, year):
    """
    Uses demography and mortality rates from NM Ferguson et. al. to infer mean
    mortality ratios for a population. Values can be plugged directly on the
    p_h, p_c and p_f parameters of a RSEICHA simulation.

    Args:
        region:
            String with country or region name.
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
    df = age_distribution(region, year, coarse=True)
    dm = covid_mortality()
    total = df.sum()

    h = dm['hospitalization']
    c = dm['icu']
    f = dm['fatality']

    p_h = (h * df).sum() / total
    p_c = (c * df).sum() / total
    p_f = (f / h / c * df).sum() / total
    return p_h, p_c, p_f


def brazil_healthcare_capacity():
    """
    Return data from Brazilian hospitals capacity.
    """
    path = DATA / 'brazil_healthcare_capacity.csv'
    df = pd.read_csv(path, index_col=0)
    return df


def contact_matrix(country='mean', physical=False):
    """
    Load contact matrix for country.
    """
    which = 'physical' if physical else 'all'
    path = DATA / 'contact_matrix' / f'{country.lower()}-{which}.csv'
    df = pd.read_csv(path, index_col=0)
    return df
