import numpy as np

from ..cache import cache
from covid.data import COUNTRIES
from ..models.seichar_demographic import SEICHARDemographic
from ..models.seichar import SEICHAR


@cache("cache/world.db")
def simulate(region, r0=2.74, ps=0.14, cls=SEICHAR):
    model = cls(region=region, R0=r0, prob_symptomatic=ps)
    model.run()
    return model


def r0_series(ps=0.14, func=lambda x: x):
    res = []
    for r0 in np.linspace(1, 5, 50):
        countries = []
        res.append(countries)
        for country in COUNTRIES:
            m = simulate(country, r0, ps)
            countries.append(func(m))
    return res


def ps_series(r0=2.74, func=lambda x: x):
    res = []
    for ps in np.linspace(0, 1, 50):
        countries = []
        res.append(countries)
        for country in COUNTRIES:
            m = simulate(country, r0, ps)
            countries.append(func(m))
    return res


if __name__ == "__main__":
    r0_series(func=print)
