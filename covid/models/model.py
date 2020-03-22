from types import MappingProxyType

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import integrate


class ModelMeta(type):
    """
    Meta class for model types.

    Reset the EXAMPLES dictionary for each sub-model.
    """

    def __init__(cls, name, bases, ns):
        try:
            ns['EXAMPLES'] = MappingProxyType(ns['EXAMPLES'])
        except KeyError:
            pass

        super().__init__(name, bases, ns)


class Model(metaclass=ModelMeta):
    """
    Base class for all Epidemic models.
    """
    EXAMPLES = MappingProxyType({})
    PERIOD = 365.25 / 12
    MAX_PERIOD = 5 * 365.25
    STEPS = 50
    X_TOL = 0.1
    x0 = None
    columns = None
    sub_groups = ()

    @classmethod
    def main(cls, *args, **kwargs):
        """
        Executes the default action for the model. Convenient for making quick
        and dirt CLI tools.
        """
        m = cls(*args, **kwargs)
        run = m.run()
        print(run)
        run.plot()
        plt.show()
        return m, run

    def __init__(self, *args, **kwargs):
        if args:
            key, = args
            default = self.EXAMPLES[key]
            kwargs = {**default, **kwargs}

        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                raise TypeError(f'invalid argument: {k}')
        if 'display_columns' not in kwargs:
            self.display_columns = self.columns

    def diff(self, x, t):
        """
        Derivative function for state.
        """
        raise NotImplementedError('implement in subclass')

    def has_converged(self, times, xs):
        """
        Read a sequence of times and a sequence of states and conclude if
        simulation has already converged to a steady state.
        """
        if len(times) > 2000:
            return True
        if times[-1] >= self.MAX_PERIOD:
            return True
        if (np.abs(xs[-1] - xs[-2]) < self.X_TOL / self.STEPS).all() \
                and self.has_burst(times, xs):
            return True
        return False

    def has_burst(self, times, xs):
        """
        Read a sequence of times and a sequence of states and conclude if
        simulation has already experienced or is experiencing an epidemic burst.

        It returns False only when it is likely that the burst has not yet
        happened.
        """
        return xs.std(1).max() > 100 * self.X_TOL

    def trim_to_burst(self, times, xs):
        """
        Find the epidemic peak and trim datasets to be around this peak.
        """
        tol = 0.1 * xs.std(1)
        x0 = xs[0]
        xf = xs[-1]

        i = 0
        for x in xs:
            if np.abs(x - x0) > tol:
                break
            i += 1

        j = len(xs)
        for x in reversed(xs):
            j -= 1
            if np.abs(x - xf) > tol:
                break

        return times[i:j], xs[i:j]

    def run(self) -> 'Run':
        """
        Run simulation until dynamics can be considered to be resolved.
        """
        time = 0.0
        x = self.x0
        dt = self.PERIOD
        steps = self.STEPS
        times = np.array([time], dtype=float)
        xs = np.array([x], dtype=float)

        while True:
            times_, xs_ = self._run_interval(dt, time, x, steps)
            times = np.concatenate([times, times_[1:]])
            xs = np.concatenate([xs, xs_[1:]])
            time = times[-1]
            x = xs[-1]

            if self.has_converged(times, xs):
                break

        return self._to_result(times, xs)

    def run_interval(self, dt, t0=0, x0=None, steps=100) -> 'Run':
        """ == 1
        Run simulation by given interval
        """
        return self._to_result(*self._run_interval(dt, t0, x0, steps))

    def _run_interval(self, dt, t0, x0, steps):
        x0 = self.x0 if x0 is None else x0
        times = np.linspace(t0, t0 + dt, steps)
        ys = integrate.odeint(self.diff, x0, times)
        return times, ys

    def _to_result(self, times, ys) -> 'Run':
        cls = getattr(self, 'run_class', Run)
        return cls(self._to_dataframe(times, ys), self)

    def _to_dataframe(self, times, ys) -> pd.DataFrame:
        if self.sub_groups:
            names = 'column', 'age'
            columns = pd.MultiIndex.from_product((self.columns, self.sub_groups), names=names)
        else:
            columns = self.columns
        df = pd.DataFrame(ys, columns=columns)
        df.index = times
        return df

    def summary(self, run):
        """
        Return a summary string for the given run. Used by run instances to
        perform string conversion.
        """
        dic = self.summary_map(run)
        keys = dic.keys()
        size = max(map(len, keys))
        keys = map(lambda x: x.ljust(size), keys)
        values = map(str, dic.values())
        return '\n'.join(f'{k} : {v}' for k, v in zip(keys, values))

    def summary_map(self, run):
        """
        Convenient access to summary data as a dictionary. Useful for
        subclasses to avoid excessive string formatting operations when
        implementing the summary() method..
        """
        raise NotImplementedError('must be implemented in subclasses')

    def get_data(self, df, name):
        """
        Returns pre-processed from dataframe. Subclasses might implement methods
        such as get_data_<foo> to handle specific names.
        """
        try:
            method = getattr(self, f'get_data_{name}')
        except AttributeError:
            return df[name]
        else:
            return method(df)


class Run:
    """
    Represents an execution of the model.
    """
    values = property(lambda self: self.data.values)

    def __init__(self, data, model):
        self.data = data
        self.model = model

    def __str__(self):
        return self.model.summary(self)

    def __getattr__(self, item):
        try:
            return self.model.get_data(self.data, item)
        except ValueError:
            raise AttributeError(item)

    def plot(self, show=False):
        res = self.data[self.model.display_columns].plot()
        if show:
            plt.show()
        else:
            return res
