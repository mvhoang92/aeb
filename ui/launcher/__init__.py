"""Tk desktop launcher ("AEB Control Center") for the CARLA AEB project.

``launcher.py`` at the repository root is the only supported entry point.  It
makes sure Tkinter is importable (re-executing through the system Python when a
venv lacks it) before importing the GUI modules of this package.

Module map:

* ``config``     paths, scenario/app/test catalogues, prerequisite check
* ``commands``   pure, Tk-free command builders and ``command_text``
* ``processes``  subprocess management and CARLA process helpers
* ``theme``      colours, fonts and ttk styles
* ``widgets``    reusable widgets (command preview, ...)
* ``pages``      one mixin per workflow page
* ``app``        the ``AebLauncher`` window
"""
