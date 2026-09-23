#!/usr/bin/env python3
"""Compatibility wrapper for :mod:`scripts.dataset.clean_yolo_labels_from_metadata`."""

from __future__ import annotations

import sys
from pathlib import Path

_AEB_ROOT = Path(__file__).resolve().parents[1]
if str(_AEB_ROOT) not in sys.path:
    sys.path.insert(0, str(_AEB_ROOT))

from scripts.dataset.clean_yolo_labels_from_metadata import *  # noqa: F401,F403,E402


if __name__ == "__main__":
    raise SystemExit(main())
