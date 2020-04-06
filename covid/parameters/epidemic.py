from types import SimpleNamespace
import sidekick as sk
from sidekick import placeholder as _

from .base import Parameters


class EpidemicParameters(Parameters):
    gamma = sk.property(1 / _.infectious_period)
    sigma = sk.property(1 / _.incubation_period)


#
# Epidemiological parameters
#
EPIDEMIC_DEFAULT = EpidemicParameters(
    "Default",
    R0=2.74,
    rho=0.4,
    prob_symptomatic=0.14,
    incubation_period=3.69,
    infectious_period=3.47,
)

epidemic = SimpleNamespace(default=EPIDEMIC_DEFAULT)
