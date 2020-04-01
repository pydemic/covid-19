import click

import covid.data.countries.geography
from covid.data import countries


@click.command()
@click.argument("name")
@click.option("--states", "-s", is_flag=True, help="Show table with country states")
@click.option("--extra", "-e", is_flag=True, help="Show extra columns, when available")
def cli(name, states, extra):
    data = None
    if states:
        data = covid.data.countries.geography.states(name, extra=extra)

    if data is not None:
        print(data)


if __name__ == "__main__":
    cli()
