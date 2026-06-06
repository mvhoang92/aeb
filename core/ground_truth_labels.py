"""Project CARLA vehicle bounding boxes into camera images and YOLO labels."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np


BOX_EDGES = (
    (0, 1),
    (1, 3),
    (3, 2),
    (2, 0),
    (0, 4),
    (4, 5),
    (5, 1),
    (5, 7),
    (7, 6),
    (6, 4),
    (6, 2),
    (7, 3),
)


@dataclass(frozen=True)
class ProjectedBox:
    x1: float
    y1: float
    x2: float
    y2: float
    min_depth_m: float
    max_depth_m: float
    truncation: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        return max(0.0, self.width) * max(0.0, self.height)

    def as_yolo(self, image_width: int, image_height: int, class_id: int = 0) -> str:
        center_x = (self.x1 + self.x2) * 0.5 / float(image_width)
        center_y = (self.y1 + self.y2) * 0.5 / float(image_height)
        width = self.width / float(image_width)
        height = self.height / float(image_height)
        return "{} {:.6f} {:.6f} {:.6f} {:.6f}".format(
            int(class_id),
            clamp(center_x, 0.0, 1.0),
            clamp(center_y, 0.0, 1.0),
            clamp(width, 0.0, 1.0),
            clamp(height, 0.0, 1.0),
        )


@dataclass(frozen=True)
class VisibilityResult:
    visible_pixels: int
    sampled_pixels: int
    visible_ratio: float
    fitted_box: Optional[ProjectedBox] = None


def camera_intrinsic(width: int, height: int, fov_degrees: float) -> np.ndarray:
    focal = float(width) / (
        2.0 * math.tan(math.radians(float(fov_degrees)) * 0.5)
    )
    return np.array(
        [
            [focal, 0.0, float(width) * 0.5],
            [0.0, focal, float(height) * 0.5],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )


def world_vertices_to_camera(
    world_vertices: Iterable[object],
    camera_transform: object,
) -> np.ndarray:
    """Return vertices in computer-vision coordinates: x right, y down, z forward."""

    homogeneous = np.array(
        [
            [vertex.x, vertex.y, vertex.z, 1.0]
            for vertex in world_vertices
        ],
        dtype=np.float64,
    )
    if homogeneous.shape != (8, 4):
        raise ValueError("Vehicle bounding box must contain exactly 8 vertices")

    world_to_camera = np.asarray(
        camera_transform.get_inverse_matrix(),
        dtype=np.float64,
    )
    unreal_camera = np.dot(world_to_camera, homogeneous.T).T
    return np.column_stack(
        (
            unreal_camera[:, 1],
            -unreal_camera[:, 2],
            unreal_camera[:, 0],
        )
    )


def project_camera_box(
    camera_vertices: np.ndarray,
    intrinsic: np.ndarray,
    image_width: int,
    image_height: int,
    near_plane_m: float = 0.10,
) -> Optional[ProjectedBox]:
    """Project an eight-vertex 3D box, including edges crossing the near plane."""

    vertices = np.asarray(camera_vertices, dtype=np.float64)
    if vertices.shape != (8, 3):
        raise ValueError("camera_vertices must have shape (8, 3)")

    points = [point for point in vertices if point[2] >= near_plane_m]
    for first_index, second_index in BOX_EDGES:
        first = vertices[first_index]
        second = vertices[second_index]
        first_front = first[2] >= near_plane_m
        second_front = second[2] >= near_plane_m
        if first_front == second_front:
            continue
        ratio = (near_plane_m - first[2]) / (second[2] - first[2])
        points.append(first + ratio * (second - first))

    if not points:
        return None

    points_array = np.asarray(points, dtype=np.float64)
    pixels = np.dot(intrinsic, points_array.T).T
    pixels = pixels[:, :2] / pixels[:, 2:3]
    raw_x1 = float(np.min(pixels[:, 0]))
    raw_y1 = float(np.min(pixels[:, 1]))
    raw_x2 = float(np.max(pixels[:, 0]))
    raw_y2 = float(np.max(pixels[:, 1]))
    raw_area = max(0.0, raw_x2 - raw_x1) * max(0.0, raw_y2 - raw_y1)

    x1 = clamp(raw_x1, 0.0, float(image_width - 1))
    y1 = clamp(raw_y1, 0.0, float(image_height - 1))
    x2 = clamp(raw_x2, 0.0, float(image_width - 1))
    y2 = clamp(raw_y2, 0.0, float(image_height - 1))
    clipped_area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if clipped_area <= 0.0:
        return None

    truncation = 0.0 if raw_area <= 0.0 else 1.0 - clipped_area / raw_area
    front_depths = points_array[:, 2]
    return ProjectedBox(
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        min_depth_m=float(np.min(front_depths)),
        max_depth_m=float(np.max(front_depths)),
        truncation=clamp(truncation, 0.0, 1.0),
    )


def project_vehicle_box(
    bounding_box: object,
    actor_transform: object,
    camera_transform: object,
    intrinsic: np.ndarray,
    image_width: int,
    image_height: int,
    near_plane_m: float = 0.10,
) -> Optional[ProjectedBox]:
    world_vertices = bounding_box.get_world_vertices(actor_transform)
    camera_vertices = world_vertices_to_camera(world_vertices, camera_transform)
    return project_camera_box(
        camera_vertices,
        intrinsic,
        image_width,
        image_height,
        near_plane_m=near_plane_m,
    )


def decode_carla_depth(image: object) -> np.ndarray:
    """Decode CARLA's 24-bit RGB depth buffer into meters."""

    bgra = np.frombuffer(image.raw_data, dtype=np.uint8)
    bgra = bgra.reshape((image.height, image.width, 4))
    red = bgra[:, :, 2].astype(np.float32)
    green = bgra[:, :, 1].astype(np.float32)
    blue = bgra[:, :, 0].astype(np.float32)
    normalized = (red + green * 256.0 + blue * 65536.0) / 16777215.0
    return normalized * 1000.0


