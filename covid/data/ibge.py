from functools import lru_cache

import pandas as pd

from .data import DATA_PATH


def brazil_healthcare_capacity():
    """
    Return datasets from Brazilian hospitals capacity.
    """
    path = DATA_PATH / "brazil_healthcare_capacity.csv"
    df = pd.read_csv(path, index_col=0)
    return df


def city_id_from_name(name):
    """
    Return IBGE´s city id from city name.
    """
    if name.isdigit():
        return int(name)
    try:
        return _city_id_map()[name.lower()]
    except KeyError:
        raise ValueError(f"invalid city: {name!r}")


@lru_cache(1)
def _city_id_map():
    path = DATA_PATH / "ibge_demographic" / "city_codes.csv"
    with path.open() as fd:
        df = pd.read_csv(path)

    # We have this map here!
    df = df[["name", "city_full_id"]]
    return {x.lower(): int(str(y)[:-1]) for x, y in df.values}
