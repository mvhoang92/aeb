"""Tests for deterministic legacy-to-workspace path resolution."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from infrastructure.workspace import (
    dataset_root,
    legacy_workspace_path,
    resolve_project_path,
    workspace_directories,
    workspace_root,
)


class WorkspacePathTests(unittest.TestCase):
    def setUp(self):
        self.environment = {"AEB_WORKSPACE_ROOT": "/tmp/aeb-test-workspace"}

    def test_environment_selects_workspace(self):
        self.assertEqual(
            workspace_root(self.environment),
            Path("/tmp/aeb-test-workspace"),
        )

    def test_dataset_generations_have_stable_active_archive_mapping(self):
        self.assertEqual(
            dataset_root("dataset_v7_same_lane", self.environment),
            Path("/tmp/aeb-test-workspace/datasets/active/v7_same_lane"),
        )
        self.assertEqual(
            dataset_root("dataset_v6", self.environment),
            Path("/tmp/aeb-test-workspace/datasets/archive/v6"),
        )

    def test_legacy_generated_paths_map_by_artifact_class(self):
        cases = {
            "aeb/logs/run_01": "runs/logs/run_01",
            "aeb/training_runs/detect": "training/detect",
            "aeb/outputs/paper_v4_final_pipeline/run": (
                "runs/campaigns/paper_v4_final_pipeline/run"
            ),
            "aeb/outputs/dataset_v7_same_lane_box_check": (
                "runs/dataset_box_checks/dataset_v7_same_lane_box_check"
            ),
            "aeb/outputs/scenario_videos": "runs/videos/scenario_videos",
            "aeb/outputs/sensor_coverage_test": (
                "runs/sensor_coverage/sensor_coverage_test"
            ),
        }
        for source, expected in cases.items():
            self.assertEqual(
                legacy_workspace_path(source, self.environment),
                Path("/tmp/aeb-test-workspace") / expected,
            )

    def test_existing_explicit_path_wins_over_workspace_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            existing = project / "aeb" / "dataset_v6"
            existing.mkdir(parents=True)
            resolved = resolve_project_path(
                "aeb/dataset_v6",
                project_root=project,
                aeb_root=project / "aeb",
                environment=self.environment,
            )
        self.assertEqual(resolved, existing)

    def test_workspace_directory_names_are_complete(self):
        names = set(workspace_directories(self.environment))
        self.assertEqual(
            names,
            {
                "workspace",
                "datasets_active",
                "datasets_archive",
                "logs",
                "campaigns",
                "videos",
                "sensor_coverage",
                "dataset_box_checks",
                "diagnostics",
                "report_support",
                "training",
                "environments",
                "quarantine",
            },
        )


if __name__ == "__main__":
    unittest.main()
