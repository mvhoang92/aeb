"""Filesystem locations used by the test bench (no Tk dependency)."""

from __future__ import absolute_import

import os
from pathlib import Path


AEB_ROOT = Path(__file__).resolve().parents[2]
CARLA_ROOT = AEB_ROOT.parent
CARLA_PYTHON = Path(
    os.environ.get(
        "AEB_TESTBENCH_RUNNER_PYTHON",
        str(CARLA_ROOT / "venv" / "bin" / "python"),
    )
)
CARLA_SCRIPT = CARLA_ROOT / "CarlaUE4.sh"
SCENARIO_ROOT = AEB_ROOT / "configs" / "scenarios"
RADAR_RUNNER = "scripts/run_radar_aeb_scenarios.py"
FUSION_RUNNER = "scripts/run_fusion_aeb_scenarios.py"
CARLA_LOG_FILE = Path("/tmp/aeb-testbench-carla.log")


def logs_root():
    """Run-log root, resolved exactly like the runners resolve it."""
    from infrastructure.workspace import logs_root as workspace_logs_root

    return workspace_logs_root()


def relative_to_repo(path):
    """Repo-relative POSIX path when ``path`` lives inside the repository."""
    path = Path(path)
    try:
        return path.resolve().relative_to(AEB_ROOT).as_posix()
    except ValueError:
        return str(path)
