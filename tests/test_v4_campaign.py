"""Tests for the resumable paper-v4 campaign orchestration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.run_v4_campaign import (
    FULL_SUITES,
    build_full_jobs,
    build_smoke_jobs,
    job_command,
    scenario_count,
    scenario_ids,
)
from scripts.run_v4_final_pipeline import (
    generate_variant_configs,
    validate_cuda_runtime,
)


class V4CampaignTests(unittest.TestCase):
    def test_smoke_campaign_has_expected_holdout_sizes(self):
        jobs = build_smoke_jobs(repeat=1)

        self.assertEqual(4, len(jobs))
        self.assertEqual([2, 8, 6, 6], [scenario_count(job) for job in jobs])
        self.assertTrue(all(job.require_all_pass for job in jobs))

    def test_full_campaign_builds_three_way_paired_jobs(self):
        jobs = build_full_jobs(repeat=5)

        self.assertEqual(3 * len(FULL_SUITES), len(jobs))
        for prefix in ("radar_only", "hard_gate", "safe_fallback"):
            self.assertEqual(
                len(FULL_SUITES),
                sum(1 for job in jobs if job.name.startswith(prefix + "_")),
            )
        self.assertTrue(all(job.repeat == 5 for job in jobs))

    def test_scenario_ids_preserve_suite_order(self):
        job = build_smoke_jobs(repeat=1)[-1]

        self.assertEqual(list(job.scenarios), scenario_ids(job))

    def test_variant_generation_applies_nested_overrides(self):
        import yaml

        with tempfile.TemporaryDirectory() as directory:
            generated = generate_variant_configs(Path(directory))
            camera_off = generated["camera_degradation"][
                "safe_fallback_camera_off"
            ]
            no_points = generated["ablation"]["no_minimum_point_constraint"]
            with open(str(camera_off)) as stream:
                camera_off_config = yaml.safe_load(stream)
            with open(str(no_points)) as stream:
                no_points_config = yaml.safe_load(stream)

        self.assertFalse(camera_off_config["model"]["enabled"])
        self.assertIsNone(camera_off_config["model"]["require_provider"])
        self.assertEqual(
            2,
            no_points_config["fusion"]["radar_emergency_fallback"][
                "min_cluster_points"
            ],
        )

    def test_final_pipeline_rejects_cpu_fallback_for_fusion(self):
        job = build_smoke_jobs(repeat=1)[0]

        with self.assertRaises(RuntimeError):
            validate_cuda_runtime(
                job,
                {
                    "model_runtime": {
                        "active_providers": ["CPUExecutionProvider"],
                        "inference_error_count": 0,
                    }
                },
            )

    def test_job_command_is_resumable_and_repeats_scenario_flags(self):
        job = build_smoke_jobs(repeat=1)[-1]
        args = SimpleNamespace(
            python=Path("/tmp/python"),
            host="127.0.0.1",
            port=2000,
            timeout=10.0,
            log_root=Path("/tmp/logs"),
            seed=2026,
            scenario_cooldown_s=0.5,
            reload_world_every=0,
            reload_world_wait_s=2.0,
        )

        command = job_command(args, job, "test_run")

        self.assertIn("--resume", command)
        self.assertIn("--seed", command)
        self.assertEqual(len(job.scenarios), command.count("--scenario"))


if __name__ == "__main__":
    unittest.main()
