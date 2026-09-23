"""Compatibility tests for decomposed brake-control modules."""

from __future__ import annotations

import unittest

from control import brake
from control.actuation import apply_brake_override, make_brake_control
from control.controller import BinaryAEB
from control.risk_model import compute_ttc, required_stopping_distance
from control.staged_pid import BrakeCommandMixin
from control.state_machine import AEBStateMachineMixin
from control.types import AEBDecision, AEBState, BinaryBrakeConfig


class ControlModuleCompatibilityTests(unittest.TestCase):
    def test_historical_facade_reexports_public_objects(self):
        self.assertIs(brake.BinaryAEB, BinaryAEB)
        self.assertIs(brake.BinaryBrakeConfig, BinaryBrakeConfig)
        self.assertIs(brake.AEBDecision, AEBDecision)
        self.assertIs(brake.AEBState, AEBState)
        self.assertIs(brake.compute_ttc, compute_ttc)
        self.assertIs(brake.make_brake_control, make_brake_control)
        self.assertIs(brake.apply_brake_override, apply_brake_override)

    def test_controller_composes_command_and_state_implementations(self):
        self.assertTrue(issubclass(BinaryAEB, BrakeCommandMixin))
        self.assertTrue(issubclass(BinaryAEB, AEBStateMachineMixin))

    def test_method_and_standalone_stopping_distance_match(self):
        config = BinaryBrakeConfig(
            response_time_s=0.35,
            ego_emergency_decel_mps2=7.0,
            target_emergency_decel_mps2=6.0,
            stopping_distance_offset_m=2.0,
        )
        controller = BinaryAEB(config)

        expected = required_stopping_distance(config, 20.0, -10.0)

        self.assertEqual(controller.required_stopping_distance(20.0, -10.0), expected)
        self.assertIsNone(required_stopping_distance(config, None, -10.0))

    def test_ttc_convention_is_preserved(self):
        self.assertEqual(compute_ttc(20.0, -10.0), 2.0)
        self.assertEqual(compute_ttc(0.0, -10.0), 0.0)
        self.assertEqual(compute_ttc(20.0, 1.0), float("inf"))


if __name__ == "__main__":
    unittest.main()
