import datetime
from numbers import Real
from pprint import pformat
from types import MappingProxyType
from typing import Sequence

import numpy as np
import pandas as pd

from .plot import Plot
from ..types import cached

NOW = datetime.datetime.now()
TODAY = datetime.date(NOW.year, NOW.month, NOW.day)
DAY = datetime.timedelta(days=1)


class ModelMeta(type):
    """
    Meta class for model types.

    Reset the EXAMPLES dictionary for each sub-model.
    """

    def __init__(cls, name, bases, ns):
        try:
            ns["EXAMPLES"] = MappingProxyType(ns["EXAMPLES"])
        except KeyError:
            pass

        super().__init__(name, bases, ns)


class Model(metaclass=ModelMeta):
    """
    Base class for all Epidemic models.
    """

    EXAMPLES = MappingProxyType({})
    OPTIONS = {}
    sub_groups = None

    # Query datasets and shape properties
    is_empty = property(lambda self: self.data.shape[1] == 0)
    columns = None

    # Auxiliary accessors and sub-attributes
    plot: Plot = cached(lambda self: self.plot_class(self))
    plot_class = Plot

    # Solver and numerical method parameters
    steps_per_day = 4
    dt = 1.0
    max_simulation_period = 5 * 365

    # Dynamic queries and epidemic state
    time = 0.0
    state = None
    is_spreading = True

    # Reporting options
    start_date = TODAY

    @classmethod
    def main(cls, *args, **kwargs):
        """
        Executes the default action for the model. Convenient for making quick
        and dirt CLI tools.
        """
        import click

        kind_map = {"int": int, "float": float, "str": str}

        @click.option("--plot", is_flag=True, help="Display plot")
        @click.option("--debug", is_flag=True, help="Display debug information")
        def cli(plot=False, debug=False, **kwargs_):
            kwargs_ = {k: v for k, v in kwargs_.items() if v is not None}
            kwargs_ = {**kwargs, **kwargs_}
            m = cls._main(*args, **kwargs_)
            m.run()
            print(m)
            if debug:
                print("\n\nDEBUG SYMBOLS")
                for k, v in vars(m).items():
                    print(k, "=", pformat(v))
            if plot:
                m.plot(show=True)

        for cmd, help in list(cls.OPTIONS.items())[::-1]:
            cmd, _, kind = cmd.partition(":")
            kind = kind_map[kind or "float"]
            cmd = cmd.replace("_", "-")
            cli = click.option(f"--{cmd}", help=help, type=kind)(cli)
        cli = click.command()(cli)
        cli()

    @classmethod
    def _main(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        if args:
            (key,) = args
            default = self.EXAMPLES[key]
            kwargs = {**default, **kwargs}

        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                raise TypeError(f"invalid argument: {k}")

        if not hasattr(self, "display_columns"):
            self.display_columns = self.columns
        if not hasattr(self, "datasets"):
            self.data = pd.DataFrame(columns=self.columns)

    def __str__(self):
        return self.summary()

    def __iter__(self):
        x = self.state
        dt = self.dt / self.steps_per_day
        t = self.time
        while True:
            for i in range(self.steps_per_day):
                x = self.rk4_step(x, t, dt)
                t += dt
            yield x

    def __getitem__(self, item):
        if isinstance(item, str):
            if ":" in item:
                col, *methods = item.split(":")
                fn, *fns = [getattr(self, f"get_{m}") for m in methods]
                res = fn(col)
                for fn in fns:
                    res = fn(res)
                return res
            else:
                try:
                    method = getattr(self, f"get_data_{item}")
                except AttributeError:
                    raise KeyError(item)
                else:
                    return method(self.data)
        else:
            cls = type(item)
            raise TypeError(f"invalid index type: {cls.__name__}")

    def get_dates(self, df):
        """
        Getitem transformer that convert integer indexes to dates.
        """
        df = self[df] if isinstance(df, str) else df
        try:
            idx = df.index
        except AttributeError:
            times: Sequence = self.time_to_dates(np.arange(len(df)))
            return pd.DataFrame(df, index=times)
        else:
            df = df.copy()
            df.index = self.time_to_dates(idx)
            return df

    def time_to_dates(self, times: Sequence, start_date=None, delta=None) -> np.ndarray:
        """
        Convert an array of numerical times to dates.

        Args:
            times:
                Sequence of times.
            start_date:
                Starting date. If not given, uses either `self.start_date` or
                the current day.
            delta:
                Conversion factor (a number or timedelta). If not given, uses
                either `self.time_delta` or the current day. The time step
                corresponding to a difference of 1.0.
        """
        if start_date is None:
            start_date = getattr(self, "start_date", TODAY)
        if delta is None:
            delta = getattr(self, "time_delta", DAY)
        if isinstance(delta, Real):
            delta = datetime.timedelta(days=float(delta))

        data = [start_date + t * delta for t in times]
        return np.array(data) if data else np.array([], dtype=datetime.date)

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
        raise NotImplementedError("implement in subclass")

    def integral(self, series):
        """
        Compute numerical integral of series.
        """
        return (series * self.dt).sum()

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
        self.x = x = x + v * dt
        self.time = t + dt
        return x

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

    def run(self, duration=None, convergence=None, watcher=None) -> "Model":
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
        x = np.asarray(self.state)
        t = self.time
        dt = self.dt
        ts = [self.time]
        xs = [x]
        convergence = convergence or self.get_convergence_function()
        watcher = watcher or self.get_watcher_function()
        tf = float("inf") if duration is None else t + duration
        tmax = t + self.max_simulation_period

        while True:
            x_ = np.asarray(self.step(x, t, dt, watcher=watcher))
            t += dt
            xs.append(x_)
            ts.append(t)
            x = x_

            if duration is None and (convergence(x, x_, t, dt) or t > tf):
                break
            elif t > tmax or t > tf:
                break

        df = self._to_dataframe(np.array(ts), np.array(xs))
        if len(self.data):
            self.data = self.data.append(df.iloc[1:])
        else:
            self.data = df
        self._run_post_process()
        self.state = x
        return self

    def run_interval(self, dt, watcher=None) -> "Model":
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
            names = "column", "age"
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
            method = getattr(self, f"get_data_{name}")
        except AttributeError:
            return df[name]
        else:
            return method(df)

    def summary(self):
        return "Model"


import splinter
