import requests

CASES_URL = "https://brasil.io/api/dataset/covid19/caso/data"


def city_cases(city_id, date=None, most_recent=None):
    params = {"place_type": "city"}
    if isinstance(city_id, str):
        if city_id.isdigit():
            params["city_ibge_code"] = city_id
        else:
            params["city"] = city_id

    if date is not None:
        params["date"] = date

    if most_recent is not None:
        params["is_last"] = most_recent is True

    return cases(**params)


def state_cases(state_code, date=None, most_recent=None):
    params = {"place_type": "state", "state": state_code}

    if date is not None:
        params["date"] = date

    if most_recent is not None:
        params["is_last"] = most_recent is True

    return cases(**params)


def cases(**kwargs):
    return requests.get(CASES_URL, params={"page_size": 1000000, **kwargs}).json()["results"]


if __name__ == "__main__":
    import click
    import pandas as pd

    @click.command()
    @click.option("-ct", "--case-type")
    @click.option("-i", "--id")
    @click.option("-d", "--date")
    @click.option("-mr", "--most-recent", type=bool)
    def main(case_type=None, id=None, **kwargs):
        results = []
        if case_type == "city":
            results = city_cases(**{"city_id": id, **kwargs})
        elif case_type == "state":
            results = state_cases(**{"state_code": id, **kwargs})
        else:
            results = cases(**kwargs)
        print(pd.DataFrame(results).to_csv())

    main()
