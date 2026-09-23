"""Failure/braking severity metrics derived from tick telemetry."""

from __future__ import annotations

from evaluation.common import numeric_values, optional_round


def compute_severity_metrics(rows, metric_start_s=0.25):
    """Return the severity fields used by the frozen scenario summary.

    ``metric_start_s`` excludes initial spawn/settling transients exactly as the
    historical runner did.  Last-tick speed is a proxy, not impact speed.
    """

    metric_rows = [
        row for row in rows if float(row.get("elapsed_s", 0.0)) >= metric_start_s
    ]
    accelerations = numeric_values(metric_rows, "ego_acceleration_mps2")
    jerks = numeric_values(metric_rows, "ego_jerk_mps3")
    return {
        "maximum_deceleration_mps2": optional_round(
            max(0.0, -min(accelerations)) if accelerations else None,
            3,
        ),
        "maximum_abs_jerk_mps3": optional_round(
            max(abs(value) for value in jerks) if jerks else None,
            3,
        ),
        "final_speed_kph": optional_round(
            rows[-1]["ego_speed_kph"] if rows else None,
            3,
        ),
    }
