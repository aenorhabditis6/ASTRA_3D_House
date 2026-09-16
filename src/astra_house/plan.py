"""Validated source-space annotations and pixel-to-room calibration."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .errors import ValidationError
from .model import Vec2

SCHEMA_VERSION = "1.0"
EDGE_TOLERANCE_PX = 2.0


@dataclass(frozen=True)
class ImageSpec:
    path: str
    width_px: int
    height_px: int


@dataclass(frozen=True)
class TargetSpec:
    room_id: str
    origin_px: Vec2
    floor_polygon_px: tuple[Vec2, ...]
    ceiling_height_m: float
    wall_thickness_m: float


@dataclass(frozen=True)
class ScaleAnchor:
    id: str
    bbox_px: tuple[float, float, float, float]
    size_m: Vec2
    fit: str
    source: str


@dataclass(frozen=True)
class AnnotatedOpening:
    id: str
    edge_index: int
    start_px: Vec2
    end_px: Vec2
    sill_m: float
    height_m: float
    confidence: float


@dataclass(frozen=True)
class AnnotatedObject:
    id: str
    kind: str
    bbox_px: tuple[float, float, float, float]
    height_m: float


@dataclass(frozen=True)
class PlanAnnotation:
    schema_version: str
    image: ImageSpec
    target: TargetSpec
    scale_anchor: ScaleAnchor
    openings: tuple[AnnotatedOpening, ...]
    objects: tuple[AnnotatedObject, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlanAnnotation":
        """Parse and fully validate an annotation JSON object."""
        if not isinstance(data, dict):
            raise ValidationError("plan annotation must be an object")
        try:
            image_data = data["image"]
            target_data = data["target"]
            anchor_data = data["scale_anchor"]
            image = ImageSpec(
                path=str(image_data["path"]),
                width_px=_integer(image_data["width_px"], "image width"),
                height_px=_integer(image_data["height_px"], "image height"),
            )
            target = TargetSpec(
                room_id=str(target_data["room_id"]),
                origin_px=Vec2.from_value(target_data["origin_px"]),
                floor_polygon_px=tuple(
                    Vec2.from_value(point)
                    for point in target_data["floor_polygon_px"]
                ),
                ceiling_height_m=float(target_data["ceiling_height_m"]),
                wall_thickness_m=float(target_data["wall_thickness_m"]),
            )
            anchor = ScaleAnchor(
                id=str(anchor_data["id"]),
                bbox_px=_bbox(anchor_data["bbox_px"], "scale anchor"),
                size_m=Vec2.from_value(anchor_data["size_m"]),
                fit=str(anchor_data["fit"]),
                source=str(anchor_data["source"]),
            )
            openings = tuple(
                AnnotatedOpening(
                    id=str(item["id"]),
                    edge_index=_integer(item["edge_index"], "opening edge_index"),
                    start_px=Vec2.from_value(item["start_px"]),
                    end_px=Vec2.from_value(item["end_px"]),
                    sill_m=float(item["sill_m"]),
                    height_m=float(item["height_m"]),
                    confidence=float(item["confidence"]),
                )
                for item in data["openings"]
            )
            objects = tuple(
                AnnotatedObject(
                    id=str(item["id"]),
                    kind=str(item["kind"]),
                    bbox_px=_bbox(item["bbox_px"], f"object {item.get('id', '')}"),
                    height_m=float(item["height_m"]),
                )
                for item in data["objects"]
            )
            annotation = cls(
                schema_version=str(data["schema_version"]),
                image=image,
                target=target,
                scale_anchor=anchor,
                openings=openings,
                objects=objects,
            )
        except ValidationError:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise ValidationError(f"invalid plan annotation: {error}") from error
        annotation.validate()
        return annotation

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValidationError(
                f"unsupported plan annotation schema_version {self.schema_version!r}"
            )
        if not self.image.path or self.image.width_px <= 0 or self.image.height_px <= 0:
            raise ValidationError("image path and dimensions must be positive")
        if not self.target.room_id:
            raise ValidationError("target room_id must not be empty")
        if len(self.target.floor_polygon_px) < 3:
            raise ValidationError("target floor polygon requires at least three points")
        if self.target.ceiling_height_m <= 0 or self.target.wall_thickness_m <= 0:
            raise ValidationError("room height and wall thickness must be positive")
        for point in (self.target.origin_px, *self.target.floor_polygon_px):
            self._validate_image_point(point)

        if self.scale_anchor.fit != "isotropic_least_squares":
            raise ValidationError(f"unsupported scale fit {self.scale_anchor.fit!r}")
        self._validate_bbox(self.scale_anchor.bbox_px, "scale anchor")
        if self.scale_anchor.size_m.x <= 0 or self.scale_anchor.size_m.y <= 0:
            raise ValidationError("scale anchor metric dimensions must be positive")

        opening_ids: set[str] = set()
        for opening in self.openings:
            if opening.id in opening_ids:
                raise ValidationError(f"duplicate opening id {opening.id!r}")
            opening_ids.add(opening.id)
            if not 0 <= opening.edge_index < len(self.target.floor_polygon_px):
                raise ValidationError(
                    f"opening {opening.id!r} has invalid edge index {opening.edge_index}"
                )
            if opening.sill_m < 0 or opening.height_m <= 0:
                raise ValidationError(f"opening {opening.id!r} dimensions are invalid")
            if not 0 <= opening.confidence <= 1:
                raise ValidationError(f"opening {opening.id!r} confidence is invalid")
            self._validate_image_point(opening.start_px)
            self._validate_image_point(opening.end_px)
            edge_start = self.target.floor_polygon_px[opening.edge_index]
            edge_end = self.target.floor_polygon_px[
                (opening.edge_index + 1) % len(self.target.floor_polygon_px)
            ]
            for endpoint in (opening.start_px, opening.end_px):
                if _distance_to_segment(endpoint, edge_start, edge_end) > EDGE_TOLERANCE_PX:
                    raise ValidationError(
                        f"opening {opening.id!r} endpoint is not on edge {opening.edge_index}"
                    )

        min_x = min(point.x for point in self.target.floor_polygon_px)
        max_x = max(point.x for point in self.target.floor_polygon_px)
        min_y = min(point.y for point in self.target.floor_polygon_px)
        max_y = max(point.y for point in self.target.floor_polygon_px)
        object_ids: set[str] = set()
        for item in self.objects:
            if item.id in object_ids:
                raise ValidationError(f"duplicate object id {item.id!r}")
            object_ids.add(item.id)
            if not item.id or not item.kind or item.height_m <= 0:
                raise ValidationError(f"object {item.id!r} fields are invalid")
            self._validate_bbox(item.bbox_px, f"object {item.id}")
            left, top, right, bottom = item.bbox_px
            if left < min_x or right > max_x or top < min_y or bottom > max_y:
                raise ValidationError(
                    f"object {item.id!r} box is outside target bounding extent"
                )

    def _validate_image_point(self, point: Vec2) -> None:
        if (
            not math.isfinite(point.x)
            or not math.isfinite(point.y)
            or point.x < 0
            or point.x > self.image.width_px
            or point.y < 0
            or point.y > self.image.height_px
        ):
            raise ValidationError(f"point {point} is outside image bounds")

    def _validate_bbox(
        self, bbox: tuple[float, float, float, float], label: str
    ) -> None:
        left, top, right, bottom = bbox
        if left >= right or top >= bottom:
            raise ValidationError(f"{label} box must have positive width and height")
        self._validate_image_point(Vec2(left, top))
        self._validate_image_point(Vec2(right, bottom))


@dataclass(frozen=True)
class PlanCalibration:
    origin_px: Vec2
    meters_per_pixel: float

    @classmethod
    def from_annotation(cls, annotation: PlanAnnotation) -> "PlanCalibration":
        annotation.validate()
        left, top, right, bottom = annotation.scale_anchor.bbox_px
        width_px = right - left
        height_px = bottom - top
        size = annotation.scale_anchor.size_m
        scale = (width_px * size.x + height_px * size.y) / (
            width_px * width_px + height_px * height_px
        )
        if not math.isfinite(scale) or scale <= 0:
            raise ValidationError("calculated plan scale is invalid")
        return cls(annotation.target.origin_px, scale)

    def pixel_to_room(self, point: Vec2) -> Vec2:
        return Vec2(
            (point.x - self.origin_px.x) * self.meters_per_pixel,
            (self.origin_px.y - point.y) * self.meters_per_pixel,
        )

    def room_to_pixel(self, point: Vec2) -> Vec2:
        return Vec2(
            point.x / self.meters_per_pixel + self.origin_px.x,
            self.origin_px.y - point.y / self.meters_per_pixel,
        )


def _integer(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{label} must be an integer")
    return value


def _bbox(value: object, label: str) -> tuple[float, float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValidationError(f"{label} bbox must contain four coordinates")
    try:
        result = tuple(float(coordinate) for coordinate in value)
    except (TypeError, ValueError) as error:
        raise ValidationError(f"{label} bbox coordinates must be numbers") from error
    if not all(math.isfinite(coordinate) for coordinate in result):
        raise ValidationError(f"{label} bbox coordinates must be finite")
    return result  # type: ignore[return-value]


def _distance_to_segment(point: Vec2, start: Vec2, end: Vec2) -> float:
    dx = end.x - start.x
    dy = end.y - start.y
    squared_length = dx * dx + dy * dy
    if squared_length == 0:
        return point.distance_to(start)
    fraction = ((point.x - start.x) * dx + (point.y - start.y) * dy) / squared_length
    fraction = min(1.0, max(0.0, fraction))
    closest = Vec2(start.x + fraction * dx, start.y + fraction * dy)
    return point.distance_to(closest)
