"""AEB Test Bench v2: an experiment-oriented launcher, independent of v1.

The package is split into Tk-free modules that define *what* is run
(``catalog``, ``policies``, ``plan``, ``results``, ``execution``) and the Tk
user interface (``theme``, ``widgets``, ``app``).  The Tk-free modules are
Python 3.7 compatible so they are covered by the project test runner; the GUI
runs under the system Python 3 that ships Tk.

The test bench only *builds commands* for the existing scenario runners and
*reads* scenario YAML and run logs.  It never writes configs or evidence.
"""