def decode_carla_semantic_tags(image: object) -> np.ndarray:
    """Decode raw CARLA semantic tags from the red channel."""

    bgra = np.frombuffer(image.raw_data, dtype=np.uint8)
    bgra = bgra.reshape((image.height, image.width, 4))
    return bgra[:, :, 2].copy()


def estimate_box_visibility(
    depth_m: np.ndarray,
    box: ProjectedBox,
    depth_tolerance_m: float = 1.0,
    sample_step_px: int = 2,
) -> VisibilityResult:
    """Estimate how much of a projected 3D box is visible in the depth image."""

    image_height, image_width = depth_m.shape[:2]
    x1 = max(0, int(math.floor(box.x1)))
    y1 = max(0, int(math.floor(box.y1)))
    x2 = min(image_width, int(math.ceil(box.x2)) + 1)
    y2 = min(image_height, int(math.ceil(box.y2)) + 1)
    step = max(1, int(sample_step_px))
    patch = depth_m[y1:y2:step, x1:x2:step]
    if patch.size == 0:
        return VisibilityResult(0, 0, 0.0)

    near_depth = max(0.0, box.min_depth_m - float(depth_tolerance_m))
    far_depth = box.max_depth_m + float(depth_tolerance_m)
    visible = np.logical_and(patch >= near_depth, patch <= far_depth)
    visible_pixels = int(np.count_nonzero(visible))
    sampled_pixels = int(patch.size)
    return VisibilityResult(
        visible_pixels=visible_pixels,
        sampled_pixels=sampled_pixels,
        visible_ratio=visible_pixels / float(sampled_pixels),
    )


def fit_box_to_visible_vehicle(
    depth_m: np.ndarray,
    semantic_tags: np.ndarray,
    box: ProjectedBox,
    vehicle_tag: int = 10,
    depth_tolerance_m: float = 1.5,
    padding_px: int = 2,
) -> VisibilityResult:
    """Fit a projected box to semantic vehicle pixels at the target depth."""

    if depth_m.shape[:2] != semantic_tags.shape[:2]:
        raise ValueError("Depth and semantic images must have equal dimensions")

    image_height, image_width = depth_m.shape[:2]
    x1 = max(0, int(math.floor(box.x1)))
    y1 = max(0, int(math.floor(box.y1)))
    x2 = min(image_width, int(math.ceil(box.x2)) + 1)
    y2 = min(image_height, int(math.ceil(box.y2)) + 1)
    depth_patch = depth_m[y1:y2, x1:x2]
    semantic_patch = semantic_tags[y1:y2, x1:x2]
    if depth_patch.size == 0:
        return VisibilityResult(0, 0, 0.0, None)

    tolerance = float(depth_tolerance_m)
    near_depth = max(0.0, box.min_depth_m - tolerance)
    far_depth = box.max_depth_m + tolerance
    depth_match = np.logical_and(
        depth_patch >= near_depth,
        depth_patch <= far_depth,
    )
    semantic_match = semantic_patch == int(vehicle_tag)
    visible_mask = np.logical_and(depth_match, semantic_match)
    visible_y, visible_x = np.nonzero(visible_mask)
    visible_pixels = int(visible_x.size)
    sampled_pixels = int(visible_mask.size)
    if visible_pixels == 0:
        return VisibilityResult(0, sampled_pixels, 0.0, None)

    padding = max(0, int(padding_px))
    fitted_x1 = max(0, x1 + int(np.min(visible_x)) - padding)
    fitted_y1 = max(0, y1 + int(np.min(visible_y)) - padding)
    fitted_x2 = min(
        image_width - 1,
        x1 + int(np.max(visible_x)) + padding,
    )
    fitted_y2 = min(
        image_height - 1,
        y1 + int(np.max(visible_y)) + padding,
    )
    fitted_box = ProjectedBox(
        x1=float(fitted_x1),
        y1=float(fitted_y1),
        x2=float(fitted_x2),
        y2=float(fitted_y2),
        min_depth_m=box.min_depth_m,
        max_depth_m=box.max_depth_m,
        truncation=box.truncation,
    )
    return VisibilityResult(
        visible_pixels=visible_pixels,
        sampled_pixels=sampled_pixels,
        visible_ratio=visible_pixels / float(sampled_pixels),
        fitted_box=fitted_box,
    )


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
