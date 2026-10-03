#!/usr/bin/env python3
"""Desktop launcher for the CARLA AEB project."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _load_tkinter():
    """Load Tk, falling back to the system GUI Python when a venv omits it."""
    try:
        import tkinter as tkinter_module
        from tkinter import messagebox as messagebox_module
        from tkinter import ttk as ttk_module
        from tkinter.scrolledtext import ScrolledText as scrolled_text_class

        return tkinter_module, messagebox_module, ttk_module, scrolled_text_class
    except ModuleNotFoundError as exc:
        if exc.name != "tkinter":
            raise
        gui_python = Path(
            os.environ.get("AEB_LAUNCHER_PYTHON", "/usr/bin/python3")
        )
        already_reexeced = os.environ.get("AEB_LAUNCHER_REEXEC") == "1"
        if gui_python.is_file() and not already_reexeced:
            environment = os.environ.copy()
            environment["AEB_LAUNCHER_REEXEC"] = "1"
            os.execve(
                str(gui_python),
                [str(gui_python), str(Path(__file__).resolve())] + sys.argv[1:],
                environment,
            )
        raise SystemExit(
            "Tkinter không có trong {}. Hãy chạy bằng /usr/bin/python3 "
            "launcher.py hoặc đặt AEB_LAUNCHER_PYTHON.".format(sys.executable)
        ) from exc


tk, messagebox, ttk, ScrolledText = _load_tkinter()

# The GUI lives in ui/launcher/; these names stay importable from ``launcher``.
from ui.launcher.app import AebLauncher  # noqa: E402
from ui.launcher.commands import command_text  # noqa: E402
from ui.launcher.config import (  # noqa: E402
    AEB_ROOT,
    BRAKE_MODES,
    CARLA_PYTHON,
    CARLA_ROOT,
    CARLA_SCRIPT,
    DEFAULT_SCENARIO_CONFIG,
    SCENARIO_CONFIGS,
    SENSOR_CONFIG,
    TEST_SCRIPTS,
    UI_APPLICATIONS,
    YOLO_PYTHON,
    check_prerequisites,
    load_yaml,
    scenario_ids,
)
from ui.launcher.processes import (  # noqa: E402
    ANSI_ESCAPE,
    ManagedProcess,
    ProcessSpec,
    carla_process_rows,
    port_open,
    process_alive,
)
from ui.launcher.theme import COLORS  # noqa: E402


__all__ = [
    "AEB_ROOT",
    "ANSI_ESCAPE",
    "AebLauncher",
    "BRAKE_MODES",
    "CARLA_PYTHON",
    "CARLA_ROOT",
    "CARLA_SCRIPT",
    "COLORS",
    "DEFAULT_SCENARIO_CONFIG",
    "ManagedProcess",
    "ProcessSpec",
    "SCENARIO_CONFIGS",
    "SENSOR_CONFIG",
    "ScrolledText",
    "TEST_SCRIPTS",
    "UI_APPLICATIONS",
    "YOLO_PYTHON",
    "carla_process_rows",
    "check_prerequisites",
    "command_text",
    "load_yaml",
    "main",
    "messagebox",
    "parse_args",
    "port_open",
    "process_alive",
    "scenario_ids",
    "tk",
    "ttk",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check launcher prerequisites without opening the window.",
    )
    parser.add_argument(
        "--page",
        default=None,
        help="Page to open first: carla, apps, tests, video (or 1-4).",
    )
    parser.add_argument(
        "--geometry",
        default=None,
        help="Initial window size/position in X11 form, e.g. 1280x800.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.check:
        return check_prerequisites()
    from ui.launcher.app import page_index

    try:
        initial_page = page_index(args.page)
    except ValueError as exc:
        raise SystemExit(str(exc))
    root = tk.Tk()
    AebLauncher(root, initial_page=initial_page)
    if args.geometry:
        root.geometry(args.geometry)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
