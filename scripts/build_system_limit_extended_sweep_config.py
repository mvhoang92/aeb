#!/usr/bin/env python
"""Build the extended AEB system-limit sweep config.

This keeps the long YAML scenario matrix reproducible and less error-prone.
"""

from __future__ import print_function

from pathlib import Path


AEB_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    AEB_ROOT
    / "configs"
    / "scenarios"
    / "suites"
    / "system_limit_extended_sweep.yaml"
)


RUNNER = """runner:
  map: Town04
  spawn_index: 81
  fixed_delta_seconds: 0.05
  sensor_wait_timeout_s: 1.0
  settle_ticks: 4
  stop_speed_mps: 0.30
  stop_hold_time_s: 0.20
  target_blueprint: vehicle.audi.tt
  control_mode: physics
  physics_speed_kp: 0.20
  physics_speed_ki: 0.03
  physics_speed_integral_limit: 3.0
  physics_speed_deadband_mps: 0.80
  physics_throttle_feedforward: 0.45
  physics_throttle_per_mps: 0.015
  physics_throttle_limit: 1.00
  physics_brake_limit: 0.60

scenarios:
"""


def duration_for_gap(gap_m, relative_kph, minimum_s=7.0, extra_s=4.0):
    relative_mps = max(1.0, float(relative_kph) / 3.6)
    return round(max(minimum_s, float(gap_m) / relative_mps + extra_s), 1)


def append_common(lines, scenario_id, description, scenario_type, ego_speed, duration):
    lines += [
        "  - id: {}".format(scenario_id),
        "    description: {}".format(description),
        "    type: {}".format(scenario_type),
        "    control_modes:",
        "      - physics",
        "    spawn_index: 81",
        "    ego_speed_kph: {:.1f}".format(ego_speed),
        "    duration_s: {:.1f}".format(duration),
        "    lane_follow: true",
        "    max_lane_offset_m: 1.25",
        "    expected_brake: true",
        "    expected_collision: false",
        "    min_stop_gap_m: 0.5",
    ]


def add_moving_lead(lines):
    gaps = [20, 30, 40, 50, 60, 80]
    pairs = [
        (60, 30),
        (80, 50),
        (100, 70),
        (110, 80),
    ]
    for ego_speed, target_speed in pairs:
        for gap in gaps:
            scenario_id = "ccrm_{}_{}_gap_{}".format(ego_speed, target_speed, gap)
            description = (
                "System limit sweep - moving lead, ego {} km/h, "
                "target {} km/h, gap {} m."
            ).format(ego_speed, target_speed, gap)
            duration = duration_for_gap(gap, ego_speed - target_speed)
            append_common(lines, scenario_id, description, "moving_lead", ego_speed, duration)
            lines += [
                "    target_speed_kph: {:.1f}".format(target_speed),
                "    initial_gap_m: {:.1f}".format(gap),
                "",
            ]


def add_braking_lead(lines):
    gaps = [20, 30, 40, 50, 60, 80]
    speeds = [50, 65, 80, 95, 110]
    for speed in speeds:
        for gap in gaps:
            scenario_id = "ccrb_{}_gap_{}".format(speed, gap)
            description = (
                "System limit sweep - braking lead, both {} km/h, "
                "target full brake after 1.5 s, gap {} m."
            ).format(speed, gap)
            duration = max(8.0, round(float(gap) / max(1.0, speed / 3.6) + 7.0, 1))
            append_common(lines, scenario_id, description, "braking_lead", speed, duration)
            lines += [
                "    target_speed_kph: {:.1f}".format(speed),
                "    initial_gap_m: {:.1f}".format(gap),
                "    target_brake_time_s: 1.5",
                "    target_brake: 1.0",
                "",
            ]


def add_cut_in(lines):
    gaps = [25, 35, 45, 60]
    pairs = [
        (60, 40),
        (80, 50),
        (100, 60),
    ]
    for ego_speed, cut_speed in pairs:
        for gap in gaps:
            scenario_id = "cutin_{}_{}_gap_{}".format(ego_speed, cut_speed, gap)
            description = (
                "System limit sweep - cut-in, ego {} km/h, cut-in {} km/h, "
                "initial gap {} m."
            ).format(ego_speed, cut_speed, gap)
            lines += [
                "  - id: {}".format(scenario_id),
                "    description: {}".format(description),
                "    type: cut_in",
                "    control_modes:",
                "      - physics",
                "    spawn_index: 81",
                "    ego_speed_kph: {:.1f}".format(ego_speed),
                "    duration_s: {:.1f}".format(duration_for_gap(gap, ego_speed - cut_speed, 8.0, 5.0)),
                "    lane_follow: true",
                "    max_lane_offset_m: 1.25",
                "    expected_brake: true",
                "    expected_brake_actor: cut_in",
                "    expected_collision: false",
                "    expected_hazard_initial_same_lane: false",
                "    expected_hazard_final_same_lane: true",
                "    min_stop_gap_m: 0.5",
                "    actors:",
                "      - role: cut_in",
                "        hazard: true",
                "        motion: moving",
                "        speed_kph: {:.1f}".format(cut_speed),
                "        initial_gap_m: {:.1f}".format(gap),
                "        spawn_lane: left",
                "        lane_follow: true",
                "        lane_change:",
                "          start_s: 1.0",
                "          direction: right",
                "          lookahead_m: 15.0",
                "",
            ]


def main():
    lines = [RUNNER.rstrip()]
    add_moving_lead(lines)
    add_braking_lead(lines)
    add_cut_in(lines)
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
