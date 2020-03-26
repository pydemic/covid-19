from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).parent.parent / 'datasets'
COARSE_INDEX = (
    '0-9', '10-19', '20-29', '30-39', '40-49', '50-59', '60-69',
    '70-79', '80+',
)

# Contact matrix information
CONTACT_MATRIX_COUNTRIES = [
    'Belgium', 'Finland', 'Germany', 'Great Britain', 'Italy',
    'Luxembourg', 'Netherlands', 'Poland',
]
CONTACT_MATRIX_IDS = [c.lower() for c in CONTACT_MATRIX_COUNTRIES]

# List of countries
COUNTRIES = {
    'Afghanistan', 'Albania', 'Algeria', 'Angola', 'Antigua and Barbuda', 'Argentina',
    'Armenia', 'Aruba', 'Australia', 'Austria', 'Azerbaijan', 'Bahamas', 'Bahrain',
    'Bangladesh', 'Barbados', 'Belarus', 'Belgium', 'Belize', 'Benin', 'Bhutan',
    'Bolivia', 'Bosnia and Herzegovina', 'Botswana', 'Brazil', 'Brunei Darussalam',
    'Bulgaria', 'Burkina Faso', 'Burundi', 'Cabo Verde', 'Cambodia', 'Cameroon', 'Canada',
    'Central African Republic', 'Chad', 'Channel Islands', 'Chile', 'China',
    'Colombia', 'Comoros', 'Congo', 'Costa Rica', 'Croatia', 'Cuba', 'Curaçao', 'Cyprus',
    'Czechia', "Côte d'Ivoire", 'Democratic Republic of the Congo', 'Denmark', 'Djibouti',
    'Dominican Republic', 'Ecuador', 'Egypt', 'El Salvador', 'Equatorial Guinea',
    'Eritrea', 'Estonia', 'Eswatini', 'Ethiopia', 'Fiji', 'Finland', 'France',
    'French Guiana', 'French Polynesia', 'Gabon', 'Gambia',
    'Georgia', 'Germany', 'Ghana', 'Greece', 'Grenada', 'Guadeloupe', 'Guam', 'Guatemala',
    'Guinea', 'Guinea-Bissau', 'Guyana', 'Haiti', 'Honduras', 'Hong Kong', 'Hungary',
    'Iceland', 'India', 'Indonesia', 'Iran', 'Iraq', 'Ireland', 'Israel', 'Italy',
    'Jamaica', 'Japan', 'Jordan', 'Kazakhstan', 'Kenya', 'Kiribati', 'Kuwait',
    'Kyrgyzstan', 'Laos', 'Latvia', 'Lebanon', 'Lesotho', 'Liberia', 'Libya', 'Lithuania',
    'Luxembourg', 'Macao', 'Madagascar', 'Malawi', 'Malaysia', 'Maldives', 'Mali',
    'Malta', 'Martinique', 'Mauritania', 'Mauritius', 'Mayotte', 'Melanesia', 'Mexico',
    'Micronesia', 'Moldova', 'Mongolia', 'Montenegro', 'Morocco', 'Mozambique', 'Myanmar',
    'Namibia', 'Nepal', 'Netherlands', 'New Caledonia', 'New Zealand', 'Nicaragua',
    'Niger', 'Nigeria', 'North Korea', 'North Macedonia', 'Norway', 'Oman',
    'Pakistan', 'Palestine', 'Panama', 'Papua New Guinea', 'Paraguay', 'Peru',
    'Philippines', 'Poland', 'Portugal', 'Puerto Rico', 'Qatar', 'Romania',
    'Russia', 'Rwanda', 'Réunion', 'Saint Lucia', 'Saint Vincent and the Grenadines',
    'Samoa', 'Sao Tome and Principe', 'Saudi Arabia', 'Senegal', 'Serbia', 'Seychelles',
    'Sierra Leone', 'Singapore', 'Slovakia', 'Slovenia', 'Solomon Islands', 'Somalia',
    'South Africa', 'South Korea', 'South Sudan', 'Spain', 'Sri Lanka', 'Sudan',
    'Suriname', 'Sweden', 'Switzerland', 'Syria', 'Taiwan', 'Tajikistan', 'Tanzania',
    'Thailand', 'Timor-Leste', 'Togo', 'Tonga', 'Trinidad and Tobago', 'Tunisia',
    'Turkey', 'Turkmenistan', 'Uganda', 'Ukraine', 'United Arab Emirates',
    'United Kingdom', 'United States',
    'United States Virgin Islands', 'Uruguay', 'Uzbekistan', 'Vanuatu', 'Venezuela',
    'Vietnam', 'Western Sahara', 'Yemen', 'Zambia', 'Zimbabwe',
}
COUNTRY_ALIASES = {
    'USA': 'United States',
    'United States of America': 'United States',
    'UK': 'United Kindom',
}
COUNTRY_ALIASES.update({k.lower(): v for k, v in COUNTRY_ALIASES.items()})
COUNTRY_ALIASES.update({k.lower(): k for k in COUNTRIES})
COUNTRY_ALIASES.update({k: k for k in COUNTRIES})


def contact_matrix(country='mean', physical=False, coarse=False) -> pd.DataFrame:
    """
    Load contact matrix for country.

    If coarse is True, return a decennial distribution that is compatible with
    other data used in this package like mortality rates and coarse age
    distributions.
    """
    which = 'physical' if physical else 'all'
    path = DATA / 'contact_matrix' / f'{country.lower()}-{which}.csv'
    df = pd.read_csv(path, index_col=0)
    return coarse_age_distribution(df) if coarse else df


def coarse_age_distribution(df, ratio=0.68):
    """
    Change contact matrix.

    We assume that in the braket 70+, we have 68% of the population is in the
    70-79 bracket and 32% is in the 80+ bracket. This is consistent with the
    average worldwide distribution, but may be slightly different per country.
    """

    row = df.iloc[-1:, :]
    row.index = ['80+']
    df = pd.concat([df, row])
    df.index = [*df.index[:-2], '70-79', '80+']

    col = df.pop('70+').values
    df['70-79'] = ratio * col
    df['80+'] = (1 - ratio) * col
    data = np.zeros((9, 9))

    # Last two rows and cols
    data[-2:, -2:] = df.values[-2:, -2:]
    for i in range(len(COARSE_INDEX) - 2):
        data[-2:, i] = df.values[-2:, 2 * i: 2 * i + 2].sum(1)
        data[i, -2:] = df.values[2 * i: 2 * i + 2, -2:].sum(0)

    # Middle
    for i in range(len(COARSE_INDEX) - 2):
        for j in range(len(COARSE_INDEX) - 2):
            data[i, j] = df.values[2 * i: 2 * i + 2, 2 * j: 2 * j + 2].sum()

    return pd.DataFrame(data, columns=COARSE_INDEX, index=COARSE_INDEX)
