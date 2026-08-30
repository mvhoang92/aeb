"""Named-scenario scoring and summary metric calculation."""

from __future__ import annotations

from control.brake import as_bool
from evaluation.common import max_value, numeric_values, optional_round
from evaluation.severity import compute_severity_metrics


def summarize_scenario(scenario, rows, log_file, run_index=1):
    brake_rows = [row for row in rows if row["aeb_override"]]
    warning_rows = [
        row for row in rows if row["aeb_state"] in ("WARNING", "BRAKE")
    ]
    collision = any(row["collision_count"] for row in rows)
    brake_activated = bool(brake_rows)
    expected_brake = bool(scenario.get("expected_brake", False))
    expected_collision = bool(scenario.get("expected_collision", False))
    failures = []
    if brake_activated != expected_brake:
        failures.append(
            "expected_brake={} actual={}".format(expected_brake, brake_activated)
        )
    if collision != expected_collision:
        failures.append(
            "expected_collision={} actual={}".format(expected_collision, collision)
        )

    center_distances = numeric_values(rows, "center_distance_m")
    bumper_gaps = numeric_values(rows, "bumper_gap_m")
    finite_ttc = numeric_values(rows, "ttc_s")
    metric_start_s = float(scenario.get("metrics_ignore_initial_s", 0.25))
    metric_rows = [
        row for row in rows if float(row.get("elapsed_s", 0.0)) >= metric_start_s
    ]
    severity = compute_severity_metrics(rows, metric_start_s)
    lane_offsets = numeric_values(metric_rows, "ego_lane_center_offset_m")
    heading_errors = numeric_values(metric_rows, "ego_heading_error_deg")
    if expected_brake and not collision and bumper_gaps:
        minimum_stop_gap = float(scenario.get("min_stop_gap_m", 0.5))
        if min(bumper_gaps) < minimum_stop_gap:
            failures.append(
                "minimum_gap={:.3f}m below {:.3f}m".format(
                    min(bumper_gaps),
                    minimum_stop_gap,
                )
            )
    if lane_offsets and scenario.get("max_lane_offset_m") is not None:
        maximum_lane_offset = max(abs(value) for value in lane_offsets)
        allowed_lane_offset = float(scenario["max_lane_offset_m"])
        if maximum_lane_offset > allowed_lane_offset:
            failures.append(
                "maximum_lane_offset={:.3f}m above {:.3f}m".format(
                    maximum_lane_offset,
                    allowed_lane_offset,
                )
            )
    lane_relation_rows = [
        row
        for row in rows
        if row.get("ego_lane_id") is not None
        and row.get("target_lane_id") is not None
    ]
    initial_same_lane = (
        lane_relation_rows[0]["ego_lane_id"]
        == lane_relation_rows[0]["target_lane_id"]
        if lane_relation_rows
        else None
    )
    final_same_lane = (
        lane_relation_rows[-1]["ego_lane_id"]
        == lane_relation_rows[-1]["target_lane_id"]
        if lane_relation_rows
        else None
    )
    first_same_lane = next(
        (
            row
            for row in lane_relation_rows
            if row["ego_lane_id"] == row["target_lane_id"]
        ),
        None,
    )
    for key, actual in (
        ("expected_hazard_initial_same_lane", initial_same_lane),
        ("expected_hazard_final_same_lane", final_same_lane),
    ):
        if scenario.get(key) is None or actual is None:
            continue
        expected = as_bool(scenario.get(key))
        if actual != expected:
            failures.append("{}={} actual={}".format(key, expected, actual))
    first_brake = brake_rows[0] if brake_rows else None
    first_warning = warning_rows[0] if warning_rows else None
    expected_brake_actor = scenario.get("expected_brake_actor")
    if first_brake is not None and expected_brake_actor is not None:
        actual_brake_actor = first_brake.get("radar_target_actor_role")
        if actual_brake_actor != expected_brake_actor:
            failures.append(
                "expected_brake_actor={} actual={}".format(
                    expected_brake_actor,
                    actual_brake_actor,
                )
            )
    hazard_match_values = numeric_values(rows, "radar_target_matches_hazard")
    fallback_rows = [row for row in rows if row.get("radar_fallback_active")]
    fusion_blocked_rows = [
        row
        for row in rows
        if row.get("fusion_gate_action") == "fusion_blocked_brake"
    ]
    first_fallback = fallback_rows[0] if fallback_rows else None
    return {
        "scenario_id": scenario["id"],
        "run_index": run_index,
        "description": scenario.get("description", ""),
        "status": "FAIL" if failures else "PASS",
        "expected_brake": expected_brake,
        "brake_activated": brake_activated,
        "expected_collision": expected_collision,
        "collision": collision,
        "duration_s": optional_round(rows[-1]["elapsed_s"] if rows else 0.0, 3),
        "first_warning_s": optional_round(
            first_warning["elapsed_s"] if first_warning else None,
            3,
        ),
        "first_brake_s": optional_round(
            first_brake["elapsed_s"] if first_brake else None,
            3,
        ),
        "brake_speed_kph": optional_round(
            first_brake["ego_speed_kph"] if first_brake else None,
            3,
        ),
        "brake_gap_m": optional_round(
            first_brake["bumper_gap_m"] if first_brake else None,
            3,
        ),
        "minimum_center_distance_m": optional_round(
            min(center_distances) if center_distances else None,
            3,
        ),
        "minimum_bumper_gap_m": optional_round(
            (
                min(bumper_gaps)
                if bumper_gaps
                and scenario.get("type") != "adjacent_stationary"
                and as_bool(scenario.get("report_minimum_gap", True))
                else None
            ),
            3,
        ),
        "minimum_ttc_s": optional_round(min(finite_ttc) if finite_ttc else None, 3),
        "brake_required_distance_m": optional_round(
            first_brake["required_distance_m"] if first_brake else None,
            3,
        ),
        "brake_distance_margin_m": optional_round(
            first_brake["distance_margin_m"] if first_brake else None,
            3,
        ),
        "maximum_deceleration_mps2": severity["maximum_deceleration_mps2"],
        "maximum_abs_jerk_mps3": severity["maximum_abs_jerk_mps3"],
        "final_speed_kph": severity["final_speed_kph"],
        "target_confirmed_rate_pct": optional_round(
            (
                100.0
                * sum(1 for row in rows if row["target_track_id"] is not None)
                / len(rows)
                if rows
                else None
            ),
            2,
        ),
        "maximum_raw_points": max_value(rows, "raw_points"),
        "maximum_path_candidates": max_value(rows, "path_candidates"),
        "maximum_clusters": max_value(rows, "clusters"),
        "maximum_confirmed_clusters": max_value(rows, "confirmed_clusters"),
        "maximum_abs_lane_center_offset_m": optional_round(
            max(abs(value) for value in lane_offsets) if lane_offsets else None,
            3,
        ),
        "maximum_abs_heading_error_deg": optional_round(
            max(abs(value) for value in heading_errors) if heading_errors else None,
            3,
        ),
        "hazard_initial_same_lane": initial_same_lane,
        "hazard_final_same_lane": final_same_lane,
        "first_hazard_same_lane_s": optional_round(
            first_same_lane["elapsed_s"] if first_same_lane else None,
            3,
        ),
        "radar_target_hazard_match_rate_pct": optional_round(
            (
                100.0 * sum(hazard_match_values) / len(hazard_match_values)
                if hazard_match_values
                else None
            ),
            2,
        ),
        "brake_target_actor_role": (
            first_brake.get("radar_target_actor_role") if first_brake else None
        ),
        "radar_fallback_activated": bool(fallback_rows),
        "radar_fallback_first_s": optional_round(
            first_fallback.get("elapsed_s") if first_fallback else None,
            3,
        ),
        "radar_fallback_tick_count": len(fallback_rows),
        "fusion_blocked_tick_count": len(fusion_blocked_rows),
        "evidence_video": None,
        "evidence_events": None,
        "log_file": log_file,
        "failure_reason": "; ".join(failures),
    }
