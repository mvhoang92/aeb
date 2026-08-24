"""Tests for simulation-time YOLO cadence and explicit cleanup."""

from __future__ import annotations

import unittest

import numpy as np

from ui.manual_control_common import YoloDetector


class YoloDetectorTimingTests(unittest.TestCase):
    def detector_stub(self):
        detector = YoloDetector.__new__(YoloDetector)
        detector.model = object()
        detector.session = None
        detector.input_name = None
        detector.output_names = None
        detector.inference_interval_s = 0.15
        detector._last_inference_time = None
        detector._last_detections = []
        detector.runtime_label = "TEST"
        detector.status = "ready"
        detector.calls = 0

        def infer_stub(_image):
            detector.calls += 1
            return [detector.calls]

        detector._infer_ultralytics = infer_stub
        return detector

    def test_simulation_timestamp_controls_inference_cadence(self):
        detector = self.detector_stub()
        image = np.zeros((4, 4, 3), dtype=np.uint8)

        first = detector.infer(image, timestamp_s=1.00)
        held = detector.infer(image, timestamp_s=1.10)
        second = detector.infer(image, timestamp_s=1.15)

        self.assertEqual([1], first)
        self.assertEqual([1], held)
        self.assertEqual([2], second)
        self.assertEqual(2, detector.calls)

    def test_timestamp_reset_does_not_freeze_inference(self):
        detector = self.detector_stub()
        image = np.zeros((4, 4, 3), dtype=np.uint8)
        detector.infer(image, timestamp_s=10.0)

        result = detector.infer(image, timestamp_s=0.1)

        self.assertEqual([2], result)

    def test_destroy_releases_runtime_references(self):
        detector = self.detector_stub()
        detector.session = object()
        detector._last_detections = [1]
        detector._last_inference_time = 1.0

        detector.destroy()

        self.assertIsNone(detector.model)
        self.assertIsNone(detector.session)
        self.assertEqual([], detector._last_detections)
        self.assertIsNone(detector._last_inference_time)


if __name__ == "__main__":
    unittest.main()
