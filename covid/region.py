import operator
import warnings
from enum import Enum
from typing import Optional, Iterable

import pandas as pd

from . import data
from .data import countries
from .types import delegate, computed
from .utils import fmt, pc, indent

ifmt = lambda x: fmt(int(x))
e = 1e-50


class RegionType(Enum):
    UNKNOWN = 0
    COUNTRY = 1
    CITY = 2
    METRO = 4


class Region:
    """
    Base class that implements several region types.

    Generic demographic and epidemiologic information about region.
    """

    _contact_matrix_ref = None
    id = None
    data_source = None
    contact_matrix = None
    demography: pd.Series
    full_name = delegate("name")

    # Derived quantities
    population_size = computed(lambda r: r.demography.sum())
    prob_hospitalization = computed(lambda r: r._mortality[0])
    prob_icu = computed(lambda r: r._mortality[1])
    prob_fatality = computed(lambda r: r._mortality[2])

    # Hospitalization
    # TODO: override with environment variables?
    # TODO: move to a specialized Healthcare class?
    hospital_occupancy_rate = 0.75
    icu_occupancy_rate = 0.75
    hospital_beds_pm = 3.22  # Global mean
    icu_beds_pm = computed(lambda r: r.hospital_beds_pm / 10.0)  # Wild guess ;)

    @computed
    def hospital_total_capacity(self):
        return self.hospital_beds_pm / 1000 * self.population_size

    @computed
    def hospital_surge_capacity(self):
        return self.hospital_total_capacity * (1 - self.hospital_occupancy_rate)

    @computed
    def icu_total_capacity(self):
        return self.icu_beds_pm / 1000 * self.population_size

    @computed
    def icu_surge_capacity(self):
        return self.icu_total_capacity * (1 - self.icu_occupancy_rate)

    # Queries
    is_country = property(lambda self: self.kind == self.KIND_COUNTRY)
    is_city = property(lambda self: self.kind == self.KIND_CITY)
    is_metro = property(lambda self: self.kind == self.KIND_METRO)

    # Optional info
    @computed
    def detailed_demography(self):
        data = self.demography.values
        idx = self.demography.index
        males = data // 2
        females = data - males
        return pd.DataFrame({"male": males, "female": females}, index=idx)

    # Kinds
    KIND_UNKNOWN = RegionType.UNKNOWN
    KIND_COUNTRY = RegionType.COUNTRY
    KIND_CITY = RegionType.CITY
    KIND_METRO = RegionType.METRO

    @property
    def _mortality(self):
        (
            self.prob_hospitalization,
            self.prob_icu,
            self.prob_fatality,
        ) = res = data.covid_mean_mortality(self.demography)
        return res

    @computed
    def contact_matrix(self):
        if self._contact_matrix_ref is None:
            return None
        return data.contact_matrix("Italy", infer=self.demography)

    def __init__(self, name, demography, full_name=None, kind=RegionType.UNKNOWN, id=None):
        self.name = name
        self.country = name.partition("/")[0]
        self.kind = kind
        self.id = id
        if full_name:
            self.full_name = full_name
        self.demography = demography
        assert isinstance(demography, pd.Series), demography

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"region({self.full_name!r})"

    def _repr_html_(self):
        return self.name

    def summary(self):
        h_max = self.hospital_total_capacity
        c_max = self.icu_total_capacity
        return f"""REGION {self.name}:

Generic
- Name       : {self.full_name}
- Kind       : {self.kind}
- Population : {fmt(self.population_size)}
- Id         : {self.id}
- Source     : {self.data_source}

Regular hospital beds
- Capacity    : {ifmt(h_max)} ({fmt(self.hospital_beds_pm)} / 1,000 ha)
- Occupation  : {pc(self.hospital_occupancy_rate)}
- Free beds   : {ifmt(self.hospital_surge_capacity)}

ICU beds
- Capacity    : {ifmt(c_max)} ({fmt(10 * self.icu_beds_pm)} / 10,000 ha)
- Occupation  : {pc(self.icu_occupancy_rate)}
- Free beds   : {ifmt(self.icu_surge_capacity)}
"""

    def report(self):
        """
        Extended version of summary
        """
        parts = [
            self.summary(),
            "Demography",
            indent(str(100 * self.demography / self.population_size)),
        ]
        return "\n".join(parts)


