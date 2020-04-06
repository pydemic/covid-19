========
Covid-19
========

.. image:: https://gitlab.com/pydemic/covid-19/badges/master/pipeline.svg
   :target: https://github.com/pydemic/covid-19/commits/master

.. image:: https://gitlab.com/pydemic/covid-19/badges/master/coverage.svg
   :target: https://github.com/pydemic/covid-19/commits/master



This is a Python library that simulates COVID-19 outbreaks. The main focus is on Brazil, but it
includes demographic data about other countries and can be adapted with relative ease. This library
implements the RSEICHA model (yet to be published, we will link the preprint here). One version,
`covid.models.RSEICHADemografic` considers demographic information and the other, `covid.models.RSEICHA`
just uses generic compartments.

**WARNING!**

This library is deprecated and will be replaced by several projects in the Pydemic organization. If you
want to use the library or contribute to its development, please contact the developers first.


Usage
=====

You can run models from the command line::

$ python -m covid.models.seichar

Or, more typically, from Python code

>>> from covid.models import SEICHAR
>>> m = SEICHAR(region='Italy')
>>> run = m.run()
>>> run.plot()
>>> print(run)

Calculator
----------

To serve the app calculator, use::

    $ inv run

Installation
============

Either clone this repository and install locally using `flit install -s` or use
`pip install covid-models`. If you do not have flit, install it using either your distribution
package manager or use `pip install flit --user`.

The model
=========

SEICHAR is a compartmental model with 8 compartments: Recovered, Fatalities, Susceptible, Exposed,
Infectious, Critical (require ICU care), Hospitalized (or requires hospitalization) and Asymptomatic.

It is governed by the following dynamics:

Basic theoretical results
-------------------------

If we ignore the "Exposed" compartment, it is easy to derive R0 for this model. We must, however,
consider the number of equivalent infectious :math:`I_e = I + \mu A`, in which asymptomatic individuals
contribute less to the overall number of infectious than symptomatic cases.

When :math:`S \simeq N`, this quantity experience an exponential growth and we can associate R0 with
:math:`R_0 = \frac{\beta}{\gamma}\left[1 - (1 - \mu) p_s\right]`

Default parameters
------------------

+------------------+----------------------+------------------------------------+
| Parameter        | Default value        | Reference                          |
+==================+======================+====================================+
|                  |                      |                                    |
+------------------+----------------------+------------------------------------+

Parameters and references
=========================

Epidemiological parameters
--------------------------

Clinical parameters
-------------------

Required medical resources
--------------------------

Development
===========

Testing
-------

Simply perform::

    $ inv test

Managing i18n
-------------

To update messages files::

    $ inv makemessages

To compile messages files::

    $ inv compilemessages

To update and compile messages files::

    $ inv i18n

Using rit tunnel
----------------

After installing `rit <https://gitlab.com/ritproject/cli#installation>`_, config your tunnel repo:

- Remotely::

  $ rit config tunnel add repo https://gitlab.com/pydemic/tunnel --name pydemic
  $ rit config tunnel default set pydemic --path .

- Locally::

  $ git clone https://gitlab.com/pydemic/tunnel ../tunnel
  $ rit config tunnel add local ../tunnel --name pydemic
  $ rit config tunnel default set pydemic --path .

Examples of usage:

- If you use docker and docker-compose, you can:

  - Build the development image::

    $ rit tunnel run apps calculator development build

  - Fetch the development docker-compose::

    $ rit tunnel run apps calculator development fetch compose

  - Run the test pipeline::

    $ rit tunnel run apps calculator development test up
    $ rit tunnel run apps calculator development test sync
    $ rit tunnel run apps calculator development test all
    $ rit tunnel run apps calculator development test down

  - Build the production image::

    $ rit tunnel run apps calculator production build

  - Fetch the production docker-compose::

    $ rit tunnel run apps calculator production fetch compose
