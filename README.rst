=========
Covid
=========

Toy model is a Python library for creating complex dynamic systems modelled as ordinary
differential equations. This is a very broad category, which notably includes particle
systems in Physics, simplified economic, demographic, and climate models, and many others.

Implementing an ODE solver in Python, specially one that uses simple methods like Euler integration,
is trivial. However, as the model grows in size and includes new dynamics and sub-systems, implementation 
often descends into giant blob of barely functional, heroically maintainable (but sometimes delicious) 
spaghetti code.

Toy Model aims to make such models organized by treating each sub-system as an independent unit that
can be plugged together like lego bricks. This kind of organization may be useful in a broad
range of disciplines: in Physics, we could create independent isolated systems and join them with a 
force between them later; in Economy, we could create an economy model,
a climate model and a third model that correlate emissions with economic output. There are many
other useful examples. This kind of organization makes it easy to test and to validate each model
separately, and then join them and remix models in different combinations and with different 
parametrizations.

Toy Model treats each model class as an specification of a dynamical system
rather than a concrete implementation of an ODE solver. Implementation is created on-the-fly
the first time the model is run and is compiled from many bits collected from each sub-system.
The point is that, by only declaring the model structure, we can automate the tedious parts
of connecting models together, implementing the solver, plotting, managing state, etc.


Installing
==========

Toy Model is packaged in PyPI_ using flit_. Just ``pip install toy-model`` or use your
favorite method of `installing Python packages`_.

.. _flit: https://flit.readthedocs.io/en/latest/
.. _PyPI: https://pypi.org
.. _installing Python packages: ???


Using the model
===============

Let us start with a simple kinematic model for a particle:

.. code-block:: python

    from toy import Model


    class Particle(Model):
        """
        Simple 2D particle with external acceleration.
        """

        # Variables
        x = 0, '[m] x position',
        y = 0, '[m] y position'
        vx = 0, '[m/s] x velocity'
        vy = 0, '[m/s] y velocity'

        # Constants
        a = -2, '[m/s2] uniform acceleration'

        # Bounds
        bounds = [y >= 0]

        # Derivatives
        D_x = vx
        D_y = vy
        D_vx = 0
        D_vy = a


The ``Particle`` class is just an specification of a dynamic model. It does not store the
state of simulation or any dynamic variables. The actual simulation is executed by calling
the run() method with the specified time range.

>>> model = Particle()
>>> run = model.run(0, 1, 5, vx=1, vy=2.0)  # from t=0, to t=1 in 5 steps

The "run" object stores all intermediary steps of execution and some methods that are
useful to inspect the simulation result. We can, for instance, fetch the final value for
a variable,

>>> run.x
1.0

and its associated time series,

>>> run.x_ts
array([0.  , 0.25, 0.5 , 0.75, 1.  ])

A model run can also be used advance the simulation a few more steps, inspect some running
parameters, saving state, and much more. We refer to the :cls:`Run` documentation for
more details.

The particular details of how we go from a model subclass (e.g., Particle) to a simulation
result involves some sophisticated processing and meta programming. The details of
will be discussed later and are important to understand how
Toy Model works. We will come back to this after showing the most important bits of
the API first.


Structure of a model
====================

Consider the model:

.. code-block:: python

    from sympy import sin


    class ForcedOscillator(Model):
        x = 0, '[m] Position of point mass'
        v = 1, '[m/s] Velocity'
        m = 1, '[kg] Mass'
        k = 1, '[N/m] Spring constant'
        F = 1, '[N] Amplitude of forced oscillation'
        omega = 0.5, '[rad/s] Frequency of oscillation'
        gamma = 0.1, '[kg/s] Damping coefficient'

        # Force
        force = F * sin(omega * t), '[N] External force'

        # Equations
        D_x = v
        D_v = -k * x - gamma * v + force / m


Variables that form a dynamic model can be classified into any of 3 different categories.
First, and perhaps more obviously, are the dynamical variables that we want to solve for,
in this case ``x`` and ``v``. In Toy model, those variables are referred as
"dynamic variables" or simply as "vars". *Vars* are exposed as a dictionary that maps
variable names to their corresponding :cls:`Value` declarations:

>>> m = ForcedOscillator()
>>> m.vars
{'x': Value('x', 0), 'v': Value('v', 1)}

The :cls:`Value` objects store information such as name, bound symbol, units,
description, etc.

The second group of variables is what we call "parameters", or "params". Those are values
that do not change during simulation, such as mass, the spring constant, etc. All *params*
must be reduced to numbers when model is initialized. They don't change.

