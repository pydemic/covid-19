import datetime
from types import MappingProxyType

import numpy as np
import pandas as pd

from ..types import cached
from .plot import Plot

NOW = datetime.datetime.now()
TODAY = datetime.date(NOW.year, NOW.month, NOW.day)


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
    sub_groups = None

    # Query data and shape properties
    is_empty = property(lambda self: self.data.shape[1] == 0)
    columns = None

    # Auxiliary accessors and sub-attributes
    plot = cached(lambda self: self.plot_class(self))
    plot_class = Plot

    # Solver and numerical method parameters
    steps_per_day = 2
    dt = 1.0
    max_simulation_period = 5 * 365

    # Dynamic queries and epidemic state
    time = 0.0
    x0 = None
    is_spreading = True

    # Reporting options
    start_date = TODAY

    @classmethod
    def main(cls, *args, **kwargs):
        """
        Executes the default action for the model. Convenient for making quick
        and dirt CLI tools.
        """
        m = cls(*args, **kwargs)
        m.run()
        print(m)
        m.plot(show=True)
        return m

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

        if not hasattr(self, 'display_columns'):
            self.display_columns = self.columns
        if not hasattr(self, 'data'):
            self.data = pd.DataFrame(columns=self.columns)

    def __str__(self):
        return self.summary()

    def __iter__(self):
        x = self.x0
        dt = self.dt / self.steps_per_day
        t = self.time
        while True:
            for i in range(self.steps_per_day):
                x = self.rk4_step(x, t, dt)
                t += dt
            yield x

    def __getitem__(self, item):
        try:
            method = getattr(self, f'get_data_{item}')
        except AttributeError:
            return self.data[item]
        else:
            return method(self.data)

    def copy(self, **kwargs):
        """
        Create a copy of simulation.
        """
        cls = type(self)
        obj = cls.__new__(cls)
        for k, v in self.__dict__.items():
            v = kwargs.get(k, v)
            setattr(obj, k, v)
        return obj

    def diff(self, x, t):
        """
        Derivative function for state.
        """
        raise NotImplementedError('implement in subclass')

    def rk4_step(self, x, t, dt, watcher=None):
        """
        A single RK4 iteration step.
        """
        k1 = self.diff(x, t)
        k2 = self.diff(x + 0.5 * dt * k1, t + 0.5 * dt)
        k3 = self.diff(x + 0.5 * dt * k2, t + 0.5 * dt)
        k4 = self.diff(x + 1.0 * dt * k3, t + 1.0 * dt)
        v = (k1 + 2 * k2 + 2 * k3 + k4) / 6
        if watcher is not None:
            watcher(x, v, t, dt)
        return x + v * dt

    def step(self, x, t=None, dt=1.0, watcher=None):
        """
        A single day step. It will perform `self.steps_per_day` RK4 iterations
        in the given time period.

        If t and dt are omitted, uses current time and dt=1.0.
        """
        dt /= self.steps_per_day
        t = self.time if t is None else t

        for i in range(self.steps_per_day):
            x = self.rk4_step(x, t, dt, watcher=watcher)
            t += dt
        return x

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

    def run(self, duration=None, convergence=None, watcher=None) -> 'Model':
        """
        Run simulation until dynamics can be considered resolved.

        Args:
            duration:
                Maximum duration of simulation.
            convergence:
                If given, test for convergence after each simulation step by
                passing (x_old, x_new, t, dt)
            watcher:
                If given, is executed with (x_old, v, t, dt) for each step
                and can track simulation variables during execution.
        """
        x = np.asarray(self.x0)
        t = self.time
        dt = self.dt
        ts = [self.time]
        xs = [x]
        convergence = convergence or self.get_convergence_function()
        watcher = watcher or self.get_watcher_function()
        tf = t + self.max_simulation_period if duration is None else t + duration

        while True:
            x_ = np.asarray(self.step(x, t, dt, watcher=watcher))
            t += dt
            xs.append(x_)
            ts.append(t)

            if t >= tf or convergence(x, x_, t, dt):
                break
            x = x_

        self.data = self._to_dataframe(np.array(ts), np.array(xs))
        self._run_post_process()
        return self

    def run_interval(self, dt, watcher=None) -> 'Model':
        """
        Run simulation by given interval.
        """
        tf = self.time + dt
        return self.run(lambda x, x_, t: t >= tf, watcher=watcher)

    def get_convergence_function(self):
        """
        Return a function that tests for convergence.

        Signature of convergence function is fn(x, x_, t, dt) in which x and x_
        are two successive simulation states.
        """
        return lambda *args: False

    def get_watcher_function(self):
        """
        Return a function that tracks simulation state and annotate model,
        save state variables, etc.

        Signature of watcher function is fn(x, v, t, dt) in which x is initial
        state and v is the derivative.
        """
        return None

    def _run_post_process(self):
        """
        Run after simulation is finished.
        """

    def _to_dataframe(self, times, ys) -> pd.DataFrame:
        if self.sub_groups:
            names = 'column', 'age'
            mk_product = pd.MultiIndex.from_product
            columns = mk_product((self.columns, self.sub_groups), names=names)
        else:
            columns = self.columns
        df = pd.DataFrame(ys, columns=columns)
        df.index = times
        return df

    def get_data(self, name, df=None):
        """
        Returns pre-processed from dataframe. Subclasses might implement methods
        such as get_data_<foo> to handle specific names.
        """
        if df is None:
            df = self.data
        try:
            method = getattr(self, f'get_data_{name}')
        except AttributeError:
            return df[name]
        else:
            return method(df)
