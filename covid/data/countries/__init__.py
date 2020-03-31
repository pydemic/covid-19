from functools import lru_cache

import pandas as pd

from ..data import DATA_PATH
from ...utils import lru_safe_cache


@lru_safe_cache(64)
def states(country: str, extra=False) -> pd.DataFrame:
    """
    Return a data frame with all states from a given country. Official state
    codes assigned by the official geographic institute of a country are
    in the index. If there is no such convention, it index states sequentially
    by alphabetic order.

    It return [name, code] columns, in which code is the usual small 2-3 letter
    abbreviations. If extra=True, it may append additional country-specific
    columns.
    """

    if not extra:
        return states(country, True)[['name', 'code']]

    path = DATA_PATH / "countries" / country / "states.csv"
    return pd.read_csv(path, index_col=0)


@lru_cache(128)
def state_codes(country):
    """
    Return a tuple with all state codes for country.
    """
    df = states.unsafe(country)
    return tuple(sorted(df['code']))


@lru_safe_cache(64)
def sub_regions(country: str, state=None) -> pd.DataFrame:
    """
    Return a data frame with the next sub-division after state level for the
    given country.

    Data frame has ['name', 'state_id', 'state_code'] columns and the index can
    be either sequential or correspond to the special code assigned by the
    official geographic institute of the given country.
    """

    if state:
        df = sub_regions.unsafe(country)
        return df[df['state'] == state]
    path = DATA_PATH / "countries" / country / "sub-regions.csv"
    return pd.read_csv(path, index_col=0)


@lru_safe_cache(64)
def cities(country: str, extra=False) -> pd.DataFrame:
    """
    Return a data frame with all cities or municipalities in a country.

    Data frame has ['name', 'sub_region', 'state_id', 'state_code'] columns
    and the index can be either sequential or the special code assigned by the
    geography institute of the given country.
    """

    path = DATA_PATH / "countries" / country / "cities.csv"
    df = pd.read_csv(path, index_col=0)
    if extra:
        return df
    return df[['name', 'sub_region', 'state_id', 'state_code']]


def city(country: str, city: str, state=None, extra=False, by='name') -> pd.Series:
    """
    Return the row corresponding to the given city in the cities(country)
    dataframe.

    Args:
        country:
            Country id or name.
        city:
            City name.
        state:
            Optional state code or id.
        extra:
            If given, return country-specific additional columns.
        by ({'name', 'id'}):
            If by='id', treats city as a city id, rather than name.
    """

    df = cities.unsafe(country, extra=extra)
    if by == 'id':
        return df.loc[city]

    if state:
        return df[(df['city'] == city) & (df['state_id'] == state)].iloc[0].copy()
    return df[df['city'] == city].iloc[0].copy()


def parse_city(country, city, extra=False):
    """
    Similar to city, but parses it from a string that might contain the state.
    """
    city, _, state = city.rpartition('-')
    if state not in state_codes(country):
        return city(country, f'{city}-{state}', extra=extra)
    return city(country, city, state or None, extra=extra)
