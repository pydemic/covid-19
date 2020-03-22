========
Covid-19
========

This is a Python library that simulates COVID-19 outbreaks. The main focus is on Brazil, but it
includes demographic data about other countries and can be adapted with relative ease. This library
implements the RSEICHA model (yet to be published, we will link the preprint here). One version,
`covid.models.RSEICHADemografic` considers demographic information and the other, `covid.models.RSEICHA`
just uses generic compartments.

Usage
=====

You can run models from the command line::

$ python -m covid.models.rseicha
...

Or, more typically, from Python code

>>> from covid.models import RSEICHA
>>> m = RSEICHA(region='Italy')
>>> run = m.run()
>>> run.plot()
>>> print(run)


Installation
============

Either clone this repository and install locally using `flit install -s` or use
`pip install covid-19`.
