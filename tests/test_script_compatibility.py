"""Compatibility checks for categorized script implementations."""

from __future__ import annotations

import unittest
from pathlib import Path

from scripts import analyze_v4_final as legacy_analysis
from scripts import collect_yolo_dataset as legacy_collector
from scripts import check_workspace as workspace_entry
from scripts import run_v4_campaign as legacy_campaign
from scripts import run_v4_final_pipeline as legacy_pipeline
from scripts import train_yolo_pipeline as legacy_training
from scripts import validate_v5_manuscript_claims as legacy_validator
from scripts.analysis import analyze_v4_final
from scripts.analysis import validate_v5_manuscript_claims
from scripts.campaign import run_v4_campaign, run_v4_final_pipeline
from scripts.dataset import collect_yolo_dataset
from scripts.training import train_yolo_pipeline
from scripts.maintenance import check_workspace


AEB_ROOT = Path(__file__).resolve().parents[1]


class ScriptCompatibilityTests(unittest.TestCase):
    def test_campaign_wrappers_reexport_implementations(self):
        self.assertIs(legacy_campaign.main, run_v4_campaign.main)
        self.assertIs(legacy_campaign.job_command, run_v4_campaign.job_command)
        self.assertIs(legacy_pipeline.main, run_v4_final_pipeline.main)
        self.assertIs(
            legacy_pipeline.validate_cuda_runtime,
            run_v4_final_pipeline.validate_cuda_runtime,
        )
        self.assertEqual(run_v4_campaign.AEB_ROOT, AEB_ROOT)
        self.assertEqual(run_v4_final_pipeline.AEB_ROOT, AEB_ROOT)

    def test_analysis_wrappers_reexport_implementations(self):
        self.assertIs(legacy_analysis.main, analyze_v4_final.main)
        self.assertIs(legacy_analysis.confusion, analyze_v4_final.confusion)
        self.assertIs(legacy_validator.main, validate_v5_manuscript_claims.main)
        self.assertEqual(analyze_v4_final.AEB_ROOT, AEB_ROOT)
        self.assertEqual(validate_v5_manuscript_claims.ROOT, AEB_ROOT)

    def test_workspace_wrapper_reexports_implementation(self):
        self.assertIs(workspace_entry.main, check_workspace.main)
        self.assertIs(workspace_entry.collect_status, check_workspace.collect_status)

    def test_dataset_and_training_wrappers_reexport_implementations(self):
        self.assertIs(
            legacy_collector.heading_difference_degrees,
            collect_yolo_dataset.heading_difference_degrees,
        )
        self.assertIs(legacy_training.audit_dataset, train_yolo_pipeline.audit_dataset)
        self.assertEqual(collect_yolo_dataset.AEB_ROOT, AEB_ROOT)
        self.assertEqual(train_yolo_pipeline.AEB_ROOT, AEB_ROOT)


if __name__ == "__main__":
    unittest.main()
