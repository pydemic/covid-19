import matplotlib.pyplot as plt
import streamlit as st

import covid
from covid.models import SEICHARDemographic as SEICHAR
from covid.data import countries

st.title('Calculadora de pressão assistencial em decorrência da COVID-19')
e = 1e-50

#
# Collect parameters on the sidebar
#

# Select region
st.sidebar.markdown('## Região')

country = 'brazil'
states = countries.states(country)
sub_regions = countries.sub_regions(country)
cities = countries.cities(country)
region: covid.Region

state = st.sidebar.selectbox('Estado', ['Brasil', *states['name']])
if state == 'Brasil':
    region = covid.region('Brazil')
else:
    state_code = states[states.name == state].index[0]
    sub_regions = sub_regions[sub_regions.state == state_code]
    sub_region = st.sidebar.selectbox('Região', ['Tudo', *sub_regions['name']])

    if sub_region == 'Tudo':
        region = covid.region(f'Brazil/{state_code} (metro)')
    else:
        cities = countries.cities(country)
        cities = cities[cities.sub_region == sub_region]
        city = st.sidebar.selectbox('Cidade ou município', ['Tudo', *cities['name']])
        region = covid.region(f'Brazil/{city}')

# Simulation
st.sidebar.text('\n')
st.sidebar.markdown('## Opções da simulação')
period = st.sidebar.slider('Dias de simulação', 0, 180, value=60)
t0 = st.sidebar.date_input('Data inicial')
kwargs = {'seed': st.sidebar.number_input('Número de casos detectados', min_value=1)}

# Healthcare system
st.sidebar.text('\n')
st.sidebar.markdown('## Capacidade hospitalar')
st.sidebar.markdown('### Leitos clínicos')
hospital_beds_total = st.sidebar.number_input(
    'Total',
    min_value=0,
    value=int(region.hospital_total_capacity),
)
occupied_hospital_beds = 0.01 * st.sidebar.slider(
    'Ocupados (%)',
    min_value=.0,
    max_value=100.0,
    value=100 * region.hospital_occupancy_rate,
)

st.sidebar.markdown('### Leitos de UTI')
icu_beds_total = st.sidebar.number_input(
    'Total',
    min_value=0,
    value=int(region.icu_total_capacity),
    key='icu_total',
)
occupied_icu_beds = 0.01 * st.sidebar.slider(
    'Ocupados (%)',
    key='icu_used',
    min_value=.0,
    max_value=100.0,
    value=100 * region.icu_occupancy_rate,
)

# Epidemiology
st.sidebar.text('\n')
st.sidebar.markdown('## Epidemiologia')
scenario = st.sidebar.selectbox('Cenário', ['Rápido', 'Lento', 'Personalizado'])
if scenario == 'Rápido':
    kwargs.update({'R0': 3.5})
elif scenario == 'Lento':
    kwargs.update({'R0': 2.5})
else:
    kwargs.update({
        'R0': st.sidebar.slider(
            "Fator de contágio (R0)",
            min_value=0.0,
            max_value=5.0,
            value=2.74,
        ),
        'sigma': 1.0 / (st.sidebar.slider(
            "Período de incubação do vírus",
            min_value=1.0,
            max_value=10.0,
            value=5.0,
        ) + e),
        'gamma': 1.0 / (st.sidebar.slider(
            "Período infeccioso",
            min_value=1.0,
            max_value=14.0,
            value=4.0,
        ) + e),
        'prob_fatality': 0.01 * st.sidebar.slider(
            "Taxa de mortalidade média",
            min_value=0.0,
            max_value=100.0,
            value=2.0,
        ),
    })

# Intervention
st.sidebar.text('\n')
st.sidebar.markdown("## Intervenção")
baseline, social_distance = interventions = [
    'Nenhuma intervenção',
    'Redução de contato social',
]
intervention = st.sidebar.selectbox('Cenário', interventions)

if intervention == baseline:
    pass
elif intervention == social_distance:
    st.sidebar.slider("Dias após data inicial para início de intervenção")
    st.sidebar.slider("Redução do fator de contágio (R0) após intervenção")

#
# Run simulation
#
kwargs.setdefault('prob_symptomatic', 0.5)
model = SEICHAR(region=region, seed=seed, **kwargs)
model.run(period)
model.plot.healthcare_overflow()
st.write(plt.gcf())

#
# Write results
#
st.text(str(model))
st.button('Atualizar')
st.write(model.data)
