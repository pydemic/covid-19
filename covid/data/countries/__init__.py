from ..data import DATA_PATH
from ...utils import lru_safe_cache
import pandas as pd


@lru_safe_cache(64)
def states(country: str) -> pd.DataFrame:
    """
    Return a data frame with all states from a given country. State codes are
    in the index and names on the name column.
    """

    path = DATA_PATH / 'countries' / country / 'states.csv'
    return pd.read_csv(path, index_col=0)


@lru_safe_cache(64)
def sub_regions(country: str) -> pd.DataFrame:
    """
    Return a data frame with the next sub-division after state level for the
    given country.

    Data frame has ['name', 'state'] columns and the index can be either
    sequential or the special code assigned by the geography institute of the
    given country.
    """

    path = DATA_PATH / 'countries' / country / 'sub-regions.csv'
    return pd.read_csv(path, index_col=0)


@lru_safe_cache(64)
def cities(country: str) -> pd.DataFrame:
    """
    Return a data frame with all cities or municipalities in a country.

    Data frame has ['name', 'state', 'sub_region'] columns and the index can be
    either sequential or the special code assigned by the geography institute
    of the given country.
    """

    path = DATA_PATH / 'countries' / country / 'cities.csv'
    return pd.read_csv(path, index_col=0)
