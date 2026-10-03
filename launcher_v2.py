#!/usr/bin/env python3
"""AEB Test Bench v2: experiment-oriented launcher (independent of launcher.py).

Usage::

    /usr/bin/python3 launcher_v2.py              # open the window
    /usr/bin/python3 launcher_v2.py --check      # prerequisites, no window
    /usr/bin/python3 launcher_v2.py --preset smoke --autostart

The window only builds commands for ``scripts/run_radar_aeb_scenarios.py`` /
``scripts/run_fusion_aeb_scenarios.py`` and reads scenario YAML and run logs.
"""

import argparse
import os
import sys
from pathlib import Path


AEB_ROOT = Path(__file__).resolve().parent
if str(AEB_ROOT) not in sys.path:
    sys.path.insert(0, str(AEB_ROOT))


def _ensure_tkinter():
    """Re-exec under the system Python when this interpreter lacks Tk."""
    try:
        import tkinter  # noqa: F401
        from tkinter import ttk  # noqa: F401

        return
    except ImportError as exc:
        if getattr(exc, "name", "tkinter") not in ("tkinter", "_tkinter"):
            raise
        gui_python = Path(os.environ.get("AEB_TESTBENCH_PYTHON", "/usr/bin/python3"))
        if gui_python.is_file() and os.environ.get("AEB_TESTBENCH_REEXEC") != "1":
            environment = os.environ.copy()
            environment["AEB_TESTBENCH_REEXEC"] = "1"
            os.execve(
                str(gui_python),
                [str(gui_python), str(Path(__file__).resolve())] + sys.argv[1:],
                environment,
            )
        raise SystemExit(
            "Tkinter không có trong {}. Hãy chạy /usr/bin/python3 launcher_v2.py "
            "hoặc đặt AEB_TESTBENCH_PYTHON.".format(sys.executable)
        )


def parse_args(argv=None):
    from ui.testbench.plan import DEFAULT_PORT, PRESETS

    parser = argparse.ArgumentParser(description="AEB Test Bench v2")
    parser.add_argument("--check", action="store_true", help="Kiểm tra điều kiện chạy, không mở cửa sổ.")
    parser.add_argument("--page", default="experiment", help="Trang mở đầu: experiment | results.")
    parser.add_argument(
        "--step", choices=("design", "run"), default=None, help="Mở bước 1–3 (design) hoặc 4–5 (run)."
    )
    parser.add_argument("--geometry", default=None, help="Kích thước cửa sổ X11, ví dụ 1280x800.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Cổng CARLA (mặc định 2000).")
    debug = parser.add_argument_group("tự động hóa / debug")
    debug.add_argument("--preset", choices=tuple(PRESETS), help="Áp dụng một mẫu thí nghiệm.")
    debug.add_argument(
        "--scenario",
        action="append",
        metavar="SUITE[:ID]",
        help="Chọn kịch bản (file suite, tùy chọn :id); lặp lại được. Ghi đè lựa chọn của mẫu.",
    )
    debug.add_argument("--policy", action="append", choices=("radar_only", "hard_gate", "fallback"))
    debug.add_argument("--device", choices=("cuda", "cpu"))
    debug.add_argument("--control-mode", choices=("yaml", "physics", "deterministic"))
    debug.add_argument("--repeat", type=int)
    debug.add_argument("--run-id", help="Mẫu run-id (có thể chứa {policy}/{suite}).")
    debug.add_argument("--autostart", action="store_true", help="Tự bấm 'Chạy kế hoạch' khi mở.")
    debug.add_argument("--exit-when-done", action="store_true", help="Đóng cửa sổ khi hàng đợi xong.")
    debug.add_argument("--linger-s", type=float, default=0.0, help="Giữ cửa sổ N giây trước khi đóng.")
    debug.add_argument("--show-results-when-done", action="store_true", help="Chuyển sang Kết quả khi xong.")
    debug.add_argument("--select-run", action="append", help="Chọn sẵn run-id ở màn Kết quả (tối đa 2).")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.check:
        from ui.testbench.checks import check_prerequisites

        return check_prerequisites()
    _ensure_tkinter()
    from ui.testbench.app import main as app_main, page_name

    try:
        args.page = page_name(args.page)
    except ValueError as exc:
        raise SystemExit(str(exc))
    return app_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
