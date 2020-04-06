import numpy as np
import pandas as pd
from ..utils import today
from ..parameters import epidemic


class Model:
    """
    Base class for all models.

    Attributes:
        params: A
    """

    # Constants
    DATA_ALIASES = {}

    # Initial values
    params = 1
    date = None
    time = 0
    iter = 0
    state = None

    @classmethod
    def create(cls, params=None):
        new = object.__new__(cls)
        new.set_params(params)
        return new

    def __init__(self, params=None, date=None, **kwargs):
        # params
        # self.set_params(params)
        self.date = date or today()

    #
    # Parameters
    #
    def set_params(self, params):
        """

        Args:
            params:

        Returns:

        """
        self.params = params

    def set_param(self, name, value, *, distrib=None, ref=None):
        """
        Sets a parameter in the model, possibly assigning a distribution and
        reference.
        """
        raise NotImplementedError

    def get_param(self, name):
        """
        Return
        Args:
            name:

        Returns:

        """

    def get_param_value(self, name):
        """

        Args:
            name:

        Returns:

        """

    #
    # Retrieving columns
    #
    def get_data_transformer(self, name):
        if name == "days":
            raise NotImplementedError
        else:
            raise ValueError(f"Invalid transform: {name}")

    def get_data(self, name):
        name = self.DATA_ALIASES.get(name, name)
        return self.data[[name]]

    def __getitem__(self, item):
        if isinstance(item, str):
            col, _, transform = item.rpartition(":")
            if transform:
                fn = self.get_data_transformer(transform)
                return fn(col)
            else:
                return self.get_data(col)

        elif isinstance(item, list):
            raise NotImplementedError
        elif isinstance(item, slice):
            raise NotImplementedError
        else:
            raise TypeError(f"invalid item: {item!r}")

    #
    # Running simulation
    #
    def run(self, time_or_fn):
        """
        Runs the model for the given duration of until the given convergence
        function returns True.
        """
        raise NotImplementedError


class eSIR(Model):
    """
    A simple SIR model linearized around the DFE.
    """

    DATA_ALIASES = {"S": "susceptible", "I": "infectious", "R": "recovered"}

    def run_interval(self, time: int):
        time = int(time)
        ts = np.arange(time)

        S, I, R = self.S(ts), self.I(ts), self.R(ts)
        data = {"susceptible": S, "infectious": I, "recovered": R}
        df = pd.DataFrame(data, index=self.to_dates(ts + self.time))
        self.time += time
        self.data_ts = self.data_ts.append(df)

    #
    # Epidemic curves
    #
    def S(self, t):
        return self.S_value - self.I_value * np.exp(self.K * t)

    def I(self, t):
        return self.I_value * np.exp(self.K * t)

    def R(self, t):
        return self.I_value * np.exp(self.K * t)


m = eSIR()
assert m.R0 == 2.74
assert m.K == m.gamma * 1.74

m.run(120)
assert m["I"] == 1e-6 * np.exp()
