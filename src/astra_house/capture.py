"""Validated capture plans for room-reconstruction photo batches."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from .errors import ValidationError
from .measurements import MeasurementSet
from .model import RoomModel, Vec2, Vec3


PITCH_RANGES = {
    "level": (-15.0, 10.0),
    "up": (15.0, 45.0),
    "down": (-45.0, -20.0),
}


@dataclass(frozen=True)
class DeviceProfile:
    make: str
    model: str
    lens: str
    orientation: str
    aspect_ratio: str
    file_format: str
    arcore_status: str
    equivalent_focal_length_mm: float
    horizontal_fov_deg: float
    vertical_fov_deg: float
    fov_source: str
    fov_confidence: float
    camera_height_m: float
    camera_height_tolerance_m: float
    coverage_margin_deg: float


@dataclass(frozen=True)
class WallReview:
    wall_id: str
    role: str
    opening_ids: tuple[str, ...]


@dataclass(frozen=True)
class ScaleAnchor:
    id: str
    target_id: str
    measurement_ids: tuple[str, ...]


@dataclass(frozen=True)
class CaptureStation:
    id: str
    number: int
    standing_point_m: Vec2
    label: str


@dataclass(frozen=True)
class CaptureShot:
    id: str
    aim_point_m: Vec2
    framing_points_m: tuple[Vec3, ...]
    pitch: str
    pitch_deg: float
    target_ids: tuple[str, ...]
    instruction: str


@dataclass(frozen=True)
class CaptureGroup:
    id: str
    title: str
    purpose: str
    station_id: str
    next_hint: str | None
    shots: tuple[CaptureShot, ...]


@dataclass(frozen=True)
class CapturePass:
    id: str
    title: str
    purpose: str
    groups: tuple[CaptureGroup, ...]

    @property
    def shots(self) -> tuple[CaptureShot, ...]:
        return tuple(shot for group in self.groups for shot in group.shots)


@dataclass(frozen=True)
class CaptureMode:
    id: str
    title: str
    description: str
    expected_image_count: int
    risk_note: str
    required_scale_anchor_ids: tuple[str, ...]
    passes: tuple[CapturePass, ...]

    @property
    def shots(self) -> tuple[CaptureShot, ...]:
        return tuple(
            shot
            for capture_pass in self.passes
            for group in capture_pass.groups
            for shot in group.shots
        )

    @property
    def groups(self) -> tuple[CaptureGroup, ...]:
        return tuple(
            group for capture_pass in self.passes for group in capture_pass.groups
        )


@dataclass(frozen=True)
class CoverageReview:
    mode_id: str
    mode_plan_sha256: str
    warning_codes: tuple[str, ...]
    reviewer: str
    reviewed_at: str


@dataclass(frozen=True)
class CapturePlan:
    schema_version: str
    room_id: str
    capture_id: str
    device_profile: DeviceProfile
    wall_review: tuple[WallReview, ...]
    scale_anchors: tuple[ScaleAnchor, ...]
    coverage_review: tuple[CoverageReview, ...]
    stations: tuple[CaptureStation, ...]
    modes: tuple[CaptureMode, ...]

    @property
    def passes(self) -> tuple[CapturePass, ...]:
        """Temporary schema-1 pack view, removed when the pack becomes mode-aware."""
        return self.mode("standard-48").passes

    @property
    def shots(self) -> tuple[CaptureShot, ...]:
        """Temporary schema-1 pack view of the standard route."""
        return self.mode("standard-48").shots

    @property
    def expected_image_count(self) -> int:
        """Temporary schema-1 pack count for the standard route."""
        return self.mode("standard-48").expected_image_count

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CapturePlan":
        """Parse a decoded schema-2 capture-plan document into immutable values."""
        schema_version = str(data.get("schema_version", ""))
        if schema_version != "2.0":
            raise ValidationError(
                f"unsupported capture-plan schema version {schema_version!r}"
            )
        try:
            device_data = data["device_profile"]
            device = DeviceProfile(
                make=str(device_data["make"]),
                model=str(device_data["model"]),
                lens=str(device_data["lens"]),
                orientation=str(device_data["orientation"]),
                aspect_ratio=str(device_data["aspect_ratio"]),
                file_format=str(device_data["file_format"]),
                arcore_status=str(device_data["arcore_status"]),
                equivalent_focal_length_mm=float(
                    device_data["equivalent_focal_length_mm"]
                ),
                horizontal_fov_deg=float(device_data["horizontal_fov_deg"]),
                vertical_fov_deg=float(device_data["vertical_fov_deg"]),
                fov_source=str(device_data["fov_source"]),
                fov_confidence=float(device_data["fov_confidence"]),
                camera_height_m=float(device_data["camera_height_m"]),
                camera_height_tolerance_m=float(
                    device_data["camera_height_tolerance_m"]
                ),
                coverage_margin_deg=float(device_data["coverage_margin_deg"]),
            )
            wall_review = tuple(
                WallReview(
                    wall_id=str(wall_id),
                    role=str(review["role"]),
                    opening_ids=tuple(str(item) for item in review["opening_ids"]),
                )
                for wall_id, review in data["wall_review"].items()
            )
            scale_anchors = tuple(
                ScaleAnchor(
                    id=str(anchor["id"]),
                    target_id=str(anchor["target_id"]),
                    measurement_ids=tuple(
                        str(item) for item in anchor["measurement_ids"]
                    ),
                )
                for anchor in data["scale_anchors"]
            )
            stations = tuple(
                CaptureStation(
                    id=str(station["id"]),
                    number=int(station["number"]),
                    standing_point_m=Vec2.from_value(station["standing_point_m"]),
                    label=str(station["label"]),
                )
                for station in data["stations"]
            )
            modes = tuple(_parse_mode(mode) for mode in data["modes"])
            coverage_review = tuple(
                CoverageReview(
                    mode_id=str(mode_id),
                    mode_plan_sha256=str(review["mode_plan_sha256"]),
                    warning_codes=tuple(
                        str(item) for item in review["warning_codes"]
                    ),
                    reviewer=str(review["reviewer"]),
                    reviewed_at=str(review["reviewed_at"]),
                )
                for mode_id, review in data.get("coverage_review", {}).items()
            )
            return cls(
                schema_version=schema_version,
                room_id=str(data["room_id"]),
                capture_id=str(data["capture_id"]),
                device_profile=device,
                wall_review=wall_review,
                scale_anchors=scale_anchors,
                coverage_review=coverage_review,
                stations=stations,
                modes=modes,
            )
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            raise ValidationError(f"invalid capture plan: {error}") from error

    def station(self, station_id: str) -> CaptureStation:
        for station in self.stations:
            if station.id == station_id:
                return station
        raise ValidationError(f"unknown station {station_id!r}")

    def mode(self, mode_id: str) -> CaptureMode:
        for mode in self.modes:
            if mode.id == mode_id:
                return mode
        raise ValidationError(f"unknown capture mode {mode_id!r}")

    def validate(self, room: RoomModel, measurements: MeasurementSet) -> None:
        """Raise when the plan is incomplete or disagrees with project sources."""
        if self.schema_version != "2.0":
            raise ValidationError(
                f"unsupported capture-plan schema version {self.schema_version!r}"
            )
        _require_text("room_id", self.room_id)
        _require_text("capture_id", self.capture_id)
        if self.room_id != room.room_id:
            raise ValidationError(
                f"capture room_id {self.room_id!r} does not match {room.room_id!r}"
            )
        if measurements.room_id != self.room_id:
            raise ValidationError(
                f"measurement room_id {measurements.room_id!r} does not match "
                f"{self.room_id!r}"
            )

        self._validate_device_profile()
        self._validate_wall_review(room)
        target_ids = {
            *(wall.id for wall in room.walls),
            *(opening.id for opening in room.openings),
            *(proxy.id for proxy in room.proxies),
        }
        self._validate_scale_anchors(target_ids, measurements)
        self._validate_stations(room)
        self._validate_modes(room, target_ids)
        self._validate_coverage_review()

    def _validate_device_profile(self) -> None:
        profile = self.device_profile
        for field_name in (
            "make", "model", "lens", "orientation", "aspect_ratio",
            "file_format", "arcore_status", "fov_source",
        ):
            _require_text(
                f"device_profile.{field_name}", getattr(profile, field_name)
            )
        if (
            not math.isfinite(profile.equivalent_focal_length_mm)
            or profile.equivalent_focal_length_mm <= 0
        ):
            raise ValidationError(
                "device_profile.equivalent_focal_length_mm must be positive and finite"
            )
        if (
            not math.isfinite(profile.coverage_margin_deg)
            or not math.isfinite(profile.horizontal_fov_deg)
            or not 0 < profile.coverage_margin_deg * 2 < profile.horizontal_fov_deg < 180
        ):
            raise ValidationError(
                "device_profile.horizontal_fov_deg must be finite, below 180, "
                "and greater than twice coverage_margin_deg"
            )
        if (
            not math.isfinite(profile.vertical_fov_deg)
            or not 0 < profile.vertical_fov_deg < 180
        ):
            raise ValidationError(
                "device_profile.vertical_fov_deg must be between 0 and 180"
            )
        if (
            not math.isfinite(profile.camera_height_m)
            or profile.camera_height_m <= 0
            or not math.isfinite(profile.camera_height_tolerance_m)
            or profile.camera_height_tolerance_m <= 0
        ):
            raise ValidationError(
                "device profile camera height and tolerance must be positive and finite"
            )
        if (
            not math.isfinite(profile.fov_confidence)
            or not 0 <= profile.fov_confidence <= 1
        ):
            raise ValidationError("device_profile.fov_confidence must be in [0, 1]")

    def _validate_scale_anchors(
        self, target_ids: set[str], measurements: MeasurementSet
    ) -> None:
        _ensure_unique("scale anchor", (anchor.id for anchor in self.scale_anchors))
        measurement_by_id = {
            record.id: record for record in measurements.measurements
        }
        for anchor in self.scale_anchors:
            _require_text("scale anchor id", anchor.id)
            _require_text(f"scale anchor {anchor.id!r} target_id", anchor.target_id)
            if anchor.target_id not in target_ids:
                raise ValidationError(
                    f"scale anchor {anchor.id!r} references unknown target "
                    f"{anchor.target_id!r}"
                )
            if not anchor.measurement_ids:
                raise ValidationError(
                    f"scale anchor {anchor.id!r} has no measurement IDs"
                )
            _ensure_unique(
                f"measurement in scale anchor {anchor.id!r}", anchor.measurement_ids
            )
            for measurement_id in anchor.measurement_ids:
                record = measurement_by_id.get(measurement_id)
                if record is None:
                    raise ValidationError(
                        f"scale anchor {anchor.id!r} references unknown measurement "
                        f"{measurement_id!r}"
                    )
                if record.target_id != anchor.target_id:
                    raise ValidationError(
                        f"measurement {measurement_id!r} targets {record.target_id!r}, "
                        f"not scale anchor target {anchor.target_id!r}"
                    )
                if record.application != "exact_override":
                    raise ValidationError(
                        f"measurement {measurement_id!r} must use exact_override"
                    )
                if not math.isfinite(record.value_m) or record.value_m <= 0:
                    raise ValidationError(
                        f"measurement {measurement_id!r} must be positive and finite"
                    )

    def _validate_stations(self, room: RoomModel) -> None:
        if not self.stations:
            raise ValidationError("capture plan must contain at least one station")
        _ensure_unique("station", (station.id for station in self.stations))
        seen_numbers: set[int] = set()
        for station in self.stations:
            _require_text("station id", station.id)
            _require_text(f"station {station.id!r} label", station.label)
            if station.number <= 0:
                raise ValidationError(
                    f"station {station.id!r} number must be positive"
                )
            if station.number in seen_numbers:
                raise ValidationError(
                    f"duplicate station number {station.number}"
                )
            seen_numbers.add(station.number)
            if not _point_strictly_in_polygon(
                station.standing_point_m, room.floor_polygon
            ):
                raise ValidationError(
                    f"station {station.id!r} must be strictly inside floor polygon"
                )

    def _validate_modes(self, room: RoomModel, target_ids: set[str]) -> None:
        if not self.modes:
            raise ValidationError("capture plan must contain at least one mode")
        _ensure_unique("mode", (mode.id for mode in self.modes))
        anchor_ids = {anchor.id for anchor in self.scale_anchors}
        station_ids = {station.id for station in self.stations}
        all_shot_ids: list[str] = []
        for mode in self.modes:
            _require_text("mode id", mode.id)
            _require_text(f"mode {mode.id!r} title", mode.title)
            _require_text(f"mode {mode.id!r} description", mode.description)
            _require_text(f"mode {mode.id!r} risk_note", mode.risk_note)
            if mode.expected_image_count <= 0:
                raise ValidationError(
                    f"mode {mode.id!r} expected_image_count must be positive"
                )
            _ensure_unique(
                f"required scale anchor in mode {mode.id!r}",
                mode.required_scale_anchor_ids,
            )
            for anchor_id in mode.required_scale_anchor_ids:
                if anchor_id not in anchor_ids:
                    raise ValidationError(
                        f"mode {mode.id!r} references unknown scale anchor "
                        f"{anchor_id!r}"
                    )
            if not mode.passes:
                raise ValidationError(f"mode {mode.id!r} has no capture passes")
            _ensure_unique("capture pass", (item.id for item in mode.passes))
            _ensure_unique("capture group", (group.id for group in mode.groups))
            for capture_pass in mode.passes:
                _require_text("capture pass id", capture_pass.id)
                _require_text(
                    f"capture pass {capture_pass.id!r} title", capture_pass.title
                )
                _require_text(
                    f"capture pass {capture_pass.id!r} purpose", capture_pass.purpose
                )
                if not capture_pass.groups:
                    raise ValidationError(
                        f"capture pass {capture_pass.id!r} has no groups"
                    )
                for group in capture_pass.groups:
                    _require_text("capture group id", group.id)
                    _require_text(f"capture group {group.id!r} title", group.title)
                    _require_text(
                        f"capture group {group.id!r} purpose", group.purpose
                    )
                    if group.next_hint is not None:
                        _require_text(
                            f"capture group {group.id!r} next_hint", group.next_hint
                        )
                    if group.station_id not in station_ids:
                        raise ValidationError(
                            f"capture group {group.id!r} references unknown station "
                            f"{group.station_id!r}"
                        )
                    if not group.shots:
                        raise ValidationError(
                            f"capture group {group.id!r} has no shots"
                        )
                    station = self.station(group.station_id)
                    for shot in group.shots:
                        self._validate_shot(shot, station, room, target_ids)
                        all_shot_ids.append(shot.id)
            actual_count = len(mode.shots)
            if actual_count != mode.expected_image_count:
                raise ValidationError(
                    f"mode {mode.id!r} expected {mode.expected_image_count} shots, "
                    f"found {actual_count}"
                )
        _ensure_unique("shot", all_shot_ids)

    def _validate_shot(
        self,
        shot: CaptureShot,
        station: CaptureStation,
        room: RoomModel,
        target_ids: set[str],
    ) -> None:
        _require_text("shot id", shot.id)
        _require_text(f"shot {shot.id!r} instruction", shot.instruction)
        _validate_pitch(shot)
        if not shot.target_ids:
            raise ValidationError(f"shot {shot.id!r} has no target IDs")
        _ensure_unique(f"target in shot {shot.id!r}", shot.target_ids)
        for target_id in shot.target_ids:
            if target_id not in target_ids:
                raise ValidationError(
                    f"shot {shot.id!r} references unknown target {target_id!r}"
                )
        if not _point_in_or_on_polygon(shot.aim_point_m, room.floor_polygon):
            raise ValidationError(
                f"shot {shot.id!r} aim point is outside floor polygon"
            )
        aim_distance_m = _quantize_length_m(
            station.standing_point_m.distance_to(shot.aim_point_m)
        )
        if aim_distance_m < 0.50:
            raise ValidationError(
                f"shot {shot.id!r} aim point must be at least 0.50 m from station"
            )
        if not shot.framing_points_m:
            raise ValidationError(f"shot {shot.id!r} has no framing points")
        for point in shot.framing_points_m:
            if not all(math.isfinite(value) for value in (point.x, point.y, point.z)):
                raise ValidationError(
                    f"shot {shot.id!r} has a non-finite framing point"
                )

    def _validate_coverage_review(self) -> None:
        _ensure_unique(
            "coverage review mode", (review.mode_id for review in self.coverage_review)
        )
        mode_ids = {mode.id for mode in self.modes}
        for review in self.coverage_review:
            if review.mode_id not in mode_ids:
                raise ValidationError(
                    f"coverage review references unknown mode {review.mode_id!r}"
                )
            if (
                len(review.mode_plan_sha256) != 64
                or any(character not in "0123456789abcdef" for character in review.mode_plan_sha256)
            ):
                raise ValidationError(
                    f"coverage review for {review.mode_id!r} has invalid SHA-256"
                )
            _ensure_unique(
                f"warning code in coverage review {review.mode_id!r}",
                review.warning_codes,
            )
            for warning_code in review.warning_codes:
                _require_text(
                    f"coverage review {review.mode_id!r} warning code", warning_code
                )
            _require_text(
                f"coverage review {review.mode_id!r} reviewer", review.reviewer
            )
            _require_text(
                f"coverage review {review.mode_id!r} reviewed_at", review.reviewed_at
            )

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


def _parse_mode(data: dict[str, Any]) -> CaptureMode:
    return CaptureMode(
        id=str(data["id"]),
        title=str(data["title"]),
        description=str(data["description"]),
        expected_image_count=int(data["expected_image_count"]),
        risk_note=str(data["risk_note"]),
        required_scale_anchor_ids=tuple(
            str(item) for item in data["required_scale_anchor_ids"]
        ),
        passes=tuple(_parse_pass(item) for item in data["passes"]),
    )


def _parse_pass(data: dict[str, Any]) -> CapturePass:
    return CapturePass(
        id=str(data["id"]),
        title=str(data["title"]),
        purpose=str(data["purpose"]),
        groups=tuple(_parse_group(item) for item in data["groups"]),
    )


def _parse_group(data: dict[str, Any]) -> CaptureGroup:
    next_hint = data.get("next_hint")
    return CaptureGroup(
        id=str(data["id"]),
        title=str(data["title"]),
        purpose=str(data["purpose"]),
        station_id=str(data["station_id"]),
        next_hint=None if next_hint is None else str(next_hint),
        shots=tuple(_parse_shot(item) for item in data["shots"]),
    )


def _parse_shot(data: dict[str, Any]) -> CaptureShot:
    return CaptureShot(
        id=str(data["id"]),
        aim_point_m=Vec2.from_value(data["aim_point_m"]),
        framing_points_m=tuple(
            Vec3.from_value(item) for item in data["framing_points_m"]
        ),
        pitch=str(data["pitch"]),
        pitch_deg=float(data["pitch_deg"]),
        target_ids=tuple(str(item) for item in data["target_ids"]),
        instruction=str(data["instruction"]),
    )


def _validate_pitch(shot: CaptureShot) -> None:
    bounds = PITCH_RANGES.get(shot.pitch)
    if bounds is None:
        raise ValidationError(
            f"shot {shot.id!r} has unsupported pitch {shot.pitch!r}"
        )
    if (
        not math.isfinite(shot.pitch_deg)
        or not bounds[0] <= shot.pitch_deg <= bounds[1]
    ):
        raise ValidationError(
            f"shot {shot.id!r} pitch_deg {shot.pitch_deg!r} "
            f"disagrees with {shot.pitch!r}"
        )


def _quantize_length_m(value: float) -> float:
    """Quantize a derived length to the capture geometry decision precision."""
    return float(
        Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    )


def _require_text(label: str, value: str) -> None:
    if not value.strip():
        raise ValidationError(f"{label} must not be empty")


def _ensure_unique(kind: str, values: Any) -> None:
    seen: set[Any] = set()
    for value in values:
        if value in seen:
            raise ValidationError(f"duplicate {kind} id {value!r}")
        seen.add(value)


def _point_strictly_in_polygon(point: Vec2, polygon: tuple[Vec2, ...]) -> bool:
    if not math.isfinite(point.x) or not math.isfinite(point.y):
        return False
    if any(
        _point_on_segment(point, start, end)
        for start, end in zip(polygon, polygon[1:] + polygon[:1], strict=True)
    ):
        return False
    return _point_in_or_on_polygon(point, polygon)


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
    # Source capture geometry is intentionally committed at 1e-4 m.  Keep
    # boundary checks tolerant of the corresponding coordinate/cross-product
    # rounding while station points remain far enough from walls to be strict.
    epsilon = 1e-3
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
