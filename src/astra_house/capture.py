"""Validated capture plans for room-reconstruction photo batches."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .errors import ValidationError
from .model import RoomModel, Vec2


@dataclass(frozen=True)
class DeviceProfile:
    make: str
    model: str
    lens: str
    orientation: str
    aspect_ratio: str
    file_format: str
    arcore_status: str


@dataclass(frozen=True)
class WallReview:
    wall_id: str
    role: str
    opening_ids: tuple[str, ...]


@dataclass(frozen=True)
class CaptureShot:
    id: str
    standing_point_m: Vec2
    pitch: str
    target_ids: tuple[str, ...]
    instruction: str


@dataclass(frozen=True)
class CapturePass:
    id: str
    title: str
    purpose: str
    shots: tuple[CaptureShot, ...]


@dataclass(frozen=True)
class CapturePlan:
    schema_version: str
    room_id: str
    capture_id: str
    expected_image_count: int
    device_profile: DeviceProfile
    wall_review: tuple[WallReview, ...]
    passes: tuple[CapturePass, ...]

    @property
    def shots(self) -> tuple[CaptureShot, ...]:
        return tuple(shot for item in self.passes for shot in item.shots)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CapturePlan":
        """Parse a decoded capture-plan document into immutable values."""
        try:
            device_data = data["device_profile"]
            wall_data = data["wall_review"]
            device = DeviceProfile(
                make=str(device_data["make"]),
                model=str(device_data["model"]),
                lens=str(device_data["lens"]),
                orientation=str(device_data["orientation"]),
                aspect_ratio=str(device_data["aspect_ratio"]),
                file_format=str(device_data["file_format"]),
                arcore_status=str(device_data["arcore_status"]),
            )
            wall_review = tuple(
                WallReview(
                    wall_id=str(wall_id),
                    role=str(review["role"]),
                    opening_ids=tuple(str(item) for item in review["opening_ids"]),
                )
                for wall_id, review in wall_data.items()
            )
            passes = tuple(
                CapturePass(
                    id=str(pass_data["id"]),
                    title=str(pass_data["title"]),
                    purpose=str(pass_data["purpose"]),
                    shots=tuple(
                        CaptureShot(
                            id=str(shot_data["id"]),
                            standing_point_m=Vec2.from_value(
                                shot_data["standing_point_m"]
                            ),
                            pitch=str(shot_data["pitch"]),
                            target_ids=tuple(
                                str(item) for item in shot_data["target_ids"]
                            ),
                            instruction=str(shot_data["instruction"]),
                        )
                        for shot_data in pass_data["shots"]
                    ),
                )
                for pass_data in data["passes"]
            )
            return cls(
                schema_version=str(data["schema_version"]),
                room_id=str(data["room_id"]),
                capture_id=str(data["capture_id"]),
                expected_image_count=int(data["expected_image_count"]),
                device_profile=device,
                wall_review=wall_review,
                passes=passes,
            )
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            raise ValidationError(f"invalid capture plan: {error}") from error

    def validate(self, room: RoomModel) -> None:
        """Raise when the plan is incomplete or disagrees with room structure."""
        if self.schema_version != "1.0":
            raise ValidationError(
                f"unsupported capture-plan schema version {self.schema_version!r}"
            )
        _require_text("room_id", self.room_id)
        _require_text("capture_id", self.capture_id)
        if self.room_id != room.room_id:
            raise ValidationError(
                f"capture room_id {self.room_id!r} does not match {room.room_id!r}"
            )
        if self.expected_image_count <= 0:
            raise ValidationError("expected_image_count must be positive")

        for field_name, value in vars(self.device_profile).items():
            _require_text(f"device_profile.{field_name}", value)

        _ensure_unique("capture pass", (item.id for item in self.passes))
        if not self.passes:
            raise ValidationError("capture plan must contain at least one pass")
        allowed_pitch = {"level", "up", "down"}
        target_ids = {
            *(wall.id for wall in room.walls),
            *(opening.id for opening in room.openings),
            *(proxy.id for proxy in room.proxies),
        }
        for item in self.passes:
            _require_text("capture pass id", item.id)
            _require_text(f"capture pass {item.id!r} title", item.title)
            _require_text(f"capture pass {item.id!r} purpose", item.purpose)
            if not item.shots:
                raise ValidationError(f"capture pass {item.id!r} has no shots")
            for shot in item.shots:
                _require_text("shot id", shot.id)
                _require_text(f"shot {shot.id!r} instruction", shot.instruction)
                if shot.pitch not in allowed_pitch:
                    raise ValidationError(
                        f"shot {shot.id!r} has unsupported pitch {shot.pitch!r}"
                    )
                if not shot.target_ids:
                    raise ValidationError(f"shot {shot.id!r} has no target IDs")
                unknown = [target for target in shot.target_ids if target not in target_ids]
                if unknown:
                    raise ValidationError(
                        f"shot {shot.id!r} references unknown target {unknown[0]!r}"
                    )
                if not _point_in_or_on_polygon(shot.standing_point_m, room.floor_polygon):
                    raise ValidationError(
                        f"shot {shot.id!r} standing point is outside floor polygon"
                    )

        _ensure_unique("shot", (shot.id for shot in self.shots))
        actual_count = len(self.shots)
        if actual_count != self.expected_image_count:
            raise ValidationError(
                f"expected {self.expected_image_count} shots, found {actual_count}"
            )

        self._validate_wall_review(room)

    def _validate_wall_review(self, room: RoomModel) -> None:
        _ensure_unique("wall review", (review.wall_id for review in self.wall_review))
        room_wall_ids = {wall.id for wall in room.walls}
        reviewed_wall_ids = {review.wall_id for review in self.wall_review}
        missing = sorted(room_wall_ids - reviewed_wall_ids)
        extra = sorted(reviewed_wall_ids - room_wall_ids)
        if missing or extra:
            raise ValidationError(
                f"wall review coverage mismatch; missing={missing}, extra={extra}"
            )

        opening_owners = {opening.id: opening.wall_id for opening in room.openings}
        reviewed_openings: list[str] = []
        for review in self.wall_review:
            _require_text(f"wall review {review.wall_id!r} role", review.role)
            _ensure_unique(
                f"opening in wall review {review.wall_id!r}", review.opening_ids
            )
            for opening_id in review.opening_ids:
                actual_wall_id = opening_owners.get(opening_id)
                if actual_wall_id is None:
                    raise ValidationError(
                        f"wall review references unknown opening {opening_id!r}"
                    )
                if actual_wall_id != review.wall_id:
                    raise ValidationError(
                        f"opening {opening_id} is reviewed under {review.wall_id} "
                        f"but belongs to {actual_wall_id}"
                    )
                reviewed_openings.append(opening_id)

        _ensure_unique("reviewed opening", reviewed_openings)
        missing_openings = sorted(set(opening_owners) - set(reviewed_openings))
        if missing_openings:
            raise ValidationError(
                f"wall review is missing openings {missing_openings}"
            )


def _require_text(label: str, value: str) -> None:
    if not value.strip():
        raise ValidationError(f"{label} must not be empty")


def _ensure_unique(kind: str, values: Any) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValidationError(f"duplicate {kind} id {value!r}")
        seen.add(value)


def _point_in_or_on_polygon(point: Vec2, polygon: tuple[Vec2, ...]) -> bool:
    """Return true for points inside the polygon or on any boundary segment."""
    if not math.isfinite(point.x) or not math.isfinite(point.y):
        return False

    inside = False
    for start, end in zip(polygon, polygon[1:] + polygon[:1], strict=True):
        if _point_on_segment(point, start, end):
            return True
        crosses = (start.y > point.y) != (end.y > point.y)
        if crosses:
            intersection_x = start.x + (
                (point.y - start.y) * (end.x - start.x) / (end.y - start.y)
            )
            if point.x < intersection_x:
                inside = not inside
    return inside


def _point_on_segment(point: Vec2, start: Vec2, end: Vec2) -> bool:
    epsilon = 1e-9
    cross = (point.x - start.x) * (end.y - start.y) - (
        point.y - start.y
    ) * (end.x - start.x)
    if abs(cross) > epsilon:
        return False
    return (
        min(start.x, end.x) - epsilon <= point.x <= max(start.x, end.x) + epsilon
        and min(start.y, end.y) - epsilon
        <= point.y
        <= max(start.y, end.y) + epsilon
    )
