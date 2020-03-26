from . import data


class Region:
    """
    Generic demographic and epidemiologic information about region.
    """

    contact_matrix = None

    def __init__(self, name, year=2020):
        self.name = name
        self.short_name = name.partition('/')[-1]
        self.country = name.partition('/')[0]
        self.is_country = '/' not in name

        if self.is_country:
            self._init_from_factbook(self.country, year)
        elif self.country == 'Brazil':
            self._init_brazil(self.short_name)
        else:
            raise ValueError('demographic data is only available to Brazil')

        # Derived quantities
        self.population_size = self.age_coarse.sum()

        # Mortality statistics
        self.prob_hospitalization, \
        self.prob_icu, \
        self.prob_fatality = data.covid_mean_mortality(self.age_coarse)

    def _init_from_factbook(self, country, year):
        cid = country.lower().replace(' ', '_')

        # Age distribution and population
        self.age_distribution = data.age_distribution(country, year) * 1000
        self.age_coarse = data.age_distribution(country, year, coarse=True) * 1000

        # Healthcare statistics
        self.icu_beds_pm = 1
        self.icu_occupancy_rate = 0.8
        self.hospital_beds_pm = data.hospital_bed_density(country)
        self.hospital_occupancy_rate = 0.8

        # Contact matrix
        ref_country = country if cid in data.CONTACT_MATRIX_IDS else 'mean'
        self.contact_matrix = data.contact_matrix(ref_country, coarse=True)

    def _init_brazil(self, city):
        city_id = data.city_id_from_name(city)

        # Age distribution and population
        self.age_distribution = data.brazil_city_demography(city_id)
        df = data.brazil_city_demography(city_id, coarse=True)
        self.age_coarse = df.sum(1)
        N = self.age_coarse.sum()

        # Healthcare statistics
        df = data.brazil_healthcare_capacity()
        stats = df.loc[city_id, :]
        cases = stats.cases_influenza_regular + stats.cases_other_regular
        cases_icu = stats.cases_influenza_icu + stats.cases_other_icu
        self.icu_beds_pm = stats.icu / N * 1000
        self.icu_occupancy_rate = cases_icu / stats.icu
        self.hospital_beds_pm = stats.regular / N * 1000
        self.hospital_occupancy_rate = cases / stats.regular

        # Contact matrix
        self.contact_matrix = data.contact_matrix('Italy', coarse=True)

    def __str__(self):
        return self.short_name

    def __repr__(self):
        return f'{self.__class__.__name__}({self.name!r})'

    def _repr_html_(self):
        return self.short_name

    def report(self):
        return f"""Region {self.name} 
"""


def as_region(name):
    """
    Normalize string or Region instance as a Region instance.
    """
    if isinstance(name, Region):
        return name
    return Region(name)
