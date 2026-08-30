"""Tick-level telemetry derivation."""

from __future__ import annotations


def add_motion_metrics(row, previous_row):
    if previous_row is None:
        return
    dt = float(row["sim_time_s"]) - float(previous_row["sim_time_s"])
    if dt <= 1e-9:
        return
    acceleration = row.get("ego_acceleration_mps2")
    previous_acceleration = previous_row.get("ego_acceleration_mps2")
    if acceleration is not None and previous_acceleration is not None:
        row["ego_jerk_mps3"] = round(
            (float(acceleration) - float(previous_acceleration)) / dt,
            4,
        )
