from functools import lru_cache

import pandas as pd

from .data import DATA


@lru_cache(1)
def brazil_healthcare_capacity():
    """
    Return data from Brazilian hospitals capacity.
    """
    path = DATA / 'brazil_healthcare_capacity.csv'
    df = pd.read_csv(path, index_col=0)
    return df


def city_id_from_name(name):
    """
    Return IBGE´s city id from city name.
    """
    try:
        return _city_id_map()[name.lower()]
    except KeyError:
        raise ValueError(f'invalid city: {name!r}')


@lru_cache(1)
def _city_id_map():
    # We have this map here!
    df = brazil_healthcare_capacity()['region']
    return dict(zip(df.apply(str.lower), df.index))
