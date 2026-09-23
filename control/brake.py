"""Compatibility facade for the decomposed AEB brake controller.

Historical imports from ``control.brake`` remain supported.  Implementations
live in focused modules so risk, staged/PID commands, state transitions and
vehicle actuation can be tested independently.
"""

from control.actuation import (
    apply_brake_override,
    clone_vehicle_control,
    make_brake_control,
)
from control.controller import BinaryAEB
from control.risk_model import compute_ttc, required_stopping_distance
from control.types import (
    AEBDecision,
    AEBState,
    BinaryBrakeConfig,
    SimpleVehicleControl,
)
from control.utils import as_bool, clamp, first_existing_attr, set_if_present

__all__ = [
    "AEBDecision",
    "AEBState",
    "BinaryAEB",
    "BinaryBrakeConfig",
    "SimpleVehicleControl",
    "apply_brake_override",
    "as_bool",
    "clamp",
    "clone_vehicle_control",
    "compute_ttc",
    "first_existing_attr",
    "make_brake_control",
    "required_stopping_distance",
    "set_if_present",
]
