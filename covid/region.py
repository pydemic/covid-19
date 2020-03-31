import json
import operator
from enum import Enum
from typing import Optional, Iterable

import pandas as pd

from . import data
from .data import DATA_PATH
from .types import delegate, computed


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

    id = None
    data_source = None
    contact_matrix = None
    full_name = delegate('name')

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
        return pd.DataFrame({'male': males, 'female': females}, index=idx)

    # Kinds
    KIND_UNKNOWN = RegionType.UNKNOWN
    KIND_COUNTRY = RegionType.COUNTRY
    KIND_CITY = RegionType.CITY
    KIND_METRO = RegionType.METRO

    @property
    def _mortality(self):
        self.prob_hospitalization, self.prob_icu, self.prob_fatality = \
            res = data.covid_mean_mortality(self.demography)
        return res

    def __init__(self, name, demography, full_name=None, kind=RegionType.UNKNOWN):
        self.name = name
        self.country = name.partition('/')[0]
        self.kind = kind
        if full_name:
            self.full_name = full_name
        self.demography = demography

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'region({self.full_name!r})'

    def _repr_html_(self):
        return self.name

    def report(self):
        return f"""Region {self.name}
"""


class BrazilMunicipality(Region):
    """
    Region represents a Brazilian municipality.
    """

    data_source = 'IBGE'
    contact_matrix = computed(lambda r: data.contact_matrix('Italy', infer=r.demography))

    def __init__(self, city):
        self.id = city_id = data.city_id_from_name(city)
        demography = data.brazil_city_demography(city_id, coarse=True).sum(1)
        super().__init__(city, demography, full_name=f'Brazil/{city}',
                         kind=self.KIND_CITY)

        # Other properties
        self.demography_detailed = data.brazil_city_demography(city_id)

        # Healthcare statistics
        N = demography.sum()
        try:
            df = data.brazil_healthcare_capacity()
            stats = df.loc[city_id, :]
        except KeyError:
            self.hospital_beds_pm = 0.0
            self.icu_beds_pm = 0.0
        else:
            cases = stats.cases_influenza_regular + stats.cases_other_regular
            cases_icu = stats.cases_influenza_icu + stats.cases_other_icu
            e = 1e-50
            self.icu_beds_pm = stats.icu / N * 1000
            self.icu_occupancy_rate = cases_icu / (stats.icu + e)
            self.hospital_beds_pm = stats.regular / N * 1000
            self.hospital_occupancy_rate = cases / (stats.regular + e)


class CIAFactbookCountry(Region):
    data_source = 'CIA Factbook'

    def __init__(self, country, year=2020):
        self.id = country_id = country.lower().replace(' ', '_')
        demography = data.age_distribution(country, year, coarse=True)
        demography *= 1000
        super().__init__(country, demography, kind=self.KIND_COUNTRY)

        # Age distribution and population
        df = data.age_distribution(country, year)
        df *= 500
        df = pd.DataFrame({'male': df, 'female': df}, index=df.index)
        self.demography_detailed = df

        # Healthcare statistics
        self.hospital_beds_pm = data.hospital_bed_density(country) * 1000

        # Contact matrix
        # TODO: using Italy reference contact matrices for all countries
        # not present in the POLYMOD dataset
        ref_country = country if country_id in data.CONTACT_MATRIX_IDS else 'Italy'
        self.contact_matrix = data.contact_matrix(ref_country, infer=self.demography)


def sub_region_acc(attr, aggr=sum):
    getter = operator.attrgetter(attr)
    return computed(lambda r: aggr(map(getter, r.sub_regions)))


class MultiRegion(Region):
    """
    Region that is an aggregate of several other regions.
    """

    demography_detailed = sub_region_acc('demography_detailed')
    icu_total_capacity = sub_region_acc('icu_total_capacity')
    icu_surge_capacity = sub_region_acc('icu_surge_capacity')
    hospital_total_capacity = sub_region_acc('hospital_total_capacity')
    hospital_surge_capacity = sub_region_acc('hospital_surge_capacity')

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
        return (total - surge) / total

    @computed
    def icu_occupancy_rate(self):
        surge = self.icu_surge_capacity
        total = self.icu_total_capacity
        return (total - surge) / total

    def __init__(self, name: Optional[str], regions: Iterable[Region], **kwargs):
        self.sub_regions = [region(r) for r in regions]

        if name is None:
            names = (r.name for r in self.sub_regions)
            name = f'Region: {names}'

        demography = sum(r.demography for r in self.sub_regions)
        super().__init__('multi', demography, kind=self.KIND_METRO, **kwargs)
        self.name = name

        # Correct this once we have better methods for handling contact
        # matrices
        self.contact_matrix = data.contact_matrix('Italy', infer=demography)


def region(name, **kwargs):
    """
    Normalize string or Region and return a Region.
    """
    if isinstance(name, Region):
        return name
    elif not isinstance(name, str):
        return MultiRegion(None, list(name), **kwargs)
    elif name.startswith('Brazil/') and name.endswith('(metro)'):
        metro = name[7:-7].strip()
        cities = brazilian_metro_area(metro)
        kwargs.setdefault('full_name', name)
        return MultiRegion(metro + ' (metro)', cities, **kwargs)
    elif name.startswith('Brazil/'):
        return BrazilMunicipality(name[7:], **kwargs)
    else:
        return CIAFactbookCountry(name, **kwargs)


def brazilian_metro_area(name):
    """
    Load all cities from a Brazilian metropolitan area.
    """

    path = DATA_PATH / 'brazil_metro.json'
    with path.open() as fd:
        data = json.load(fd)
    return [region(f'Brazil/{id}') for id in data[name]]
