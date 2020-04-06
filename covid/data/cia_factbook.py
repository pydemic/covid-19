import pandas as pd

from .data import DATA_PATH
from covid.data.countries.constants import COUNTRY_ALIASES

COUNTRY_TO_AGE_DISTRIBUTION = {
    "Bolivia": "Bolivia (Plurinational State of)",
    "Hong Kong": "China,Hong Kong SAR",
    "Macao": "China,Macao SAR",
    "Taiwan": "China,Taiwan Province of China",
    "North Korea": "Dem. People's Republic of Korea",
    "Iran": "Iran (Islamic Republic of)",
    "Laos": "Lao People's Democratic Republic",
    "Micronesia": "Micronesia (Fed. States of)",
    "South Korea": "Republic of Korea",
    "Moldova": "Republic of Moldova",
    "Russia": "Russian Federation",
    "Palestine": "State of Palestine",
    "Syria": "Syrian Arab Republic",
    "United States": "United States of America",
    "Venezuela": "Venezuela (Bolivarian Republic of)",
    "Tanzania": "United Republic of Tanzania",
    "Vietnam": "Viet Nam",
}
COUNTRY_TO_AGE_DISTRIBUTION.update({k.lower(): v for k, v in COUNTRY_TO_AGE_DISTRIBUTION.items()})
COUNTRY_TO_HOSPITAL_BEDS = {
    # '': 'Andorra',
    # '': 'Brunei',
    # '': 'Burma',
    # '': 'Dominica',
    # '': 'Faroe Islands',
    # '': 'Gaza Strip',
    # '': 'Greenland',
    # '': 'Monaco',
    # '': 'Marshall Islands',
    # '': 'Nauru',
    # '': 'Palau',
    # '': 'Saint Kitts and Nevis',
    # '': 'San Marino',
    "Bahamas": "Bahamas, The",
    "Gambia": "Gambia, The",
    "North Korea": "Korea, North",
    "South Korea": "Korea, South",
    "North Macedonia": "Macedonia",
    "Micronesia": "Micronesia, Federated States of",
    "": "West Bank",
}
COUNTRY_TO_HOSPITAL_BEDS.update({k.lower(): v for k, v in COUNTRY_TO_HOSPITAL_BEDS.items()})
HOSPITAL_BEDS_MISSING_DATA = {
    "Angola",
    "Aruba",
    "Bahamas",
    "Brunei Darussalam",
    "Chad",
    "Channel Islands",
    "Congo",
    "Curaçao",
    "Côte d'Ivoire",
    "Democratic Republic of the Congo",
    "French Guiana",
    "French Polynesia",
    "Guadeloupe",
    "Guam",
    "Lesotho",
    "Macao",
    "Martinique",
    "Mauritania",
    "Mayotte",
    "Melanesia",
    "Myanmar",
    "New Caledonia",
    "Niger",
    "Nigeria",
    "Palestine",
    "Papua New Guinea",
    "Puerto Rico",
    "Rwanda",
    "Réunion",
    "Samoa",
    "Sierra Leone",
    "South Africa",
    "South Sudan",
    "Taiwan",
    "United States Virgin Islands",
    "Western Sahara",
}
HOSPITAL_BEDS_MISSING_DATA.update(list(map(str.lower, HOSPITAL_BEDS_MISSING_DATA)))


def cia_factbook(which):
    """
    Import dataset from CIA factbook spreadsheets.

    Valid datasets:
    * 'age distributions'
    * 'hospital beds'
    """
    if which == "age distribution":
        df = pd.read_csv(DATA_PATH / "cia_factbook-age_distribution.csv", index_col=0)
        return df
    if which == "hospital beds":
        df = pd.read_csv(DATA_PATH / "cia_factbook-hospital_bed_density.csv", index_col=0, sep=";")
        return df
    else:
        raise ValueError(f"invalid dataset: {which}")


def age_distribution(region: str, year: int, coarse: bool = False) -> pd.Series:
    """
    Load a series object with age distribution for given country in the given
    year.

    Uses datasets from CIA factbook.

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
            If True, reduce the number of bins to be compatible with datasets from
            :func:`covid_mortality` function.
    """
    region = COUNTRY_ALIASES.get(region, region)
    region = COUNTRY_TO_AGE_DISTRIBUTION.get(region, region)

    df = cia_factbook("age distribution")
    data = df[(df.region == region) & (df.ref_date == year)]
    if data.shape[0] == 0:
        raise ValueError(f"Invalid country/year: {region!r} / {year!r}")
    data = data.loc[:, "0-4":].T
    data.index.name = "age"
    data = data.iloc[:, 0].apply(int)

    return coarse_age_distribution(data) if coarse else data


def coarse_age_distribution(df: pd.Series) -> pd.Series:
    """
    Convert the CIA fact book age distribution dataframe to a coarser form
    that is compatible with the output of :func:`covid_mortality`.

    Args:
        df: Input age distribution datasets set.
    """
    xs = list(df.index)
    ranges = list(zip(xs[::2], xs[1::2]))
    last = ranges.pop()
    ranges[-1] = (*ranges[-1], *last, xs[-1])

    data = {}
    for cat in map(list, ranges):
        total = df.T[cat].sum()
        start = cat[0].split("-")[0]
        end = cat[-1].split("-")[-1]
        data[f"{start}-{end}"] = total

    data["80+"] = data.pop("80-100+")
    data = pd.Series(data)
    data.index.name = "age"

    return data


def hospital_bed_density(country=None):
    """
    Return a datasets frame with hospital bed density per country or a single number
    with hospital bed density for a given country.

    Uses datasets from CIA factbook.

    >>> hospital_bed_density('Brazil')
    2.3
    >>> hospital_bed_density()
    ...
    """
    country = COUNTRY_ALIASES.get(country, country)
    country = COUNTRY_TO_HOSPITAL_BEDS.get(country, country)

    path = DATA_PATH / "cia_factbook-hospital_bed_density.csv"
    df = pd.read_csv(path, index_col=0, sep=";")
    df["density"] /= 1000
    if country:
        try:
            return df.loc[country, "density"]
        except KeyError:
            if country in HOSPITAL_BEDS_MISSING_DATA:
                return df.density.mean()
            raise ValueError(country)
    return df
