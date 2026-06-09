"""Unit tests for ONNX class-name metadata parsing."""

from __future__ import annotations

import unittest

from ui.manual_control_common import onnx_model_names


class OnnxModelNamesTests(unittest.TestCase):
    def test_custom_single_class_names(self):
        names = onnx_model_names({"names": "{0: 'car'}"}, {0: "person"})
        self.assertEqual(names, {0: "car"})

    def test_invalid_metadata_uses_fallback(self):
        names = onnx_model_names({"names": "not valid"}, {2: "car"})
        self.assertEqual(names, {2: "car"})


if __name__ == "__main__":
    unittest.main()
