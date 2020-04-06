import re
from functools import lru_cache, wraps
from typing import Tuple

import pandas as pd

from .constants import normalize_country_id as _as_country
from ..data import DATA_PATH
from ...utils import lru_safe_cache

PARSE_STATE_RE = re.compile(r"^[A-Z]{2,3}$")
PARSE_CITY_STATE_RE = re.compile(r"^.* ?- ?[A-Z]{2,3}$")


def with_id_entry(obj):
    if callable(obj):

        @wraps(obj)
        def decorated(*args, **kwargs):
            res = obj(*args, **kwargs)
            return res.append(pd.Series({"id": res.name}))

        return decorated
    else:
        return obj.append(pd.Series({"id": obj.name}))


@with_id_entry
def get_entity(df, key, state_code, state_id, by, msg):
    try:
        if by == "id":
            return df.loc[key]
        for col, val in (("state_code", state_code), ("state_id", state_id)):
            if val is not None:
                df = df[df[col] == val]
        return df[df["name"] == key].iloc[0]
    except IndexError:
        raise ValueError(msg.format(key=key))


@lru_safe_cache(64)
def states(country: str, extra=False) -> pd.DataFrame:
    """
    Return a datasets frame with all states from a given country. Official state
    codes assigned by the official geographic institute of a country are
    in the index. If there is no such convention, it index states sequentially
    by alphabetic order.

    It return [name, code] columns, in which code is the usual small 2-3 letter
    abbreviations. If extra=True, it may append additional country-specific
    columns.
    """

    country = _as_country(country)
    if not extra:
        return states(country, True)[["name", "code"]]

    path = DATA_PATH / "countries" / country / "states.csv"
    return pd.read_csv(path, index_col=0)


@lru_cache(128)
def state_codes(country):
    """
    Return a tuple with all state codes for country.
    """
    country = _as_country(country)
    df = states.unsafe(country)
    return frozenset(sorted(df["code"]))


@with_id_entry
def state(country, key, extra=False):
    """
    Return state from key.
    """
    df = states.unsafe(country, extra=extra)
    try:
        return df.loc[key]
    except KeyError:
        pass

    for col in ["name", "code"]:
        df_ = df[df[col] == key]
        if len(df_) != 0:
            return df_.iloc[0]
    raise ValueError(f"invalid state for {country}: {state}")


@lru_safe_cache(64)
def sub_regions(country: str, state_id=None, state_code=None, extra=False) -> pd.DataFrame:
    """
    Return a datasets frame with the next sub-division after state level for the
    given country.

    Data frame has ['name', 'state_id', 'state_code'] columns and the index can
    be either sequential or correspond to the special code assigned by the
    official geographic institute of the given country.
    """

    country = _as_country(country)
    if state_id:
        df = sub_regions.unsafe(country, extra=extra)
        return df[(df["state_id"] == state_id)]
    elif state_code:
        df = sub_regions.unsafe(country, extra=extra)
        return df[(df["state_code"] == state_code)]
    path = DATA_PATH / "countries" / country / "sub-regions.csv"
    df = pd.read_csv(path, index_col=0)
    return df if not extra else df[["name", "state_id", "state_code"]]


def sub_region(
    country: str, key, state_code=None, state_id=None, extra=False, by="name"
) -> pd.Series:
    """
    Return the row corresponding to the given sub_region in the
    sub_regions(country) datasets frame.

    Args:
        country:
            Country id or name.
        key:
            Sub-region name (default) or id.
        state_code:
            Optional state code.
        state_id:
            Optional state id.
        extra:
            If given, return country-specific additional columns.
        by ({'name', 'id'}):
            If by='id', treats input as a sub-region id, rather than name.
    """

    country = _as_country(country)
    df = sub_regions.unsafe(country, extra=extra)
    return get_entity(df, key, state_code, state_id, by, "invalid sub-region: {key!r}")


@lru_safe_cache(64)
def cities(
    country: str, extra=False, sub_region=None, state_id=None, state_code=None
) -> pd.DataFrame:
    """
    Return a datasets frame with all cities or municipalities in a country.

    Data frame has ['name', 'sub_region', 'state_id', 'state_code'] columns
    and the index can be either sequential or the special code assigned by the
    geography institute of the given country.

    Optionally filter by state_id or sub_region id.
    """

    country = _as_country(country)
    path = DATA_PATH / "countries" / country / "cities.csv"
    df = pd.read_csv(path, index_col=0)
    if sub_region:
        df = df[df["sub_region"] == sub_region]
    if state_id:
        df = df[df["state_id"] == state_id]
    if state_code:
        df = df[df["state_code"] == state_code]
    if extra:
        return df
    return df[["name", "sub_region", "state_id", "state_code"]]


@lru_safe_cache(1025)
def city(
    country: str, key: str, state_code=None, state_id=None, extra=False, by="name"
) -> pd.Series:
    """
    Return the row corresponding to the given city in the cities(country)
    dataframe.

    Args:
        country:
            Country id or name.
        key:
            City name (default) or id.
        state_code:
            Optional state code.
        state_id:
            Optional state id.
        extra:
            If given, return country-specific additional columns.
        by ({'name', 'id'}):
            If by='id', treats city as a city id, rather than name.
    """

    country = _as_country(country)
    df = cities.unsafe(country, extra=extra)
    return get_entity(df, key, state_code, state_id, by, "invalid city: {key!r}")


def parse_city(country, text, extra=False):
    """
    Similar to city, but parses it from a string that might contain the state.
    """
    name, _, st = text.rpartition("-")
    if st in state_codes(country):
        return _city(country, name, extra=extra, state_code=st)
    return _city(country, text, extra=extra)


def parse_entity(country, text, extra=False) -> Tuple[str, pd.Series]:
    """
    Similar to parse_city, but parses any geographical entity in a country.
    Returns a tuple of (kind, datasets), in which kind is either 'city', 'state'
    or 'sub-region'.
    """

    # It only works for Brazil
    if isinstance(text, int) or text.isdigit():
        code = int(text)
        if 0 <= code <= 99:
            df = states.unsafe(country, extra=extra)
            return "state", with_id_entry(df.loc[code])
        elif 100 <= code <= 9_999:
            df = sub_regions.unsafe(country, extra=extra)
            return "sub-region", with_id_entry(df.loc[code])
        elif 1000000 <= code <= 9_999_999:
            df = cities.unsafe(country, extra=extra)
            return "city", with_id_entry(df.loc[code])
        else:
            raise ValueError(f"invalid entity code: {text!r}")

    if PARSE_STATE_RE.match(text):
        df = states.unsafe(country, extra=extra)
        return "state", with_id_entry(df[df["code"] == text].iloc[0])

    if PARSE_CITY_STATE_RE.match(text):
        city_, _, code = map(str.strip, text.rpartition("-"))
        return "city", city(country, city_, state_code=code, extra=extra)

    try:
        return "city", city(country, text, extra=extra)
    except ValueError:
        pass
    try:
        return "sub-region", sub_region(country, text, extra=extra)
    except ValueError:
        pass
    try:
        return "state", state(country, text, extra=extra)
    except ValueError:
        raise ValueError(f"invalid geographic entity: {text!r}")


_city = city
