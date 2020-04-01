from covid import region


class TestRegion:
    def test_country(self):
        br = region("Brazil")
        assert br.population_size == 212_559_000

    def test_city(self):
        sp = region("Brazil/São Paulo")
        assert sp.population_size == 11_253_503

    def test_metro_area(self):
        sp = region("Brazil/Metropolitana de São Paulo")
        assert sp.population_size == 21_154_988
