"""Unit tests for ONNX class-name metadata parsing."""

from __future__ import annotations

import unittest

from ui.manual_control_common import Detection, nms_detections, onnx_model_names


class OnnxModelNamesTests(unittest.TestCase):
    def test_custom_single_class_names(self):
        names = onnx_model_names({"names": "{0: 'car'}"}, {0: "person"})
        self.assertEqual(names, {0: "car"})

    def test_invalid_metadata_uses_fallback(self):
        names = onnx_model_names({"names": "not valid"}, {2: "car"})
        self.assertEqual(names, {2: "car"})


class OnnxNmsTests(unittest.TestCase):
    def test_overlapping_same_class_boxes_are_suppressed(self):
        detections = [
            Detection(10.0, 10.0, 100.0, 100.0, 0.90, 0, "car"),
            Detection(12.0, 12.0, 98.0, 98.0, 0.80, 0, "car"),
            Detection(200.0, 200.0, 260.0, 260.0, 0.70, 0, "car"),
        ]

        kept = nms_detections(detections, 0.5)

        self.assertEqual(len(kept), 2)
        self.assertEqual(kept[0].confidence, 0.90)


if __name__ == "__main__":
    unittest.main()
