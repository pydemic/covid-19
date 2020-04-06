from pathlib import Path

import click
import pandas as pd
import requests

from .cia_factbook import coarse_age_distribution
from .data import DATA_PATH
from .ibge import city_id_from_name

IBGE_DATA: Path = DATA_PATH / "ibge_demographic"

URL = (
    "https://servicodados.ibge.gov.br/api/v1/pesquisas/23/periodos/all/resultados"
    "?localidade={city}&indicadores=27692,27693,27694,27695,27696,27697,27698,27699,"
    "27700,27701,27702,27703,27704,27705,27706,27707,27708,27709,27710,27711,27712,"
    "27713,27719,27720,27721,27722,27723,27724,27725,27726,27727,27728,27729,27730,"
    "27731,27732,27733,27734,27735,27736,27737,27738,27739,27740&lang=pt "
)

VARNAMES_MALE = {
    27692: "0",
    27693: "1-4",
    27694: "5-9",
    27695: "10-14",
    27696: "15-19",
    27697: "20-24",
    27698: "25-29",
    27699: "30-34",
    27700: "35-39",
    27701: "40-44",
    27702: "45-49",
    27703: "50-54",
    27704: "55-59",
    27705: "60-64",
    27706: "65-69",
    27707: "70-74",
    27708: "75-79",
    27709: "80-84",
    27710: "85-89",
    27711: "90-94",
    27712: "95-99",
    27713: "100+",
}

VARNAMES_FEMALE = {
    27719: "0",
    27720: "1-4",
    27721: "5-9",
    27722: "10-14",
    27723: "15-19",
    27724: "20-24",
    27725: "25-29",
    27726: "30-34",
    27727: "35-39",
    27728: "40-44",
    27729: "45-49",
    27730: "50-54",
    27731: "55-59",
    27732: "60-64",
    27733: "65-69",
    27734: "70-74",
    27735: "75-79",
    27736: "80-84",
    27737: "85-89",
    27738: "90-94",
    27739: "95-99",
    27740: "100+",
}
BLACK_LIST = {4220000}


def brazil_city_demography(city_id, coarse=False, collapse_newborn=False, download=True):
    """
    Load demographic datasets for given city and return a datasets-frame.

    Args:
        city_id:
            Numeric city id or name in IBGE database.
        coarse:
            If True, return datasets in a format compatible with morbidity datasets.
            Categories span 10 years instead of 5.
        collapse_newborn (bool):
            Default API separates newborns (age=0) from the group 1-4. If true,
            this collapses newborns in the age group 0-4.
        download:
            If True, download datasets from IBGE website.
    """
    if isinstance(city_id, str) and not city_id.isdigit():
        city_id = city_id_from_name(city_id)

    if coarse:
        df = brazil_city_demography(city_id, collapse_newborn=True, download=download)
        males, females = map(coarse_age_distribution, [df.males, df.females])
        return pd.DataFrame({"males": males, "females": females})

    if collapse_newborn:
        df = brazil_city_demography(city_id, download=download)
        row_0 = df.iloc[0]
        df = df.iloc[1:, :].copy()
        df.iloc[0, :] += row_0
        df.index = ["0-4", *df.index[1:]]
        return df

    return _load_city(city_id, download)


def _load_city(city_id, dowload):
    path = IBGE_DATA / f"city-{city_id}.csv"

    if path.exists():
        with path.open() as fd:
            return pd.read_csv(fd, index_col=0)

    elif dowload:
        r = requests.get(URL.format(city=city_id))
        obj = r.json()

        obj = {k["id"]: _int_or_nan(k["res"][0]["res"]["2010"]) for k in obj}
        try:
            males = [obj[k] for k in VARNAMES_MALE]
            females = [obj[k] for k in VARNAMES_FEMALE]
        except KeyError:
            print(obj, city_id, dowload)
            raise
        df = pd.DataFrame(list(zip(males, females)), columns=["males", "females"])
        df.index = list(VARNAMES_MALE.values())

        with path.open("w") as fd:
            df.to_csv(fd)
        return df
    else:
        raise ValueError(f"city not in the database: {city_id}")


def _int_or_nan(x):
    return float("nan") if x == "-" else int(x)


if __name__ == "__main__":

    @click.command()
    @click.argument("CITY_ID")
    @click.option("--coarse", is_flag=True, type=bool, help="Reduce the number of categories")
    @click.option("--no-gender", is_flag=True, type=bool, help="Do not discriminate by gender")
    def main(city_id, coarse, no_gender):
        df = brazil_city_demography(city_id, coarse=coarse)
        if no_gender:
            df = df.sum(1)
        print(df.to_csv())

    main()