class City(Region):
    """
    Region represents a Brazilian municipality.
    """

    data_source = "IBGE"
    _contact_matrix_ref = "Italy"

    def __init__(self, country, id):
        self.data = df = countries.city(country, id, by="id")
        demography = data.brazil_city_demography(id, coarse=True, download=False).sum(1)
        super().__init__(df["name"], demography, id=id, kind=self.KIND_CITY)

        # Other properties
        self.demography_detailed = data.brazil_city_demography(id)

        # Healthcare statistics
        N = demography.sum()
        try:
            df = data.brazil_healthcare_capacity()
            stats = df[df.index == id // 10].iloc[0]
        except IndexError:
            self.hospital_beds_pm = 0.0
            self.icu_beds_pm = 0.0
        else:
            cases = stats.cases_influenza_regular + stats.cases_other_regular
            cases_icu = stats.cases_influenza_icu + stats.cases_other_icu
            e = 1e-50
            self.icu_beds_pm = stats.icu / N * 1000
            self.icu_occupancy_rate = min(cases_icu / (stats.icu + e), 1.0)
            self.hospital_beds_pm = stats.regular / N * 1000
            self.hospital_occupancy_rate = min(cases / (stats.regular + e), 1.0)


class CIAFactbookCountry(Region):
    data_source = "CIA Factbook"

    # TODO: using Italy reference contact matrices for all countries
    _contact_matrix_ref = computed(
        lambda r: r.country if r.id in data.CONTACT_MATRIX_IDS else "Italy"
    )

    def __init__(self, country, year=2020):
        self.id = country.lower().replace(" ", "_")
        demography = data.age_distribution(country, year, coarse=True)
        demography *= 1000
        super().__init__(country, demography, kind=self.KIND_COUNTRY)

        # Age distribution and population
        df = data.age_distribution(country, year)
        df *= 500
        df = pd.DataFrame({"male": df, "female": df}, index=df.index)
        self.demography_detailed = df

        # Healthcare statistics
        self.hospital_beds_pm = data.hospital_bed_density(country) * 1000


def sub_region_acc(attr, aggr=sum):
    getter = operator.attrgetter(attr)

    @computed
    def fn(self):
        lst = []
        for r in self.sub_regions:
            lst.append(getter(r))
        return aggr(lst)

    return fn


class MultiRegion(Region):
    """
    Region that is an aggregate of several other regions.
    """

    _contact_matrix_ref = "Italy"
    demography_detailed = sub_region_acc("demography_detailed")
    icu_total_capacity = sub_region_acc("icu_total_capacity")
    icu_surge_capacity = sub_region_acc("icu_surge_capacity")
    hospital_total_capacity = sub_region_acc("hospital_total_capacity")
    hospital_surge_capacity = sub_region_acc("hospital_surge_capacity")

    @computed
    def hospital_beds_pm(self):
        return 1000 * self.hospital_total_capacity / self.population_size

    @computed
    def icu_beds_pm(self):
        return 1000 * self.icu_total_capacity / self.population_size

    @computed
    def hospital_occupancy_rate(self):
        surge = self.hospital_surge_capacity
        total = self.hospital_total_capacity
        return min((total - surge) / (total + e), 1.0)

    @computed
    def icu_occupancy_rate(self):
        surge = self.icu_surge_capacity
        total = self.icu_total_capacity
        return min((total - surge) / (total + e), 1.0)

    def __init__(self, name: Optional[str], regions: Iterable[Region], **kwargs):
        if not regions:
            raise ValueError(f"cannot create empty multi-region {name}")

        self.sub_regions = [region(r) for r in regions]

        if name is None:
            names = (r.name for r in self.sub_regions)
            name = f"Region: {names}"

        demography = sum(r.demography for r in self.sub_regions)
        super().__init__("multi", demography, kind=self.KIND_METRO, **kwargs)
        self.name = name


def region(name, **kwargs):
    """
    Normalize string or Region and return a Region.
    """
    if isinstance(name, Region):
        return name
    elif not isinstance(name, str):
        return MultiRegion(None, list(name), **kwargs)

    # TODO: generalize this
    elif "/" in name:
        country, _, entity = map(str.strip, name.partition("/"))
        country = countries.normalize_country_id(country)
        kind, info = countries.parse_entity(country, entity)

        if kind == "state":
            df = countries.cities(country, state_id=info["id"])
            state = _region_from_cities(country, info, df, kwargs)
            state.state_code = info["code"]
            state.data_source = "IBGE"
            return state

        elif kind == "city":
            return City(country, info["id"])

        elif kind == "sub-region":
            df = countries.cities(country)
            df = df[df["sub_region"] == info["id"]]
            sub_region = _region_from_cities(country, info, df, kwargs)
            sub_region.state_code = info["state_code"]
            sub_region.state_id = info["state_id"]
            sub_region.data_source = "IBGE"
            return sub_region

    else:
        return CIAFactbookCountry(name, **kwargs)


def _region_from_cities(country, info, df, kwargs):
    cities = []
    for id_, row in df.iterrows():
        try:
            id_: int
            city = City(country, id_)
        except ValueError:
            name = row["name"]
            warnings.warn(f"City has no demography: {name} ({id_})")
        else:
            cities.append(city)
    res = MultiRegion(info["name"], cities, id=info["id"])
    return res


if __name__ == "__main__":
    import click

    @click.command(name="covid.region")
    @click.argument("name")
    def cli(name):
        click.echo(region(name).report())

    cli()
