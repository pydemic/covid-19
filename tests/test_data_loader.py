import pytest

from covid.data import (
    age_distribution,
    hospital_bed_density,
    covid_mortality,
    covid_mean_mortality,
    contact_matrix,
    city_id_from_name,
)


class TestCiaFactbook:
    def test_load_age_distribution(self):
        df = age_distribution("Brazil", 2020)
        assert 209_000 <= df.sum() <= 220_000

    def test_load_bad_age_distribution(self):
        with pytest.raises(ValueError):
            age_distribution("Brazil", 2050)

        with pytest.raises(ValueError):
            age_distribution("Bad spelling", 2050)

    def test_load_covid_mortality_syncs_with_age_distribution(self):
        dm = covid_mortality()
        df = age_distribution("Brazil", 2020, coarse=True)
        assert (dm.index == df.index).all()

    def test_mean_mortality(self):
        ph, pc, pf = covid_mean_mortality("Brazil", 2020)
        assert abs(ph - 0.054) < 1e-3
        assert abs(pc - 0.106) < 1e-3
        assert abs(pf - 0.465) < 1e-3

        ph, pc, pf = covid_mean_mortality("Italy", 2020)
        assert abs(ph - 0.094) < 1e-3
        assert abs(pc - 0.178) < 1e-3
        assert abs(pf - 0.472) < 1e-3

        ph, pc, pf = covid_mean_mortality("China", 2020)
        assert abs(ph - 0.065) < 1e-3
        assert abs(pc - 0.118) < 1e-3
        assert abs(pf - 0.469) < 1e-3

    def test_hospital_bed_density(self):
        assert hospital_bed_density("Brazil") == 0.0022
        assert hospital_bed_density().loc["Brazil", "density"] == 0.0022

    def test_contact_matrix(self):
        c_italy = contact_matrix("italy").values.mean()
        c_germany = contact_matrix("germany").values.mean()
        assert c_italy > 2 * c_germany

        c_italy = contact_matrix("italy", physical=True).values.mean()
        c_germany = contact_matrix("germany", physical=True).values.mean()
        assert c_italy > 1.5 * c_germany

    def test_coarse_contact_matrix(self):
        m1 = contact_matrix("italy")
        m2 = contact_matrix("italy", coarse=True)

        assert abs(m1.values[:-1, :-1].sum() - m2.values[:-2, :-2].sum()) < 1e-3
        assert list(m1.index) != list(m2.index)
        assert (m2.index == age_distribution("Italy", 2020, coarse=True).index).all()


class TestIBGE:
    def test_load_city_from_code(self):
        assert city_id_from_name("São Paulo") == 355_030
