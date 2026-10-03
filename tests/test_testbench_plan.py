"""AEB Test Bench v2: catalogue, policy mapping, plan/command building (Tk-free).

The argument lists built here are the experiment record of a test-bench run,
so the golden commands below must only change deliberately.
"""

import re
import shutil
import tempfile
import textwrap
import unittest
from datetime import datetime
from pathlib import Path

from ui.testbench.catalog import (
    EXPECT_BRAKE,
    EXPECT_COLLISION_OK,
    EXPECT_NO_BRAKE,
    Catalog,
    expectation_text,
    group_key,
    scenario_facts,
)
from ui.testbench.paths import AEB_ROOT, CARLA_PYTHON, FUSION_RUNNER, RADAR_RUNNER
from ui.testbench.plan import (
    CORE_SUITES,
    PRESETS,
    ExperimentOptions,
    build_argv,
    build_plan,
    command_text,
    default_run_id_template,
    estimate_seconds,
    expand_run_id,
    format_duration,
)
from ui.testbench.policies import (
    POLICIES,
    classify_run,
    policy_slug,
    run_label,
    sensor_config_for,
    short_run_label,
)


SMOKE = "configs/scenarios/suites/smoke_basic.yaml"
RADAR_REGRESSION = "configs/scenarios/suites/radar_only_regression.yaml"
HOLDOUT = "configs/scenarios/suites/fusion_fallback_holdout.yaml"
PY = str(CARLA_PYTHON)
LOGS = Path("/tmp/aeb-testbench-logs-does-not-exist")
NOW = datetime(2026, 10, 3, 15, 30)


def never_exists(_path):
    return False


CATALOG = Catalog.load()


def keys_of(suite_rel, ids=None):
    suite = CATALOG.suite(suite_rel)
    return [s.key for s in suite.scenarios if ids is None or s.id in ids]


