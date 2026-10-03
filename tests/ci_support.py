"""Explicit skip guards for tests that need machine-local resources.

GitHub Actions runs the suite with ``AEB_CI=1``.  The runner has no CARLA
0.9.11 PythonAPI egg (it is not published on PyPI; it ships only inside the
CARLA tarball) and no sibling ``../venv`` or ``../CarlaUE4.sh``.  Only under
``AEB_CI=1`` do these guards turn such a missing resource into an explicit
skip.  On a workstation the guards are inert: a missing resource still fails
loudly, so the local suite never silently loses coverage.

This module is not collected by ``unittest discover`` (no ``test`` prefix).
"""

from __future__ import annotations

import importlib
import os
import unittest

IN_CI = os.environ.get("AEB_CI") == "1"

CARLA_EGG_REASON = (
    "CARLA 0.9.11 PythonAPI egg is not on PyPI and is unavailable in CI"
)
CARLA_INSTALL_REASON = (
    "needs the CARLA 0.9.11 install next to the repository "
    "(../CarlaUE4.sh, ../venv/bin/python)"
)


def carla_import_skip_reason(exc):
    """Return the CI skip reason when only ``carla`` is missing, else re-raise.

    Call it from ``except ModuleNotFoundError as exc`` around an import of a
    module that needs the CARLA egg.
    """

    if IN_CI and getattr(exc, "name", None) == "carla":
        return CARLA_EGG_REASON
    raise exc


def probe_carla_import(module_name):
    """Import ``module_name``; return ``None`` or the CI skip reason."""

    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        return carla_import_skip_reason(exc)
    return None


def skip_if(reason):
    """Decorator that skips with ``reason`` (prefixed ``AEB_CI:``) if set."""

    if reason:
        return unittest.skip("AEB_CI: " + reason)
    return lambda obj: obj


def ci_requires(available, reason):
    """Skip under ``AEB_CI=1`` when ``available`` is false; never skip locally."""

    return skip_if(None if (available or not IN_CI) else reason)
