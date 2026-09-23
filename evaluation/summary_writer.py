"""Stable CSV/JSON summary output and repetition aggregation."""

from __future__ import annotations

import json
from pathlib import Path

from evaluation.artifact_io import write_csv
from evaluation.common import numeric_values, optional_round
from evaluation.schemas import SUMMARY_FIELDS


def aggregate_summaries(summaries):
    grouped = {}
    for summary in summaries:
        grouped.setdefault(summary["scenario_id"], []).append(summary)
    aggregate = []
    for scenario_id in sorted(grouped):
        rows = grouped[scenario_id]
        gaps = numeric_values(rows, "minimum_bumper_gap_m")
        brake_times = numeric_values(rows, "first_brake_s")
        decelerations = numeric_values(rows, "maximum_deceleration_mps2")
        aggregate.append(
            {
                "scenario_id": scenario_id,
                "runs": len(rows),
                "passes": sum(1 for row in rows if row["status"] == "PASS"),
                "pass_rate_pct": round(
                    100.0
                    * sum(1 for row in rows if row["status"] == "PASS")
                    / len(rows),
                    2,
                ),
                "brake_rate_pct": round(
                    100.0
                    * sum(1 for row in rows if row["brake_activated"])
                    / len(rows),
                    2,
                ),
                "minimum_gap_m": optional_round(min(gaps) if gaps else None, 3),
                "mean_brake_time_s": optional_round(
                    sum(brake_times) / len(brake_times)
                    if brake_times
                    else None,
                    3,
                ),
                "maximum_deceleration_mps2": optional_round(
                    max(decelerations) if decelerations else None,
                    3,
                ),
            }
        )
    return aggregate


class SummaryWriter(object):
    """Write run-level and aggregate summaries using the frozen schemas."""

    def write_run_summaries(self, run_directory, summaries):
        run_directory = Path(run_directory)
        write_csv(run_directory / "summary.csv", SUMMARY_FIELDS, summaries)
        with open(str(run_directory / "summary.json"), "w") as stream:
            json.dump(summaries, stream, ensure_ascii=False, indent=2)

    def write_aggregate_summaries(self, run_directory, summaries):
        aggregate = aggregate_summaries(summaries)
        if not aggregate:
            return
        run_directory = Path(run_directory)
        write_csv(
            run_directory / "aggregate_summary.csv",
            list(aggregate[0].keys()),
            aggregate,
        )
        with open(str(run_directory / "aggregate_summary.json"), "w") as stream:
            json.dump(aggregate, stream, ensure_ascii=False, indent=2)
