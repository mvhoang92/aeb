"""Golden schema and compatibility tests for extracted evaluation helpers."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from evaluation.artifact_io import write_csv
from evaluation.metrics import summarize_scenario
from evaluation.schemas import SUMMARY_FIELDS, TICK_FIELDS
from scripts import run_radar_aeb_scenarios as historical_runner


class EvaluationModuleTests(unittest.TestCase):
    def test_frozen_output_field_order(self):
        tick_digest = hashlib.sha256("\n".join(TICK_FIELDS).encode("utf-8")).hexdigest()
        summary_digest = hashlib.sha256(
            "\n".join(SUMMARY_FIELDS).encode("utf-8")
        ).hexdigest()

        self.assertEqual(len(TICK_FIELDS), 57)
        self.assertEqual(
            tick_digest,
            "7912a571fe38924fb37a671915794004178f1502c1d7803afb986eb276a2b848",
        )
        self.assertEqual(len(SUMMARY_FIELDS), 41)
        self.assertEqual(
            summary_digest,
            "88b2d9f98a29e2a8d88798626784590159ef274f3ba4cffc419b43ec3093ee9a",
        )

    def test_historical_runner_reexports_extracted_api(self):
        self.assertIs(historical_runner.TICK_FIELDS, TICK_FIELDS)
        self.assertIs(historical_runner.SUMMARY_FIELDS, SUMMARY_FIELDS)
        self.assertIs(historical_runner.summarize_scenario, summarize_scenario)
        self.assertIs(historical_runner.write_csv, write_csv)

    def test_summary_shape_matches_frozen_schema(self):
        row = dict.fromkeys(TICK_FIELDS)
        row.update(
            {
                "elapsed_s": 1.0,
                "sim_time_s": 2.0,
                "ego_speed_kph": 0.0,
                "ego_acceleration_mps2": 0.0,
                "ego_jerk_mps3": 0.0,
                "aeb_state": "NORMAL",
                "aeb_override": 0,
                "collision_count": 0,
                "raw_points": 0,
                "path_candidates": 0,
                "clusters": 0,
                "confirmed_clusters": 0,
            }
        )

        summary = summarize_scenario(
            {"id": "golden_clear", "expected_brake": False},
            [row],
            "golden_clear.csv",
        )

        self.assertEqual(list(summary), SUMMARY_FIELDS)
        self.assertEqual(summary["status"], "PASS")
        self.assertFalse(summary["brake_activated"])
        self.assertEqual(summary["failure_reason"], "")

    def test_csv_writer_preserves_schema_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.csv"
            write_csv(path, SUMMARY_FIELDS, [])
            header = path.read_text().splitlines()[0]

        self.assertEqual(header, ",".join(SUMMARY_FIELDS))


if __name__ == "__main__":
    unittest.main()
