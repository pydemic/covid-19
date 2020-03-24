from pathlib import Path

import pandas as pd

DATA = Path(__file__).parent.parent / 'datasets'


def contact_matrix(country='mean', physical=False):
    """
    Load contact matrix for country.
    """
    which = 'physical' if physical else 'all'
    path = DATA / 'contact_matrix' / f'{country.lower()}-{which}.csv'
    df = pd.read_csv(path, index_col=0)
    return df
