#
# Clinical parameters
#
CLINICAL_DEFAULT = Parameters(
    "Default",
    hospitalization_period=10.0,
    icu_period=7.5,
    prob_hospitalization=0.18,
    prob_icu=0.05 / 0.18,
    prob_fatality=0.015 / 0.05,
    prob_no_hospitalization_fatality=0.25,
    prob_no_icu_fatality=1.00,
)
clinical = SimpleNamespace(default=CLINICAL_DEFAULT)
