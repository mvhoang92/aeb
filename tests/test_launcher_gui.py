"""Headless smoke test of the launcher window (system Python + Xvfb).

Builds the real window without starting its event loop, so nothing is polled
or launched, and checks the layout contract: four pages, a status pill, a
command preview per page that matches the pure command builders.
"""

import os
import shutil
import subprocess
import textwrap
import unittest
from pathlib import Path


AEB_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PYTHON = "/usr/bin/python3"

SCRIPT = textwrap.dedent(
    """
    import launcher
    from ui.launcher.app import PAGES, page_index
    from ui.launcher.commands import command_text

    root = launcher.tk.Tk()
    root.withdraw()
    app = launcher.AebLauncher(root, initial_page=page_index("video"))
    root.update_idletasks()
    assert app.page_var.get() == 3, app.page_var.get()
    assert [page_index(name) for name in ("carla", "apps", "tests", "video", "2", "server")] == [0, 1, 2, 3, 1, 0]
    try:
        page_index("nope")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown page accepted")
    for index in range(len(PAGES)):
        app._show_page(index)
        root.update_idletasks()
        visible = [page.winfo_manager() == "grid" for page in app.pages]
        assert visible.count(True) == 1 and visible[index], visible
    pairs = (
        (app.server_command, app._server_preview_command()),
        (app.ui_command_preview, app._ui_command()),
        (app.test_command_preview, app._test_command()),
        (app.video_command_preview, app._video_command()),
    )
    for widget, command in pairs:
        assert widget.get("1.0", "end-1c") == command_text(command)
    app.status_pill.set("OFFLINE  127.0.0.1:2000", "offline")
    assert int(app.status_pill.cget("width")) > 0
    app.process_label.set_text("Không có")
    min_width, min_height = root.minsize()
    assert min_width > 0 and min_height > 0
    root.destroy()
    print("GUI-OK")
    """
)


class LauncherGuiTests(unittest.TestCase):
    def test_window_builds_headless(self):
        if not Path(SYSTEM_PYTHON).is_file():
            self.skipTest("system Python with Tkinter not available")
        command = [SYSTEM_PYTHON, "-c", SCRIPT]
        environment = os.environ.copy()
        xvfb_run = shutil.which("xvfb-run")
        if xvfb_run:
            command = [xvfb_run, "-a", "-s", "-screen 0 1280x800x24 -dpi 96"] + command
            environment.pop("DISPLAY", None)
        elif not environment.get("DISPLAY"):
            self.skipTest("no X display or xvfb-run")
        result = subprocess.run(
            command,
            cwd=str(AEB_ROOT),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("GUI-OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
