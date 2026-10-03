"""AEB Test Bench v2: run-log parsing, paired comparison and queue (Tk-free)."""

import csv
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from ui.testbench.execution import (
    OUTCOME_ALGO_FAIL,
    OUTCOME_ALL_PASS,
    OUTCOME_HARD_STOP,
    OUTCOME_SKIPPED,
    OUTCOME_STOPPED,
    OUTCOME_TECH_ERROR,
    CommandQueue,
    OutputState,
    classify_exit,
    listening_ports,
)
from ui.testbench.results import (
    OUTCOME_FAIL,
    OUTCOME_MIXED,
    OUTCOME_PASS,
    condition_outcomes,
    list_runs,
    load_summaries,
    paired_comparison,
    planned_runs,
    totals,
)
from ui.testbench.catalog import Catalog


def row(scenario_id, status="PASS", run_index=1, expected_brake=True, brake=True, collision=False, gap=3.0):
    return {
        "scenario_id": scenario_id,
        "run_index": run_index,
        "status": status,
        "expected_brake": expected_brake,
        "brake_activated": brake,
        "expected_collision": False,
        "collision": collision,
        "minimum_bumper_gap_m": gap,
        "first_brake_s": 1.5 if brake else None,
        "failure_reason": "" if status == "PASS" else "brake mismatch",
    }


class RunDirectoryTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.root))

    def make_run(self, name, rows, metadata=None, as_csv=False):
        path = self.root / name
        path.mkdir()
        if metadata is not None:
            (path / "run_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        if as_csv:
            with open(str(path / "summary.csv"), "w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                for item in rows:
                    writer.writerow(item)
        else:
            (path / "summary.json").write_text(json.dumps(rows), encoding="utf-8")
        return path

    def test_list_runs_newest_first_with_policy(self):
        self.make_run(
            "old",
            [row("a")],
            {
                "created_at": "2026-10-01T10:00:00.1",
                "command": "scripts/run_radar_aeb_scenarios.py --scenario-config configs/scenarios/suites/smoke_basic.yaml",
                "sensor_config": "configs/sensors.yaml",
                "scenario_config": "configs/scenarios/suites/smoke_basic.yaml",
                "control_mode": "physics",
                "repeat": 1,
                "seed": 2026,
                "passed": 1,
                "failed": 0,
                "completed_scenario_runs": 1,
            },
        )
        self.make_run(
            "new",
            [row("a")],
            {
                "created_at": "2026-10-03T10:00:00",
                "command": "scripts/run_fusion_aeb_scenarios.py",
                "sensor_config": "configs/sensors_fusion_safe_fallback_batch_gpu.yaml",
                "scenario_config": "configs/scenarios/suites/smoke_basic.yaml",
                "passed": 0,
                "failed": 1,
                "completed_scenario_runs": 1,
            },
        )
        (self.root / "not_a_run").mkdir()
        (self.root / "stray.txt").write_text("x")
        runs = list_runs(self.root)
        self.assertEqual([run.run_id for run in runs], ["new", "old"])
        new, old = runs
        self.assertEqual(new.policy_label, "Gate + radar emergency fallback · CUDA")
        self.assertEqual(new.short_label, "Fallback · CUDA")
        self.assertEqual(new.pass_text, "0/1")
        self.assertEqual(old.policy_label, "Radar-only")
        self.assertEqual(old.suite_stem, "smoke_basic")
        self.assertEqual(old.date_text, "2026-10-01 10:00")
        self.assertEqual(list_runs(self.root / "missing"), [])

    def test_planned_runs_detects_incomplete_runs(self):
        catalog = Catalog.load()
        meta = {
            "command": "scripts/run_radar_aeb_scenarios.py --scenario-config "
            "configs/scenarios/suites/smoke_basic.yaml --repeat 2 --run-id x",
            "scenario_config": "configs/scenarios/suites/smoke_basic.yaml",
            "control_mode": "physics",
            "repeat": 2,
            "completed_scenario_runs": 3,
            "passed": 3,
            "failed": 0,
        }
        self.make_run("whole", [row("a")], meta)
        partial = dict(meta, command=meta["command"] + " --scenario ccrs_30 --scenario ccrm_50_20")
        self.make_run("partial", [row("a")], partial)
        runs = dict((run.run_id, run) for run in list_runs(self.root))
        self.assertEqual(planned_runs(runs["whole"], catalog), 10)
        self.assertEqual(planned_runs(runs["partial"], catalog), 4)
        physics_only = dict(
            meta,
            command="scripts/run_radar_aeb_scenarios.py --scenario-config "
            "configs/scenarios/suites/radar_only_regression.yaml --scenario cut_in_65_45",
            scenario_config="configs/scenarios/suites/radar_only_regression.yaml",
            control_mode="deterministic",
            repeat=1,
        )
        self.make_run("skipped", [row("a")], physics_only)
        self.make_run("legacy", [row("a")], {"completed_scenario_runs": 1})
        runs = dict((run.run_id, run) for run in list_runs(self.root))
        self.assertEqual(planned_runs(runs["skipped"], catalog), 0)
        self.assertIsNone(planned_runs(runs["legacy"], catalog))

    def test_csv_fallback_and_totals(self):
        rows = [
            row("hit"),
            row("miss", status="FAIL", brake=False, collision=True),
            row("false_alarm", status="FAIL", expected_brake=False, brake=True),
            row("quiet", expected_brake=False, brake=False, gap=None),
        ]
        path = self.make_run("csv_run", rows, as_csv=True)
        loaded = load_summaries(path)
        self.assertEqual([item["scenario_id"] for item in loaded], ["hit", "miss", "false_alarm", "quiet"])
        self.assertIs(loaded[1]["collision"], True)
        self.assertIsNone(loaded[3]["minimum_bumper_gap_m"])
        stats = totals(loaded)
        self.assertEqual(
            (stats["passed"], stats["total"], stats["tp"], stats["fn"], stats["fp"], stats["tn"], stats["collisions"]),
            (2, 4, 1, 1, 1, 1, 1),
        )
        self.assertAlmostEqual(stats["precision"], 0.5)
        self.assertAlmostEqual(stats["recall"], 0.5)
        empty = totals([])
        self.assertIsNone(empty["precision"])

    def test_condition_outcomes_and_paired_table(self):
        a = [
            row("both_ok"),
            row("a_only"),
            row("b_only", status="FAIL"),
            row("both_bad", status="FAIL"),
            row("flaky", run_index=1),
            row("flaky", status="FAIL", run_index=2),
            row("only_a"),
        ]
        b = [
            row("both_ok"),
            row("a_only", status="FAIL"),
            row("b_only"),
            row("both_bad", status="FAIL"),
            row("flaky"),
            row("only_b"),
        ]
        outcomes = condition_outcomes(a)
        self.assertEqual(outcomes["flaky"], OUTCOME_MIXED)
        self.assertEqual(outcomes["both_bad"], OUTCOME_FAIL)
        self.assertEqual(outcomes["both_ok"], OUTCOME_PASS)
        comparison = paired_comparison(a, b)
        table = comparison["table"]
        self.assertEqual(table["both_pass"], ["both_ok"])
        self.assertEqual(table["a_only_pass"], ["a_only"])
        self.assertEqual(table["b_only_pass"], ["b_only"])
        self.assertEqual(table["both_fail"], ["both_bad"])
        self.assertEqual(table["mixed"], ["flaky"])
        self.assertEqual(comparison["only_in_a"], ["only_a"])
        self.assertEqual(comparison["only_in_b"], ["only_b"])
        self.assertEqual(len(comparison["common"]), 5)


RUNNER_OUTPUT = """\
Resume: bỏ qua 1/3 scenario-runs đã hoàn thành
[1/2] ccrs_30 run 2/3: Xe mục tiêu đứng yên
  PASS | brake=True collision=False min_gap=7.75m log=ccrs_30.csv
[2/2] ccrm_50_20 run 1/3: Ego 50 km/h
  FAIL | brake=False collision=True min_gap=0.00m log=ccrm_50_20.csv

Log directory: /tmp/logs/tb_x
"""


class OutputParsingTests(unittest.TestCase):
    def test_progress_and_results(self):
        state = OutputState(3)
        for line in RUNNER_OUTPUT.splitlines():
            state.feed(line + "\n")
        self.assertEqual(state.resumed, 1)
        self.assertEqual((state.passed, state.failed, state.done), (1, 1, 2))
        self.assertEqual(state.current_scenario, "ccrm_50_20")
        self.assertEqual((state.current_run, state.repeat, state.jobs_total), (1, 3, 2))
        self.assertEqual(state.log_directory, "/tmp/logs/tb_x")
        self.assertFalse(state.saw_traceback)
        self.assertEqual(classify_exit(1, state), OUTCOME_ALGO_FAIL)
        self.assertEqual(classify_exit(1, state, stopped=True), OUTCOME_STOPPED)

    def test_technical_problems_are_never_algorithm_fail(self):
        state = OutputState()
        state.feed("\x1b[31mTECHNICAL HARD-STOP: CUDAExecutionProvider unavailable\x1b[0m\n")
        self.assertTrue(state.saw_hard_stop)
        self.assertEqual(classify_exit(3, state), OUTCOME_HARD_STOP)
        crash = OutputState()
        crash.feed("  FAIL | brake=False\n")
        crash.feed("Traceback (most recent call last):\n")
        crash.feed('  File "x.py", line 1, in <module>\n')
        crash.feed("RuntimeError: time-out of 10000ms while waiting for the simulator\n")
        self.assertEqual(classify_exit(1, crash), OUTCOME_TECH_ERROR)
        self.assertIn("time-out", crash.last_error)
        self.assertEqual(classify_exit(0, OutputState()), OUTCOME_ALL_PASS)
        self.assertEqual(classify_exit(2, OutputState()), OUTCOME_TECH_ERROR)
        self.assertEqual(classify_exit(-9, OutputState()), OUTCOME_TECH_ERROR)


class ListeningPortTests(unittest.TestCase):
    def test_reads_listen_entries_only(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        table = os.path.join(folder, "tcp")
        with open(table, "w") as stream:
            stream.write(
                "  sl  local_address rem_address   st tx_queue rx_queue\n"
                "   0: 00000000:07D0 00000000:0000 0A 00000000:00000000\n"
                "   1: 0100007F:07D1 0100007F:9C40 01 00000000:00000000\n"
            )
        self.assertEqual(listening_ports((table,)), {2000})
        self.assertIsNone(listening_ports((os.path.join(folder, "missing"),)))


class FakeCommand(object):
    def __init__(self, code):
        self.argv = [sys.executable, "-c", code]
        self.scenario_runs = 1


class CommandQueueTests(unittest.TestCase):
    def run_queue(self, commands, stop_on_technical=True, timeout=30.0):
        events = []
        done = threading.Event()

        def emit(event, payload):
            events.append((event, payload))
            if event == "finished":
                done.set()

        command_queue = CommandQueue(commands, emit, stop_on_technical=stop_on_technical, cwd=tempfile.gettempdir())
        command_queue.start()
        self.assertTrue(done.wait(timeout))
        return command_queue, events

    def test_sequential_outcomes_and_stop_on_technical(self):
        ok = FakeCommand("print('[1/1] a run 1/1: x'); print('  PASS | brake=True')")
        fail = FakeCommand("import sys; print('  FAIL | brake=False'); sys.exit(1)")
        hard = FakeCommand("import sys; print('TECHNICAL HARD-STOP: no CUDA'); sys.exit(3)")
        never = FakeCommand("print('should not run')")
        command_queue, events = self.run_queue([ok, fail, hard, never])
        self.assertEqual(
            command_queue.outcomes,
            [OUTCOME_ALL_PASS, OUTCOME_ALGO_FAIL, OUTCOME_HARD_STOP, OUTCOME_SKIPPED],
        )
        lines = [payload[1] for event, payload in events if event == "line"]
        self.assertIn("  PASS | brake=True", lines)
        self.assertNotIn("should not run", lines)
        ends = [payload[:3] for event, payload in events if event == "end"]
        self.assertEqual([code for _, _, code in ends], [0, 1, 3])

    def test_runner_environment_is_unbuffered(self):
        probe = FakeCommand("import os; print('  PASS | ' + os.environ.get('PYTHONUNBUFFERED', '-'))")
        command_queue, events = self.run_queue([probe])
        lines = [payload[1] for event, payload in events if event == "line"]
        self.assertEqual(lines, ["  PASS | 1"])

    @unittest.skipUnless(hasattr(os, "killpg"), "POSIX process groups required")
    def test_stop_current_interrupts_and_is_reported_as_stopped(self):
        slow = FakeCommand(
            "import time, sys\n"
            "print('[1/1] a run 1/1: x', flush=True)\n"
            "try:\n    time.sleep(30)\nexcept KeyboardInterrupt:\n    print('cleanup', flush=True); sys.exit(130)\n"
        )
        follow = FakeCommand("print('next')")
        events = []
        done = threading.Event()

        def emit(event, payload):
            events.append((event, payload))
            if event == "line" and "a run" in payload[1]:
                command_queue.stop_queue()
            if event == "finished":
                done.set()

        command_queue = CommandQueue([slow, follow], emit, cwd=tempfile.gettempdir())
        started = time.time()
        command_queue.start()
        self.assertTrue(done.wait(20))
        self.assertLess(time.time() - started, 15)
        self.assertEqual(command_queue.outcomes, [OUTCOME_STOPPED, OUTCOME_SKIPPED])
        self.assertIn("cleanup", [payload[1] for event, payload in events if event == "line"])


if __name__ == "__main__":
    unittest.main()
