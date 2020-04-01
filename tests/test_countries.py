import numpy as np
import pandas as pd
import pytest

from covid.data import countries


def eq(x, y, tol=None) -> bool:
    if tol is None:
        test = np.all(x == y)
        return test
    else:
        raise NotImplementedError


class TestCountriesGeography:
    @pytest.fixture()
    def state(self):
        data = {"name": "Distrito Federal", "code": "DF", "id": 53}
        return pd.Series(data, name=53)

    @pytest.fixture()
    def sub_region(self):
        data = ["Distrito Federal", 53, "DF", 531]
        index = ["name", "state_id", "state_code", "id"]
        return pd.Series(data, name=531, index=index)

    @pytest.fixture()
    def city(self):
        data = ["Brasília", 531, 53, "DF", 5300108]
        index = ["name", "sub_region", "state_id", "state_code", "id"]
        return pd.Series(data, index=index, name=5300108)

    def test_states_table(self, state):
        df = countries.states("brazil")
        assert eq(df, countries.states("Brasil"))
        assert {"DF", "RJ"}.issubset(df["code"])
        assert {"Distrito Federal", "Rio de Janeiro"}.issubset(df["name"])
        assert {53, 33}.issubset(df.index)
        assert len(df) == 27
        assert eq(df.columns, ["name", "code"])
        assert eq(df.loc[53], state[["name", "code"]])
        assert eq(df.loc[53].name, 53)

    def test_state_codes(self):
        assert countries.state_codes("Brazil") == set(
            "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE "
            "SP TO".split()
        )

    def test_sub_regions(self, sub_region):
        df = countries.sub_regions("brazil", 53)
        assert eq(df, sub_region[["name", "state_id", "state_code"]])

    def test_parse_entity_state(self, state, sub_region, city):
        kind, st = countries.parse_entity("brazil", state.name)
        assert kind == "state"
        assert eq(st, state)

        kind, st = countries.parse_entity("brazil", str(state.name))
        assert kind == "state"
        assert eq(st, state)

        kind, st = countries.parse_entity("brazil", state["code"])
        assert kind == "state"
        assert eq(st, state)

    def test_parse_entity_sub_region(self, state, sub_region, city):
        kind, st = countries.parse_entity("brazil", sub_region.name)
        assert kind == "sub-region"
        assert eq(st, sub_region)

        kind, st = countries.parse_entity("brazil", str(sub_region.name))
        assert kind == "sub-region"
        assert eq(st, sub_region)

        kind, st = countries.parse_entity("brazil", str(sub_region["name"]))
        assert kind == "sub-region"
        assert eq(st, sub_region)

    def test_parse_entity_sub_city(self, state, sub_region, city):
        kind, st = countries.parse_entity("brazil", city.name)
        assert kind == "city"
        assert eq(st, city)

        kind, st = countries.parse_entity("brazil", str(city.name))
        assert kind == "city"
        assert eq(st, city)

        kind, st = countries.parse_entity("brazil", city["name"])
        assert kind == "city"
        assert eq(st, city)

    def test_city(self, city):
        assert eq(countries.city("brazil", city["id"], by="id"), city)
        assert eq(countries.city("brazil", city["name"]), city)

    def test_sub_region(self, sub_region):
        assert eq(countries.sub_region("brazil", sub_region.name, by="id"), sub_region)
        assert eq(countries.sub_region("brazil", sub_region["name"]), sub_region)
