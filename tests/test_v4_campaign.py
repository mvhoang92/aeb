"""Tests for the resumable paper-v4 campaign orchestration."""

from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.run_v4_campaign import (
    FULL_SUITES,
    build_full_jobs,
    build_smoke_jobs,
    job_command,
    scenario_count,
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
