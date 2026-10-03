"""Headless smoke test of the AEB Test Bench v2 window (system Python + Xvfb).

Builds the real window without its event loop and without starting any run,
then checks the experiment contract: presets fill sections 1-3, the plan shown
in section 4 is exactly what ``build_plan`` produces, checkbox toggling, both
step views and both pages.
"""

import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


AEB_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PYTHON = "/usr/bin/python3"

SCRIPT = textwrap.dedent(
    """
    import tkinter as tk
    from ui.testbench.app import TestBenchApp, page_name
    from ui.testbench.plan import build_plan

    root = tk.Tk()
    root.withdraw()
    app = TestBenchApp(root)
    root.update_idletasks()
    exp = app.experiment
    assert root.title() == "AEB Test Bench v2"
    assert page_name("ket-qua") == "results" and page_name(None) == "experiment"

    exp.apply_preset("smoke")
    exp.refresh_plan()
    plan = exp.plan
    assert plan.ok, plan.errors
    assert len(plan.commands) == 1 and plan.commands[0].policy_key == "radar_only"
    assert plan.commands[0].run_id.startswith("tb_smoke_radar_only_"), plan.commands[0].run_id
    assert exp.selected_label.cget("text").startswith("Đã chọn: 5 kịch bản")
    rows = exp.plan_tree.get_children("")
    assert len(rows) == 1
    preview = exp.command_preview.get("1.0", "end-1c")
    assert plan.commands[0].text() in preview
    expected = build_plan(app.catalog, exp.selected, ["radar_only"], exp.current_options(),
                          exp.run_id_var.get(), app.logs_root)
    assert [c.argv for c in expected.commands] == [c.argv for c in plan.commands]

    # Unticking one scenario turns the plan into an explicit --scenario list.
    exp.toggle("C|configs/scenarios/suites/smoke_basic.yaml|clear_road_50")
    exp.refresh_plan()
    command = exp.plan.commands[0]
    assert not command.whole_suite and command.argv.count("--scenario") == 4, command.argv
    assert exp.preset_key is None
    assert exp.tree.item("S|configs/scenarios/suites/smoke_basic.yaml", "image")

    exp.apply_preset("core")
    exp.refresh_plan()
    assert len(exp.plan.commands) == 12, len(exp.plan.commands)
    assert exp.full_repeat_button.winfo_manager() == "grid"
    exp.apply_preset("holdout")
    exp.refresh_plan()
    assert [c.policy_key for c in exp.plan.commands] == ["radar_only", "hard_gate", "fallback"]

    exp.search_var.set("ccrs 30")
    exp.rebuild_tree()
    assert exp.tree.get_children(""), "search found nothing"
    exp.show_view("run")
    root.update_idletasks()
    assert exp.run_view.winfo_manager() == "grid" and exp.design_view.winfo_manager() == ""
    exp.show_view("design")
    app.show_page("results")
    root.update_idletasks()
    assert app.results.winfo_manager() == "grid" and exp.winfo_manager() == ""
    assert app.theme.scale >= 1.0
    root.destroy()
    print("GUI-OK")
    """
)


class TestBenchGuiTests(unittest.TestCase):
    def test_window_builds_headless(self):
        if not Path(SYSTEM_PYTHON).is_file():
            self.skipTest("system Python with Tkinter not available")
        command = [SYSTEM_PYTHON, "-c", SCRIPT]
        environment = os.environ.copy()
        # Empty workspace: no existing run directory can collide with run-ids.
        workspace = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, workspace)
        environment["AEB_WORKSPACE_ROOT"] = workspace
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
            timeout=90,
            check=False,
        )
        if "No module named 'tkinter'" in result.stderr:
            self.skipTest("system Python lacks Tkinter")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("GUI-OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
