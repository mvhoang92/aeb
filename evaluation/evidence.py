"""Pure evidence-event selection helpers."""

from __future__ import annotations


def select_evidence_events(rows, include_minimum_gap=True):
    if not rows:
        return []

    warning = next(
        (row for row in rows if row.get("aeb_state") in ("WARNING", "BRAKE")),
        None,
    )
    brake = next((row for row in rows if row.get("aeb_override")), None)
    gap_rows = [
        row for row in rows if row.get("bumper_gap_m") not in (None, "")
    ]
    minimum_gap = (
        min(gap_rows, key=lambda row: float(row["bumper_gap_m"]))
        if gap_rows and include_minimum_gap
        else None
    )
    events = []
    for name, row in (
        ("first_warning", warning),
        ("first_brake", brake),
        ("minimum_gap", minimum_gap),
    ):
        if row is None:
            continue
        events.append(
            {
                "name": name,
                "frame": int(row["frame"]),
                "elapsed_s": float(row["elapsed_s"]),
                "ego_speed_kph": float(row["ego_speed_kph"]),
                "bumper_gap_m": optional_float(row.get("bumper_gap_m")),
                "ttc_s": optional_float(row.get("ttc_s")),
                "aeb_state": row.get("aeb_state"),
            }
        )
    return events

def nearest_frame_path(frame_paths, target_frame):
    if not frame_paths:
        return None
    return min(
        frame_paths,
        key=lambda path: abs(int(path.stem) - int(target_frame)),
    )

def optional_float(value):
    if value in (None, ""):
        return None
    return float(value)
