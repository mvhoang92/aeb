#!/usr/bin/env python3
"""Compatibility entry point for the historical misspelling ``laucher.py``.

Use :mod:`launcher` for new integrations.  Public names are re-exported so
existing imports and ``/usr/bin/python3 laucher.py`` continue to work.
"""

from __future__ import annotations

from launcher import *  # noqa: F401,F403 - intentional compatibility surface


if __name__ == "__main__":
    raise SystemExit(main())