class CatalogTests(unittest.TestCase):
    def test_loads_every_tracked_suite(self):
        rels = [suite.rel for suite in CATALOG.suites]
        self.assertIn(SMOKE, rels)
        self.assertIn(HOLDOUT, rels)
        self.assertIn("configs/scenarios/car_to_car/cut_in.yaml", rels)
        self.assertEqual(len(rels), len(set(rels)))
        self.assertEqual(rels[0], SMOKE, "smoke suite is listed first")

    def test_smoke_suite_contents_and_groups(self):
        suite = CATALOG.suite(SMOKE)
        self.assertEqual(
            suite.scenario_ids(),
            ["clear_road_50", "ccrs_30", "ccrm_50_20", "ccrb_40_to_0", "adjacent_stationary_30"],
        )
        groups = dict((s.id, s.group) for s in suite.scenarios)
        self.assertEqual(
            groups,
            {
                "clear_road_50": "clear",
                "ccrs_30": "ccrs",
                "ccrm_50_20": "ccrm",
                "ccrb_40_to_0": "ccrb",
                "adjacent_stationary_30": "adjacent",
            },
        )
        # Must-brake groups are listed before must-not-brake groups.
        self.assertEqual([key for key, _ in suite.groups()], ["ccrs", "ccrm", "ccrb", "clear", "adjacent"])
        self.assertEqual(suite.default_control_mode, "deterministic")

    def test_same_id_in_two_suites_is_two_scenarios(self):
        a = CATALOG.scenario((SMOKE, "clear_road_50"))
        b = CATALOG.scenario((RADAR_REGRESSION, "clear_road_50"))
        self.assertNotEqual(a.key, b.key)
        self.assertEqual(a.duration_s, 5.0)
        self.assertEqual(b.duration_s, 6.0)

    def test_group_key_rules(self):
        self.assertEqual(group_key({"type": "moving_lead", "expected_brake": False}), "non_closing")
        self.assertEqual(group_key({"type": "moving_lead", "expected_brake": True}), "ccrm")
        self.assertEqual(group_key({"type": "clear_road", "synthetic_radar_points": [{}]}), "ghost")
        self.assertEqual(group_key({"type": "physical_false_positive"}), "roadside")
        self.assertEqual(group_key({"type": "physical_hazard"}), "hazard")
        self.assertEqual(group_key({"type": "something_new"}), "something_new")

    def test_filter_text_expectation_and_selection(self):
        hits = CATALOG.filter("ccrs 30 smoke")
        self.assertEqual([s.id for s in hits[SMOKE]], ["ccrs_30"])
        brake = CATALOG.filter("", EXPECT_BRAKE)
        self.assertTrue(all(s.expected_brake for group in brake.values() for s in group))
        no_brake = CATALOG.filter("", EXPECT_NO_BRAKE)
        self.assertTrue(all(not s.expected_brake for group in no_brake.values() for s in group))
        total = sum(len(suite.scenarios) for suite in CATALOG.suites)
        counts = CATALOG.expectation_counts()
        self.assertEqual(counts[EXPECT_BRAKE] + counts[EXPECT_NO_BRAKE], total)
        self.assertEqual(counts[EXPECT_COLLISION_OK], len([
            1 for group in CATALOG.filter("", EXPECT_COLLISION_OK).values() for _ in group
        ]))
        only = CATALOG.filter("", only_keys={(SMOKE, "ccrs_30")})
        self.assertEqual(list(only), [SMOKE])
        self.assertEqual(CATALOG.filter("no-such-token-xyz"), {})

    def test_facts_are_plain_vietnamese_and_name_the_file(self):
        scenario = CATALOG.scenario((SMOKE, "ccrs_30"))
        facts = dict(scenario_facts(scenario))
        self.assertEqual(facts["Tốc độ xe thử (ego)"], "30 km/h")
        self.assertEqual(facts["Tốc độ xe mục tiêu"], "0 km/h (đứng yên)")
        self.assertEqual(facts["Khoảng cách ban đầu"], "28 m")
        self.assertEqual(facts["Kỳ vọng"], "Phải phanh · không được va chạm")
        self.assertEqual(facts["File · id"], SMOKE + " · ccrs_30")
        self.assertEqual(expectation_text(CATALOG.scenario((SMOKE, "clear_road_50"))), "Không được phanh · không được va chạm")

    def test_unknown_suite_falls_back_to_header_comment(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(root))
        folder = root / "configs" / "scenarios" / "suites"
        folder.mkdir(parents=True)
        (folder / "my_suite.yaml").write_text(
            textwrap.dedent(
                """\
                # Hand-written suite for a test.
                # Second line.
                scenarios:
                  - {id: a, type: stationary_lead, expected_brake: true, duration_s: 4, control_modes: [physics]}
                  - {id: b, type: clear_road, expected_brake: false, expected_collision: true, duration_s: 3}
                """
            ),
            encoding="utf-8",
        )
        catalog = Catalog.load(root=root)
        suite = catalog.suite("configs/scenarios/suites/my_suite.yaml")
        self.assertEqual(suite.title, "my_suite")
        self.assertEqual(suite.summary, "Hand-written suite for a test. Second line.")
        self.assertEqual(suite.default_control_mode, "deterministic")
        a, b = suite.scenarios
        self.assertFalse(a.supports_mode("deterministic"))
        self.assertTrue(b.supports_mode("deterministic"))
        self.assertTrue(b.matches_expectation(EXPECT_COLLISION_OK))


