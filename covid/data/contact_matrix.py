import numpy as np
import pandas as pd

from .data import DATA_PATH, COARSE_INDEX


def symmetric_contact_matrix(country, coarse=False):
    """
    Return inferred symmetric matrix datasets from (Fumanelli, 2012)

    See Also:
        https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1002673#s4
    """
    path = DATA_PATH / "contact_matrix" / "fumanelli.xls"
    df = pd.read_excel(path, country, header=None)
    df.index = range(1, 101)
    df.columns = df.index
    return _symmetric_contact_matrix_coarse(df) if coarse else df


def _symmetric_contact_matrix_coarse(df):
    out = np.zeros((9, 9))

    # Add a zeroed row and column to represent the 0 age range
    data = np.zeros((101, 101))
    data[1:, 1:] = df.values

    # Fill 0-9, 10-19, ..., 70-79 ranges
    for i in range(0, 80, 10):
        for j in range(0, 80, 10):
            out[i // 10, j // 10] += data[i : i + 10, j : j + 10].sum()

    # Fill 80+ ranges
    for i in range(8):
        out[i, 8] += data[10 * i : 10 * (i + 1), 80:].sum()
        out[8, i] += data[80:, 10 * i : 10 * (i + 1)].sum()
    out[8, 8] += data[80:, 80:].sum()

    return pd.DataFrame(out, columns=COARSE_INDEX, index=COARSE_INDEX)


def contact_matrix(country="mean", physical=False, coarse=None, infer=False) -> pd.DataFrame:
    """
    Load contact matrix for country.

    If coarse is True, return a decennial distribution that is compatible with
    other datasets used in this package like mortality rates and coarse age
    distributions.
    """
    if infer is not False and physical:
        raise ValueError("cannot infer physical contact matrix")
    elif infer is False:
        return _contact_matrix(country, physical, coarse)
    elif coarse is False:
        raise ValueError("can only infer coarse matrices")
    elif infer is True:
        demography = age_distribution(country, 2020, coarse=True).values * 1.0
    else:
        demography = np.asarray(infer)

    contacts = symmetric_contact_matrix(country, coarse=True).values
    demography = demography / demography.sum()
    data = (contacts / demography).T
    eig = np.linalg.eigvals(data)
    lambd = eig.real.max()
    return pd.DataFrame(data / lambd, index=COARSE_INDEX, columns=COARSE_INDEX)


def _contact_matrix(country, physical, coarse):
    which = "physical" if physical else "all"
    path = DATA_PATH / "contact_matrix" / f"{country.lower()}-{which}.csv"
    df = pd.read_csv(path, index_col=0)
    return _contact_matrix_coarse_age_distribution(df) if coarse else df


def _contact_matrix_coarse_age_distribution(df, ratio=0.68):
    """
    Change contact matrix.

    We assume that in the bracket 70+, we have 68% of the population is in the
    70-79 bracket and 32% is in the 80+ bracket. This is consistent with the
    average worldwide distribution, but may be slightly different per country.
    """

    row = df.iloc[-1:, :]
    row.index = ["80+"]
    df = pd.concat([df, row])
    df.index = [*df.index[:-2], "70-79", "80+"]

    col = df.pop("70+").values
    df["70-79"] = ratio * col
    df["80+"] = (1 - ratio) * col
    data = np.zeros((9, 9))

    # Last two rows and cols
    data[-2:, -2:] = df.values[-2:, -2:]
    for i in range(len(COARSE_INDEX) - 2):
        data[-2:, i] = df.values[-2:, 2 * i : 2 * i + 2].sum(1)
        data[i, -2:] = df.values[2 * i : 2 * i + 2, -2:].sum(0)

    # Middle
    for i in range(len(COARSE_INDEX) - 2):
        for j in range(len(COARSE_INDEX) - 2):
            data[i, j] = df.values[2 * i : 2 * i + 2, 2 * j : 2 * j + 2].sum()

    return pd.DataFrame(data, columns=COARSE_INDEX, index=COARSE_INDEX)


if __name__ == "__main__":
    c = "Italy"
    from covid.data import age_distribution

    print(contact_matrix(c, infer=True))
