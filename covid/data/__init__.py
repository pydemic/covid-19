"""
Import data sets from various sources.
"""
from .cia_factbook import cia_factbook, age_distribution, hospital_bed_density
from .data import (contact_matrix)
from .ibge import brazil_healthcare_capacity, city_id_from_name
from .mortality import covid_mortality, covid_mean_mortality