class PolicyTests(unittest.TestCase):
    def test_sensor_config_mapping_matches_campaign(self):
        expected = {
            ("radar_only", "cuda"): "configs/sensors.yaml",
            ("radar_only", "cpu"): "configs/sensors.yaml",
            ("hard_gate", "cuda"): "configs/sensors_fusion_hard_batch_gpu.yaml",
            ("hard_gate", "cpu"): "configs/sensors_fusion_hard_batch_cpu.yaml",
            ("fallback", "cuda"): "configs/sensors_fusion_safe_fallback_batch_gpu.yaml",
            ("fallback", "cpu"): "configs/sensors_fusion_safe_fallback_batch_cpu.yaml",
        }
        for (key, device), path in expected.items():
            self.assertEqual(sensor_config_for(key, device), path)
            self.assertTrue((AEB_ROOT / path).is_file(), path)
        self.assertEqual(POLICIES["radar_only"].runner, RADAR_RUNNER)
        self.assertEqual(POLICIES["hard_gate"].runner, FUSION_RUNNER)
        self.assertEqual(POLICIES["fallback"].runner, FUSION_RUNNER)

    def test_slugs(self):
        self.assertEqual(policy_slug("radar_only", "cuda"), "radar_only")
        self.assertEqual(policy_slug("radar_only", "cpu"), "radar_only")
        self.assertEqual(policy_slug("hard_gate", "cuda"), "hard_gate_cuda")
        self.assertEqual(policy_slug("fallback", "cpu"), "fallback_cpu")

    def test_classify_past_runs(self):
        self.assertEqual(
            classify_run("scripts/run_radar_aeb_scenarios.py --scenario-config x", "configs/sensors.yaml"),
            ("radar_only", None),
        )
        self.assertEqual(
            classify_run(
                "scripts/run_fusion_aeb_scenarios.py",
                "configs/sensors_fusion_safe_fallback_batch_gpu.yaml",
            ),
            ("fallback", "cuda"),
        )
        self.assertEqual(
            classify_run("scripts/run_fusion_aeb_scenarios.py", "configs/sensors_fusion_hard_batch_cpu.yaml"),
            ("hard_gate", "cpu"),
        )
        self.assertEqual(
            classify_run("", "configs/sensors_fusion_hold_0p35.yaml", ["CUDAExecutionProvider", "CPUExecutionProvider"]),
            ("hard_gate", "cuda"),
        )
        self.assertEqual(classify_run("", "configs/sensors.yaml"), (None, None))
        self.assertEqual(run_label("hard_gate", "cuda", "configs/sensors_fusion_hold_0p35.yaml"), "Camera hard gate (hold 0p35) · CUDA")
        self.assertEqual(run_label(None, None), "Không rõ")
        self.assertEqual(short_run_label("fallback", "cuda"), "Fallback · CUDA")
        self.assertEqual(short_run_label("radar_only", None), "Radar-only")


class RunIdTests(unittest.TestCase):
    def test_default_template(self):
        self.assertEqual(default_run_id_template("smoke", NOW), "tb_smoke_{policy}_20261003_1530")
        self.assertEqual(default_run_id_template(None, NOW, multi_suite=True), "tb_custom_{policy}_{suite}_20261003_1530")
        self.assertEqual(default_run_id_template("Hồi quy core!", NOW), "tb_h_i_quy_core_{policy}_20261003_1530")

    def test_expand(self):
        self.assertEqual(expand_run_id("tb_x_{policy}_t", "fallback_cuda", "s", False, False), "tb_x_fallback_cuda_t")
        self.assertEqual(expand_run_id("mine", "radar_only", "smoke_basic", True, True), "mine_radar_only_smoke_basic")
        self.assertEqual(expand_run_id("mine", "radar_only", "smoke_basic", False, False), "mine")
        self.assertEqual(expand_run_id("a_{suite}_{policy}", "p", "s", False, False), "a_s_p")


