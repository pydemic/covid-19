from numbers import Number
from types import SimpleNamespace
from typing import NamedTuple, Optional, Callable, Union


class Parameter(NamedTuple):
    """
    Represents a parameter
    """

    value: Number
    ref: Optional[str] = None
    distribution: Optional[Union[Callable, str]] = None

    def __str__(self):
        suffix = []
        if self.ref:
            suffix.append(str(self.ref))
        if self.distribution and not isinstance(self.distribution, SimpleNamespace):
            suffix.append(str(self.distribution))
        suffix = ", ".join(suffix)
        return f"{self.value} ({suffix})" if suffix else str(self.value)


class Parameters:
    """
    Represents a set of parameters.
    """

    __slots__ = ("name", "refs", "distributions", "__dict__")

    def __init__(self, name=None, **kwargs):
        type(self).name.__set__(self, name or type(self).__name__)
        type(self).refs.__set__(self, {})
        type(self).distributions.__set__(self, {})

        for k, v in kwargs.items():
            ref = rvs = None
            if isinstance(v, tuple):
                v, ref, rvs = v
            super().__setattr__(k, v)
            if ref is not None:
                self.refs[k] = ref
            if rvs is None:
                rvs = SimpleNamespace(rvs=cte(v))
            self.distributions[k] = rvs

    def __setattr__(self, k, v):
        raise TypeError(
            f"Parameters are immutable. Use param.copy({k}={v!r}) to create a copy with "
            f"different values"
        )

    def __iter__(self):
        refs = self.refs.get
        rvs = self.distributions.get
        for k, v in self.__dict__.items():
            yield k, Parameter(v, refs(k), rvs(k))

    def __str__(self):
        return self.summary()

    def __repr__(self):
        args = (f"{k}={v.value!r}" for k, v in self)
        args = ", ".join(args)
        cls = type(self).__name__
        return f"{cls}({self.name!r}, {args})"

    def copy(self, **kwargs):
        """
        Copy, possibly overwriting some values.
        """
        cls = type(self)
        for k, v in kwargs.items():
            if hasattr(self, k):
                kwargs[k] = v
            else:
                raise AttributeError(f"invalid attribute: {k}")

        kwargs = {**self.__dict__, **kwargs}
        return cls(self.name, **kwargs)

    def summary(self):
        lines = [f"Parameters ({self.name}):", *(f"  - {k}: {p}" for k, p in self)]
        return "\n".join(lines)


# Return a function always return the same value
cte = lambda v: lambda: v


def param(value, ref=None, distrib=None):
    """
    Declares a parameter with optional reference attribution and RVS
    attribution.
    """
    return Parameter(value, ref, distrib)
