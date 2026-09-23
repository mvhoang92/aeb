"""Vehicle-control cloning and AEB brake override helpers."""

from __future__ import annotations

from typing import Optional

from control.types import AEBDecision, AEBState, SimpleVehicleControl
from control.utils import clamp, set_if_present


def make_brake_control(
    decision: AEBDecision,
    base_control: Optional[object] = None,
) -> object:
    control = clone_vehicle_control(base_control)
    if decision.state == AEBState.BRAKE:
        set_if_present(control, "throttle", 0.0)
        set_if_present(control, "brake", clamp(decision.brake, 0.0, 1.0))
        set_if_present(control, "hand_brake", False)
    elif decision.state == AEBState.RELEASE:
        set_if_present(control, "brake", 0.0)
    return control

def apply_brake_override(
    vehicle: object,
    decision: AEBDecision,
    base_control: Optional[object] = None,
) -> object:
    if base_control is None and hasattr(vehicle, "get_control"):
        base_control = vehicle.get_control()
    control = make_brake_control(decision, base_control)
    vehicle.apply_control(control)
    return control

def clone_vehicle_control(base_control: Optional[object]) -> object:
    if base_control is None:
        return SimpleVehicleControl()

    try:
        control = base_control.__class__()
    except Exception:  # pylint: disable=broad-except
        control = SimpleVehicleControl()

    for name in (
        "throttle",
        "steer",
        "brake",
        "hand_brake",
        "reverse",
        "manual_gear_shift",
        "gear",
    ):
        if hasattr(base_control, name) and hasattr(control, name):
            setattr(control, name, getattr(base_control, name))
    return control
