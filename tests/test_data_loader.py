import pytest

from covid.data import *


class TestCiaFactbook:
    def test_load_age_distribution(self):
        df = age_distribution('Brazil', 2020)
        assert 209_000 <= df.sum() <= 220_000

    def test_load_bad_age_distribution(self):
        with pytest.raises(ValueError):
            age_distribution('Brazil', 2050)

        with pytest.raises(ValueError):
            age_distribution('Bad spelling', 2050)

    def test_load_covid_mortality_syncs_with_age_distribution(self):
        dm = covid_mortality()
        df = age_distribution('Brazil', 2020, coarse=True)
        assert (dm.index == df.index).all()

    def test_mean_mortality(self):
        ph, pc, pf = covid_mean_mortality('Brazil', 2020)
        assert abs(ph - 0.054) < 1e-3
        assert abs(pc - 0.106) < 1e-3
        assert abs(pf - 0.465) < 1e-3

        ph, pc, pf = covid_mean_mortality('Italy', 2020)
        assert abs(ph - 0.094) < 1e-3
        assert abs(pc - 0.178) < 1e-3
        assert abs(pf - 0.472) < 1e-3

        ph, pc, pf = covid_mean_mortality('China', 2020)
        assert abs(ph - 0.065) < 1e-3
        assert abs(pc - 0.118) < 1e-3
        assert abs(pf - 0.469) < 1e-3

    def test_hospital_bed_density(self):
        assert hospital_bed_density('Brazil') == 0.0022
        assert hospital_bed_density().loc['Brazil', 'density'] == 0.0022
