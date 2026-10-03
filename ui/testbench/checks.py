"""Tk-free prerequisite check for ``launcher_v2.py --check``."""

from __future__ import absolute_import

import sys
from pathlib import Path

from ui.testbench.catalog import Catalog
from ui.testbench.execution import carla_listening
from ui.testbench.paths import (
    AEB_ROOT,
    CARLA_PYTHON,
    CARLA_SCRIPT,
    FUSION_RUNNER,
    RADAR_RUNNER,
    logs_root,
)
from ui.testbench.plan import DEFAULT_HOST, DEFAULT_PORT
from ui.testbench.policies import POLICIES


def check_prerequisites(stream=None):
    """Print one line per prerequisite; return 0 when all are present."""
    stream = stream or sys.stdout
    checks = [
        ("CARLA script", Path(CARLA_SCRIPT).is_file(), str(CARLA_SCRIPT)),
        ("Runner Python", Path(CARLA_PYTHON).is_file(), str(CARLA_PYTHON)),
        ("Radar runner", (AEB_ROOT / RADAR_RUNNER).is_file(), RADAR_RUNNER),
        ("Fusion runner", (AEB_ROOT / FUSION_RUNNER).is_file(), FUSION_RUNNER),
    ]
    for policy in POLICIES.values():
        for device, config in sorted(policy.configs.items()):
            checks.append(
                ("Sensor {} {}".format(policy.key, device), (AEB_ROOT / config).is_file(), config)
            )
    try:
        catalog = Catalog.load()
        scenarios = sum(len(suite.scenarios) for suite in catalog.suites)
        checks.append(("Scenario catalog", scenarios > 0, "{} file, {} kịch bản".format(len(catalog.suites), scenarios)))
    except Exception as exc:  # noqa: BLE001 - report any YAML problem
        checks.append(("Scenario catalog", False, str(exc)))
    root = logs_root()
    checks.append(("Log root", Path(root).is_dir(), str(root)))
    for name, passed, detail in checks:
        stream.write("{:<24} {:<8} {}\n".format(name, "OK" if passed else "MISSING", detail))
    online = carla_listening(DEFAULT_HOST, DEFAULT_PORT)
    stream.write("{:<24} {:<8} {}:{}\n".format("CARLA port", "online" if online else "offline", DEFAULT_HOST, DEFAULT_PORT))
    return 0 if all(passed for _, passed, _ in checks) else 2
