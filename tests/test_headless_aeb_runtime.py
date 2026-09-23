"""Unit tests for the shared policy-controlled headless runtime."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from control.brake import AEBDecision, AEBState
from core.brake_permission_policy import RadarOnlyPolicy
from core.headless_aeb_runtime import PolicyControlledAEBRuntime


def decision(state):
    return AEBDecision(
        state=state,
        brake=1.0 if state == AEBState.BRAKE else 0.0,
        throttle=0.0,
        ttc_s=1.0,
        target_distance_m=10.0,
        relative_velocity_mps=-10.0,
        should_override=state == AEBState.BRAKE,
        reason=state.value.lower(),
    )


class FakePipeline(object):
    def __init__(self, states):
        self.frames = [
            SimpleNamespace(
                decision=decision(state),
                target="target",
                radar_timestamp_s=float(index),
            )
            for index, state in enumerate(states)
        ]
        self.decision = decision(AEBState.NORMAL)
        self.reset_control_calls = 0
        self.reset_calls = 0

    def update(self, radar):
        del radar
        frame = self.frames.pop(0)
        self.decision = frame.decision
        return frame

    def reset_control_state(self):
        self.reset_control_calls += 1
        self.decision = decision(AEBState.NORMAL)

    def reset(self):
        self.reset_calls += 1


class FakeRadar(object):
    def __init__(self):
        self.destroy_calls = 0

    def destroy(self):
        self.destroy_calls += 1


class RecordingRadarPolicy(RadarOnlyPolicy):
    def __init__(self):
        self.contexts = []
        self.reset_calls = 0

    def evaluate(self, context):
        self.contexts.append(context)
        return super(RecordingRadarPolicy, self).evaluate(context)

    def reset(self):
        self.reset_calls += 1


class HeadlessRuntimeTests(unittest.TestCase):
    def test_tick_order_applies_brake_and_one_release_override(self):
        pipeline = FakePipeline(
            [AEBState.BRAKE, AEBState.BRAKE, AEBState.RELEASE, AEBState.NORMAL]
        )
        radar = FakeRadar()
        policy = RecordingRadarPolicy()
        overrides = []
        runtime = PolicyControlledAEBRuntime(
            ego="ego",
            radar=radar,
            pipeline=pipeline,
            brake_policy=policy,
            brake_override=lambda ego, value: overrides.append((ego, value.state)),
        )

        frames = [runtime.tick() for _ in range(4)]

        self.assertEqual(
            overrides,
            [
                ("ego", AEBState.BRAKE),
                ("ego", AEBState.BRAKE),
                ("ego", AEBState.RELEASE),
            ],
        )
        self.assertEqual([item.radar_timestamp_s for item in frames], [0.0, 1.0, 2.0, 3.0])
        self.assertEqual([item.timestamp_s for item in policy.contexts], [0.0, 1.0, 2.0, 3.0])
        self.assertFalse(runtime.aeb_override_active)

    def test_reset_and_destroy_delegate_in_historical_order(self):
        pipeline = FakePipeline([])
        radar = FakeRadar()
        policy = RecordingRadarPolicy()
        runtime = PolicyControlledAEBRuntime(
            ego="ego",
            radar=radar,
            pipeline=pipeline,
            brake_policy=policy,
        )
        runtime.aeb_override_active = True

        runtime.reset_control_state()
        runtime.destroy()

        self.assertEqual(pipeline.reset_control_calls, 1)
        self.assertEqual(policy.reset_calls, 1)
        self.assertFalse(runtime.aeb_override_active)
        self.assertEqual(pipeline.reset_calls, 1)
        self.assertEqual(radar.destroy_calls, 1)


if __name__ == "__main__":
    unittest.main()
