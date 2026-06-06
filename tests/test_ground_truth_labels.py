"""Unit tests for CARLA ground-truth camera projection helpers."""

from __future__ import annotations

import unittest

import numpy as np

from core.ground_truth_labels import (
    ProjectedBox,
    camera_intrinsic,
    estimate_box_visibility,
    fit_box_to_visible_vehicle,
    project_camera_box,
)


class GroundTruthProjectionTests(unittest.TestCase):
    def setUp(self):
        self.intrinsic = camera_intrinsic(1280, 720, 70.0)

    def test_box_in_front_projects_inside_image(self):
        vertices = box_vertices(
            center=(0.0, 0.0, 20.0),
            extent=(1.0, 1.0, 2.0),
        )
        box = project_camera_box(vertices, self.intrinsic, 1280, 720)
        self.assertIsNotNone(box)
        self.assertGreater(box.width, 0.0)
        self.assertGreater(box.height, 0.0)
        self.assertGreaterEqual(box.x1, 0.0)
        self.assertLessEqual(box.x2, 1279.0)

    def test_box_behind_camera_is_rejected(self):
        vertices = box_vertices(
            center=(0.0, 0.0, -10.0),
            extent=(1.0, 1.0, 2.0),
        )
        self.assertIsNone(
            project_camera_box(vertices, self.intrinsic, 1280, 720)
        )

    def test_near_plane_crossing_does_not_create_infinite_box(self):
        vertices = box_vertices(
            center=(0.0, 0.0, 0.15),
            extent=(0.1, 0.1, 0.1),
        )
        box = project_camera_box(
            vertices,
            self.intrinsic,
            1280,
            720,
            near_plane_m=0.10,
        )
        self.assertIsNotNone(box)
        self.assertLessEqual(box.x2, 1279.0)
        self.assertLessEqual(box.y2, 719.0)

    def test_yolo_values_are_normalized(self):
        box = ProjectedBox(100.0, 50.0, 300.0, 250.0, 10.0, 12.0, 0.0)
        values = box.as_yolo(1000, 500).split()
        self.assertEqual(values[0], "0")
        for value in values[1:]:
            self.assertGreaterEqual(float(value), 0.0)
            self.assertLessEqual(float(value), 1.0)


class VisibilityTests(unittest.TestCase):
    def test_depth_visibility_counts_target_pixels(self):
        depth = np.full((100, 100), 100.0, dtype=np.float32)
        depth[20:60, 30:70] = 20.0
        box = ProjectedBox(30.0, 20.0, 69.0, 59.0, 18.0, 22.0, 0.0)
        visibility = estimate_box_visibility(
            depth,
            box,
            depth_tolerance_m=1.0,
            sample_step_px=1,
        )
        self.assertEqual(visibility.visible_pixels, visibility.sampled_pixels)
        self.assertAlmostEqual(visibility.visible_ratio, 1.0)

    def test_semantic_and_depth_mask_tightens_box(self):
        depth = np.full((100, 100), 100.0, dtype=np.float32)
        semantic = np.zeros((100, 100), dtype=np.uint8)
        depth[30:50, 40:70] = 20.0
        semantic[30:50, 40:70] = 10
        box = ProjectedBox(20.0, 10.0, 80.0, 70.0, 18.0, 22.0, 0.0)
        visibility = fit_box_to_visible_vehicle(
            depth,
            semantic,
            box,
            vehicle_tag=10,
            depth_tolerance_m=1.0,
            padding_px=0,
        )
        self.assertEqual(visibility.visible_pixels, 600)
        self.assertEqual(visibility.fitted_box.x1, 40.0)
        self.assertEqual(visibility.fitted_box.y1, 30.0)
        self.assertEqual(visibility.fitted_box.x2, 69.0)
        self.assertEqual(visibility.fitted_box.y2, 49.0)

    def test_semantic_vehicle_at_wrong_depth_is_rejected(self):
        depth = np.full((100, 100), 10.0, dtype=np.float32)
        semantic = np.full((100, 100), 10, dtype=np.uint8)
        box = ProjectedBox(20.0, 20.0, 80.0, 80.0, 28.0, 32.0, 0.0)
        visibility = fit_box_to_visible_vehicle(depth, semantic, box)
        self.assertEqual(visibility.visible_pixels, 0)
        self.assertIsNone(visibility.fitted_box)


def box_vertices(center, extent):
    center_x, center_y, center_z = center
    extent_x, extent_y, extent_z = extent
    return np.array(
        [
            [center_x + extent_x, center_y + extent_y, center_z - extent_z],
            [center_x - extent_x, center_y + extent_y, center_z - extent_z],
            [center_x - extent_x, center_y - extent_y, center_z - extent_z],
            [center_x + extent_x, center_y - extent_y, center_z - extent_z],
            [center_x + extent_x, center_y + extent_y, center_z + extent_z],
            [center_x - extent_x, center_y + extent_y, center_z + extent_z],
            [center_x - extent_x, center_y - extent_y, center_z + extent_z],
            [center_x + extent_x, center_y - extent_y, center_z + extent_z],
        ],
        dtype=np.float64,
    )


if __name__ == "__main__":
    unittest.main()