>>> m.params   # doctest: +ELLIPSIS
{'m': Value('m', 1), 'k': Value('k', 1), ...}

If you only need the initial values, use

>>> m.param_values()
{'m': 1, 'k': 1, 'F': 1, 'omega': 0.5, 'gamma': 0.1}

This distinction is important, because parameters cannot be changed once the
model is initialized, but the initial values for vars can. That is, the run()
method can override vars, but not params.

For instance, that's ok:

>>> m.run(0, 10, v=2)  # doctest: +SKIP

This is an error:

>>> m.run(0, 10, k=2)  # doctest: +SKIP

We can, however, override parameters during model initialization, by creating
different instances of a model class

>>> m1 = ForcedOscillator(k=2)
>>> m2 = ForcedOscillator(k=1)

Some auxiliary variables must be computed at every step of the simulation,
usually because they depend on time or the other dynamic variables. This is
what the "force" term is in the oscillator model.
We refer to those terms as "auxiliary terms" or simply as "aux",

>>> m.aux
{'force': Value('force', sin(0.5*t))}

They are subject to similar restriction as parameters, in that it is not possible
to change computed terms in the run() method, but we can do it during model
initialization. In fact, since we can override expressions to constant numerical
values and vice-versa, the distinction between parameters and computed terms
is only possible after model initialization.

>>> m3 = ForcedOscillator(force=0)
>>> m3.aux
{}
>>> m3.params  # doctest: +ELLIPSIS
{'m': Value('m', 1), ..., 'force': Value('force', 0)}


Composing models
================

Toy Model has several facilities for composing independent models into larger
integrated ones. The most trivial case is when models are independent, and
they are simply merged into a "super" model that simulates both simultaneously.

.. code-block:: python

    class M1(Model):
        x = 1, "A variable with exponential growth"
        k1 = 1, "Growth coefficient"
        D_x = k1 * x

    class M2(Model):
        y = 1, "Another variable with exponential growth"
        k2 = 0.5, "Growth coefficient"
        D_y = k2 * y

We can merge both models with subclassing:

.. code-block:: python

    class M3(M1, M2):
        """
        A composite model with variables from M1 and M2.
        """

This creates a "super" model that has variables both from M1 and M2.
M3 is not that interesting, though, since the dynamics of x and y are still
uncoupled and it doesn't matter much to solve each model separately or
conjointly. In fact, it is probably more efficient to solve each model
separately since in principle it is possible to control the time step and solution
algorithm to better fit each model.

The interesting bits, however, happen when we override variables from
the parent models that couples both dynamics.

.. code-block:: python

    class M4(M1, M2):
        """
        A composite model with variables from M1 and M2.
        """

        k1 = 1 - y
        k2 = 0.5 * (1 - x)


Transforming models
-------------------

Sometimes it is useful to transform our models to replace variable names, default values, etc.
This is particularly useful to prepare models before composing them or to specialize generic
models to some specific application.

Transformation rules can change names of variables, values of coefficients,
initial values, and units. This is all done with specialized functions that take in
model classes and return new transformed classes.


Renaming
........

.. code-block:: python

    from toy model import rename, prefix

    class M1(Model):
        k = 0.1, "Growth coefficient"
        x = 1, "A variable with exponential growth"
        D_x = k * x

    M2 = rename(M1, x='P - Population')
    M3 = rename(M1, x='M - [U$] Money')


Prefixing
.........

.. code-block:: python

    M4 = prefix(M2, 'prey_')
    M5 = prefix(M2, 'predator_')


Set initial conditions
......................

.. code-block:: python

    M6 = fix_values(M2, k=0.2)



Topics
======

* Variables, Parameters, and Computed
* Algebraic expressions and parameter overriding
* Units
* Model fusion and sub-classing
* Model composition and mounting
* Model vectorization
* Sensors, validation, and control
* AOT and JIT compilation
* Plotting
* CLI Apps
* Jupyter widgets and apps
* API reference
* Examples


Class creation and interpretation
---------------------------------

Python has powerful meta programming capabilities and allow us to customize many
aspects of class creation. Toy model uses a somewhat obscure feature of metaclass
programming, which is the ability to change the type of the scope dictionary used
internally during class declaration.

This allow us to turn a class declaration into very simple embedded
interpreter to a domain specific language (eDSL). Python
commands inside Model declaration are reinterpreted as mathematical expressions and
**do not** obey standard Python semantics. This embedded language is largely powered
by Sympy_, which is a Python computer algebra system.

.. _Sympy: https://sympy.pydata.org