class CommandTests(unittest.TestCase):
    def test_golden_whole_suite_radar(self):
        plan = build_plan(
            CATALOG,
            keys_of(SMOKE),
            ["radar_only"],
            ExperimentOptions(),
            "tb_smoke_{policy}_20261003_1530",
            LOGS,
            path_exists=never_exists,
        )
        self.assertTrue(plan.ok, plan.errors)
        self.assertEqual(len(plan.commands), 1)
        command = plan.commands[0]
        self.assertEqual(
            command.argv,
            [
                PY,
                "scripts/run_radar_aeb_scenarios.py",
                "--sensor-config",
                "configs/sensors.yaml",
                "--scenario-config",
                SMOKE,
                "--control-mode",
                "physics",
                "--repeat",
                "1",
                "--seed",
                "2026",
                "--scenario-cooldown-s",
                "1",
                "--reload-world-every",
                "1",
                "--run-id",
                "tb_smoke_radar_only_20261003_1530",
                "--load-map",
            ],
        )
        self.assertTrue(command.whole_suite)
        self.assertEqual(command.scenario_runs, 5)
        self.assertEqual(command.log_dir, LOGS / "tb_smoke_radar_only_20261003_1530")

    def test_partial_selection_is_one_command_with_repeated_scenario_flags(self):
        ids = {"adjacent_stationary_30", "ccrs_30"}
        options = ExperimentOptions(repeat=3, device="cuda", record_evidence=True, resume=True, load_map=False)
        plan = build_plan(CATALOG, keys_of(SMOKE, ids), ["fallback"], options, "tb_custom_{policy}_x", LOGS, path_exists=never_exists)
        self.assertTrue(plan.ok, plan.errors)
        (command,) = plan.commands
        self.assertFalse(command.whole_suite)
        self.assertEqual(command.argv[1], "scripts/run_fusion_aeb_scenarios.py")
        self.assertEqual(command.argv[3], "configs/sensors_fusion_safe_fallback_batch_gpu.yaml")
        tail = command.argv[command.argv.index("--run-id"):]
        # YAML order, not click order; one run directory for the subset.
        self.assertEqual(
            tail,
            [
                "--run-id",
                "tb_custom_fallback_cuda_x",
                "--record-evidence",
                "--resume",
                "--scenario",
                "ccrs_30",
                "--scenario",
                "adjacent_stationary_30",
            ],
        )
        self.assertNotIn("--load-map", command.argv)
        self.assertEqual(command.scenario_runs, 6)

    def test_policies_times_suites_suite_major_with_unique_run_ids(self):
        keys = keys_of(SMOKE) + keys_of(HOLDOUT, {"holdout_ghost_6pt_center"})
        template = default_run_id_template("custom", NOW, multi_suite=True)
        plan = build_plan(CATALOG, keys, list(POLICIES), ExperimentOptions(), template, LOGS, path_exists=never_exists)
        self.assertTrue(plan.ok, plan.errors)
        order = [(c.suite_rel, c.policy_key) for c in plan.commands]
        self.assertEqual(
            order,
            [
                (SMOKE, "radar_only"),
                (SMOKE, "hard_gate"),
                (SMOKE, "fallback"),
                (HOLDOUT, "radar_only"),
                (HOLDOUT, "hard_gate"),
                (HOLDOUT, "fallback"),
            ],
        )
        run_ids = [c.run_id for c in plan.commands]
        self.assertEqual(len(set(run_ids)), 6)
        self.assertEqual(run_ids[1], "tb_custom_hard_gate_cuda_smoke_basic_20261003_1530")
        self.assertEqual(plan.total_runs, 3 * 5 + 3 * 1)
        self.assertTrue(any("Hold-out" in warning for warning in plan.warnings))

    def test_control_mode_filter_matches_runner(self):
        # radar_only_regression has physics-only scenarios (control_modes: [physics]).
        options = ExperimentOptions(control_mode="deterministic")
        plan = build_plan(CATALOG, keys_of(RADAR_REGRESSION), ["radar_only"], options, "r_{policy}", LOGS, path_exists=never_exists)
        (command,) = plan.commands
        self.assertTrue(command.skipped)
        self.assertEqual(len(command.runnable) + len(command.skipped), len(keys_of(RADAR_REGRESSION)))
        self.assertTrue(any("bỏ qua" in warning for warning in plan.warnings))
        only_physics = keys_of(RADAR_REGRESSION, {"cut_in_65_45"})
        plan = build_plan(CATALOG, only_physics, ["radar_only"], options, "r_{policy}", LOGS, path_exists=never_exists)
        self.assertEqual(plan.commands, [])
        self.assertFalse(plan.ok)

    def test_yaml_mode_resolves_per_suite(self):
        options = ExperimentOptions(control_mode="yaml")
        keys = keys_of(SMOKE) + keys_of(HOLDOUT)
        plan = build_plan(CATALOG, keys, ["radar_only"], options, "y_{policy}_{suite}", LOGS, path_exists=never_exists)
        modes = dict((c.suite_rel, c.control_mode) for c in plan.commands)
        self.assertEqual(modes, {SMOKE: "deterministic", HOLDOUT: "physics"})
        for command in plan.commands:
            self.assertEqual(command.argv[command.argv.index("--control-mode") + 1], command.control_mode)

    def test_blocking_errors(self):
        options = ExperimentOptions()
        plan = build_plan(CATALOG, [], [], options, "x", LOGS, path_exists=never_exists)
        self.assertEqual(len(plan.errors), 2)
        plan = build_plan(CATALOG, keys_of(SMOKE), ["radar_only"], options, "bad id/..", LOGS, path_exists=never_exists)
        self.assertFalse(plan.ok)
        plan = build_plan(CATALOG, keys_of(SMOKE), ["radar_only"], options, "exists", LOGS, path_exists=lambda _p: True)
        self.assertFalse(plan.ok)
        self.assertTrue(plan.commands[0].log_dir_exists)
        resumed = ExperimentOptions(resume=True)
        plan = build_plan(CATALOG, keys_of(SMOKE), ["radar_only"], resumed, "exists", LOGS, path_exists=lambda _p: True)
        self.assertTrue(plan.ok, plan.errors)
        bad = ExperimentOptions(repeat=0, cooldown_s=-1, reload_every=-2)
        self.assertEqual(len(bad.validate()), 3)

    def test_cpu_and_host_port(self):
        options = ExperimentOptions(device="cpu", port=2010, host="10.0.0.2")
        plan = build_plan(CATALOG, keys_of(SMOKE, {"ccrs_30"}), ["hard_gate"], options, "c_{policy}", LOGS, path_exists=never_exists)
        (command,) = plan.commands
        self.assertEqual(command.run_id, "c_hard_gate_cpu")
        self.assertIn("configs/sensors_fusion_hard_batch_cpu.yaml", command.argv)
        self.assertEqual(command.argv[command.argv.index("--host") + 1], "10.0.0.2")
        self.assertEqual(command.argv[command.argv.index("--port") + 1], "2010")
        self.assertTrue(any("CPU" in warning for warning in plan.warnings))

    def test_estimate_and_text(self):
        scenarios = CATALOG.suite(SMOKE).scenarios
        one = estimate_seconds(RADAR_RUNNER, scenarios, ExperimentOptions(repeat=1))
        five = estimate_seconds(RADAR_RUNNER, scenarios, ExperimentOptions(repeat=5))
        fusion = estimate_seconds(FUSION_RUNNER, scenarios, ExperimentOptions(repeat=1))
        self.assertGreater(one, sum(s.duration_s for s in scenarios))
        self.assertGreater(five, 4 * one)
        self.assertGreater(fusion, one)
        self.assertEqual(estimate_seconds(RADAR_RUNNER, [], ExperimentOptions()), 0.0)
        self.assertEqual(format_duration(30), "< 1 phút")
        self.assertEqual(format_duration(125), "≈ 2 phút")
        self.assertEqual(format_duration(3600 + 25 * 60), "≈ 1 giờ 25 phút")
        argv = build_argv(RADAR_RUNNER, "configs/sensors.yaml", SMOKE, "physics", ExperimentOptions(), "a b")
        self.assertTrue(command_text(argv).endswith("--run-id 'a b' --load-map"))
        self.assertTrue(command_text(argv, cwd="/x y").startswith("cd '/x y' && "))

    def test_presets_reference_real_suites(self):
        self.assertEqual(set(PRESETS), {"smoke", "core", "holdout"})
        for preset in PRESETS.values():
            for rel in preset.suites:
                self.assertIn(rel, [suite.rel for suite in CATALOG.suites])
            for key in preset.policies:
                self.assertIn(key, POLICIES)
            self.assertLessEqual(preset.repeat, preset.full_repeat)
        self.assertEqual(PRESETS["smoke"].suites, (SMOKE,))
        self.assertEqual(PRESETS["smoke"].policies, ("radar_only",))
        self.assertEqual(len(CORE_SUITES), 4)
        self.assertEqual(PRESETS["core"].full_repeat, 5)
        self.assertEqual(PRESETS["holdout"].suites, (HOLDOUT,))
        self.assertTrue(re.match(r"^tb_holdout_\{policy\}_\d{8}_\d{4}$", default_run_id_template("holdout", NOW)))


if __name__ == "__main__":
    unittest.main()
