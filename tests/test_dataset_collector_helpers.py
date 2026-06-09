"""Unit tests for dataset collector helpers."""

from __future__ import annotations

import unittest

from scripts.collect_yolo_dataset import heading_difference_degrees


class DatasetCollectorHelperTests(unittest.TestCase):
    def test_heading_difference_handles_wraparound(self):
        self.assertAlmostEqual(heading_difference_degrees(179.0, -179.0), 2.0)

    def test_heading_difference_is_unsigned(self):
        self.assertAlmostEqual(heading_difference_degrees(10.0, 350.0), 20.0)


if __name__ == "__main__":
    unittest.main()
