"""Unit tests for the automatic model pipeline."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from scripts.train_yolo_pipeline import (
    difference_hash,
    hamming_distance,
    parse_yolo_label,
)


class ModelPipelineTests(unittest.TestCase):
    def test_valid_label(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.txt"
            path.write_text("0 0.5 0.5 0.2 0.3\n", encoding="utf-8")
            instances, errors = parse_yolo_label(path)
        self.assertEqual(instances, 1)
        self.assertEqual(errors, [])

    def test_invalid_label_coordinate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.txt"
            path.write_text("0 1.2 0.5 0.2 0.3\n", encoding="utf-8")
            instances, errors = parse_yolo_label(path)
        self.assertEqual(instances, 0)
        self.assertEqual(len(errors), 1)

    def test_difference_hash_matches_identical_images(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.jpg"
            second = Path(directory) / "second.jpg"
            image = np.zeros((40, 60, 3), dtype=np.uint8)
            image[:, 30:] = 255
            cv2.imwrite(str(first), image)
            cv2.imwrite(str(second), image)
            first_hash = difference_hash(first)
            second_hash = difference_hash(second)
        self.assertIsNotNone(first_hash)
        self.assertEqual(hamming_distance(first_hash, second_hash), 0)


if __name__ == "__main__":
    unittest.main()
