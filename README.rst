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
`pip install covid-models`. If you do not have flit, install it using either your distribution
package manager or use `pip install flit --user`.


The model
=========

RSEICHA is a compartmental model with 8 compartments: Recovered, Fatalities, Susceptible, Exposed,
Infectious, Critical (require ICU care), Hospitalized (or requires hospitalization) and Asymptomatic.

It is governed by the following dynamics:

...

Basic theoretical results
-------------------------

If we ignore the "Exposed" compartment, it is easy to derive R0 for this model. We must, however,
consider the number of equivalent infectious :math:`I_e = I + \mu A`, in which asymptomatic individuals
contribute less to the overall number of infectious than symptomatic cases.

When :math:`S \simeq N`, this quantity experience an exponential growth and we can associate R0 with
:math:`R_0 = \frac{\beta}{\gamma}\left[1 - (1 - \mu) p_s\right]`


Default parameters
------------------

+==================+======================+====================================+
| Parameter        | Default value        | Reference                          |
+==================+======================+====================================+
|

Parameters and references
=========================



Epidemiological parameters
--------------------------


Clinical parameters
-------------------



Required medical resources
--------------------------
