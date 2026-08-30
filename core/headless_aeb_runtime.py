"""Shared policy-controlled headless AEB runtime.

Sensor construction and camera confirmation remain entry-point concerns.  This
class centralizes the invariant tick order: radar pipeline, permission policy,
then brake override.  It deliberately contains no CARLA scenario or detector
configuration logic.
"""

from __future__ import annotations

from typing import Callable, Optional

from control.brake import AEBState, apply_brake_override
from core.brake_permission_policy import (
    BrakePermissionContext,
    BrakePermissionPolicy,
    BrakePermissionResult,
    RadarOnlyPolicy,
)


class PolicyControlledAEBRuntime(object):
    """Apply one brake-permission policy to a radar pipeline."""

    def __init__(
        self,
        ego,
        radar,
        pipeline,
        brake_policy: Optional[BrakePermissionPolicy] = None,
        brake_override: Callable = apply_brake_override,
    ):
        self.ego = ego
        self.radar = radar
        self.pipeline = pipeline
        self.brake_policy = brake_policy or RadarOnlyPolicy()
        self._apply_brake_override = brake_override
        self.decision = self.pipeline.decision
        self.permission_result = None
        self.aeb_override_active = False

    def tick(self):
        frame = self.pipeline.update(self.radar)
        result = self.brake_policy.evaluate(self._permission_context(frame))
        self._record_permission_result(result)

        if self.decision.state == AEBState.BRAKE:
            self._apply_brake_override(self.ego, self.decision)
            self.aeb_override_active = True
        elif self.aeb_override_active:
            self._apply_brake_override(self.ego, self.decision)
            self.aeb_override_active = False
        return frame

    def _permission_context(self, frame) -> BrakePermissionContext:
        """Build the radar-only context; fusion runtimes override this hook."""

        return BrakePermissionContext(
            radar_decision=frame.decision,
            target=getattr(frame, "target", None),
            timestamp_s=getattr(frame, "radar_timestamp_s", None),
        )

    def _record_permission_result(self, result: BrakePermissionResult) -> None:
        self.permission_result = result
        self.decision = result.decision

    def reset_control_state(self):
        self.pipeline.reset_control_state()
        self.brake_policy.reset()
        self.decision = self.pipeline.decision
        self.permission_result = None
        self.aeb_override_active = False

    def destroy(self):
        self.pipeline.reset()
        self.radar.destroy()
