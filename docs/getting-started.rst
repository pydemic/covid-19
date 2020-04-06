Getting started
===============

This package implements several different epidemiological models that are relevant to COVID-19
and other transmissible diseases. The most simple ones are in the class of exponential models
with closed form solutions, and are usually good approximations for the behaviour at the outset
of an epidemic.

The most simple of those, the linearized SIR model, has a simple exponential for the
infectious population. Let us create a simple example, and show how it works on code.

>>> from covid.models import eSIR
>>> m = eSIR()

By default, it creates a model with a population of 1 and contaminated with a seed of 1
infectious per million. We can simulate this scenario by calling the run(dt) method with
the desired time interval.

>>> m.run(120)
...

The results of the simulation are exposed as pandas dataframes and can be easily
processed, plotted, and analyzed. The time series for any component of the model can be
extracted using Python's indexing notation

>>> infectious_ts = m["infectious"]  # A Pandas data frame
>>> infectious_ts.plot()
...

Covid uses a clever notation that allow us to make convenient transformations in the
resulting components by simply appending the desired transformations after the
component name.

>>> m["infectious:days"]  # A Pandas dataframe indexed by days instead of dates
...

It also recognizes the shorthand notation for each compartment and allows some advanced
indexing tricks such as slicing and retrieving several columns at once.

>>> m[["S", "I", "R"]]
...
>>> m["S:trim"]


Model parameters
----------------

The model exposes all relevant epidemiological parameters as class attributes.

>>> m.R0, m.infectious_period
(2.74, 3.64)

Some parameters can be naturally expressed in different equivalent mathematical forms,
or have common aliases or shorthand notations. Covid makes sure to keep everything
in sync.

>>> m.infectious_period = 4
>>> m.gamma
0.25

The parameters can also be accessed using the special ``.params`` attribute, which
exposes the complete list of parameters in a normalized and convenient form. The
``.params`` attribute also stores information about confidence intervals and the
reference used to assign the given point value, when available.

>>> m.params.table()
...


Monte Carlo runs
----------------

#TODO
