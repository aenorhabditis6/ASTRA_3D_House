"""Validated, serializable room-domain model."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .errors import ValidationError


@dataclass(frozen=True)
class Vec2:
    x: float
    y: float

    def distance_to(self, other: "Vec2") -> float:
        return math.hypot(other.x - self.x, other.y - self.y)

    def to_list(self) -> list[float]:
        return [self.x, self.y]

    @classmethod
    def from_value(cls, value: Any) -> "Vec2":
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValidationError(f"expected a 2D coordinate, got {value!r}")
        return cls(float(value[0]), float(value[1]))


@dataclass(frozen=True)
class Vec3:
    x: float
    y: float
    z: float

    def to_list(self) -> list[float]:
        return [self.x, self.y, self.z]

    @classmethod
    def from_value(cls, value: Any) -> "Vec3":
        if not isinstance(value, (list, tuple)) or len(value) != 3:
            raise ValidationError(f"expected a 3D coordinate, got {value!r}")
        return cls(float(value[0]), float(value[1]), float(value[2]))


@dataclass(frozen=True)
class SourceRef:
    kind: str
    reference: str
    confidence: float

    def validate(self) -> None:
        if not self.kind.strip():
            raise ValidationError("source kind must not be empty")
        if not self.reference.strip():
            raise ValidationError("source reference must not be empty")
        if not math.isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValidationError(
                f"source confidence must be in [0, 1], got {self.confidence}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "reference": self.reference,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "SourceRef":
        if not isinstance(data, dict):
            raise ValidationError(f"source must be an object, got {data!r}")
        try:
            source = cls(
                kind=str(data["kind"]),
                reference=str(data["reference"]),
                confidence=float(data["confidence"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValidationError(f"invalid source: {error}") from error
        source.validate()
        return source


@dataclass(frozen=True)
class Wall:
    id: str
    start: Vec2
    end: Vec2
    thickness_m: float
    geometry_source: SourceRef
    thickness_source: SourceRef

    @property
    def length_m(self) -> float:
        return self.start.distance_to(self.end)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "start": self.start.to_list(),
            "end": self.end.to_list(),
            "thickness_m": self.thickness_m,
            "geometry_source": self.geometry_source.to_dict(),
            "thickness_source": self.thickness_source.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Wall":
        return cls(
            id=str(data["id"]),
            start=Vec2.from_value(data["start"]),
            end=Vec2.from_value(data["end"]),
            thickness_m=float(data["thickness_m"]),
            geometry_source=SourceRef.from_dict(data["geometry_source"]),
            thickness_source=SourceRef.from_dict(data["thickness_source"]),
        )


@dataclass(frozen=True)
class Opening:
    id: str
    wall_id: str
    offset_m: float
    width_m: float
    sill_m: float
    height_m: float
    position_source: SourceRef
    vertical_source: SourceRef

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "wall_id": self.wall_id,
            "offset_m": self.offset_m,
            "width_m": self.width_m,
            "sill_m": self.sill_m,
            "height_m": self.height_m,
            "position_source": self.position_source.to_dict(),
            "vertical_source": self.vertical_source.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Opening":
        return cls(
            id=str(data["id"]),
            wall_id=str(data["wall_id"]),
            offset_m=float(data["offset_m"]),
            width_m=float(data["width_m"]),
            sill_m=float(data["sill_m"]),
            height_m=float(data["height_m"]),
            position_source=SourceRef.from_dict(data["position_source"]),
            vertical_source=SourceRef.from_dict(data["vertical_source"]),
        )


@dataclass(frozen=True)
class ProxyObject:
    id: str
    kind: str
    center: Vec3
    size: Vec3
    yaw_rad: float
    footprint_source: SourceRef
    height_source: SourceRef

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "center": self.center.to_list(),
            "size": self.size.to_list(),
            "yaw_rad": self.yaw_rad,
            "footprint_source": self.footprint_source.to_dict(),
            "height_source": self.height_source.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProxyObject":
        return cls(
            id=str(data["id"]),
            kind=str(data["kind"]),
            center=Vec3.from_value(data["center"]),
            size=Vec3.from_value(data["size"]),
            yaw_rad=float(data["yaw_rad"]),
            footprint_source=SourceRef.from_dict(data["footprint_source"]),
            height_source=SourceRef.from_dict(data["height_source"]),
        )


@dataclass(frozen=True)
class RoomModel:
    schema_version: str
    room_id: str
    units: str
    up_axis: str
    ceiling_height_m: float
    ceiling_height_source: SourceRef
    scale_source: SourceRef
    floor_polygon: tuple[Vec2, ...]
    walls: tuple[Wall, ...]
    openings: tuple[Opening, ...]
    proxies: tuple[ProxyObject, ...]
    provenance: tuple[SourceRef, ...]

    def validate(self) -> None:
        if self.schema_version != "1.0":
            raise ValidationError(
                f"unsupported room schema version {self.schema_version!r}"
            )
        if not self.room_id.strip():
            raise ValidationError("room_id must not be empty")
        if self.units != "meters":
            raise ValidationError(f"units must be 'meters', got {self.units!r}")
        if self.up_axis != "Z":
            raise ValidationError(f"up_axis must be 'Z', got {self.up_axis!r}")
        if not math.isfinite(self.ceiling_height_m) or self.ceiling_height_m <= 0:
            raise ValidationError("ceiling height must be positive")
        if len(self.floor_polygon) < 3 or abs(_polygon_area(self.floor_polygon)) < 1e-9:
            raise ValidationError("floor polygon must contain three non-collinear points")

        for source in self._all_sources():
            source.validate()
        _ensure_unique("wall", (wall.id for wall in self.walls))
        _ensure_unique("opening", (opening.id for opening in self.openings))
        _ensure_unique("proxy", (proxy.id for proxy in self.proxies))

        walls_by_id: dict[str, Wall] = {}
        for wall in self.walls:
            if not wall.id.strip():
                raise ValidationError("wall id must not be empty")
            if wall.length_m <= 1e-9:
                raise ValidationError(f"wall {wall.id!r} has zero length")
            if not math.isfinite(wall.thickness_m) or wall.thickness_m <= 0:
                raise ValidationError(f"wall {wall.id!r} thickness must be positive")
            walls_by_id[wall.id] = wall

        for opening in self.openings:
            wall = walls_by_id.get(opening.wall_id)
            if wall is None:
                raise ValidationError(
                    f"opening {opening.id!r} references missing wall {opening.wall_id!r}"
                )
            if opening.offset_m < 0 or opening.width_m <= 0:
                raise ValidationError(
                    f"opening {opening.id!r} on {opening.wall_id!r} has invalid horizontal dimensions"
                )
            if opening.offset_m + opening.width_m > wall.length_m + 1e-9:
                raise ValidationError(
                    f"opening {opening.id!r} does not fit wall {opening.wall_id!r}"
                )
            if opening.sill_m < 0 or opening.height_m <= 0:
                raise ValidationError(
                    f"opening {opening.id!r} has invalid vertical dimensions"
                )
            if opening.sill_m + opening.height_m > self.ceiling_height_m + 1e-9:
                raise ValidationError(
                    f"opening {opening.id!r} exceeds ceiling height"
                )

        for proxy in self.proxies:
            if not proxy.id.strip() or not proxy.kind.strip():
                raise ValidationError("proxy id and kind must not be empty")
            if any(
                not math.isfinite(value) or value <= 0
                for value in (proxy.size.x, proxy.size.y, proxy.size.z)
            ):
                raise ValidationError(f"proxy {proxy.id!r} size must be positive")
            if not math.isfinite(proxy.yaw_rad):
                raise ValidationError(f"proxy {proxy.id!r} yaw must be finite")

    def _all_sources(self) -> tuple[SourceRef, ...]:
        sources = [self.ceiling_height_source, self.scale_source, *self.provenance]
        for wall in self.walls:
            sources.extend((wall.geometry_source, wall.thickness_source))
        for opening in self.openings:
            sources.extend((opening.position_source, opening.vertical_source))
        for proxy in self.proxies:
            sources.extend((proxy.footprint_source, proxy.height_source))
        return tuple(sources)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "room_id": self.room_id,
            "coordinate_system": {"units": self.units, "up_axis": self.up_axis},
            "ceiling_height_m": self.ceiling_height_m,
            "ceiling_height_source": self.ceiling_height_source.to_dict(),
            "scale_source": self.scale_source.to_dict(),
            "floor_polygon": [point.to_list() for point in self.floor_polygon],
            "walls": [wall.to_dict() for wall in self.walls],
            "openings": [opening.to_dict() for opening in self.openings],
            "proxies": [proxy.to_dict() for proxy in self.proxies],
            "provenance": [source.to_dict() for source in self.provenance],
        }

    @classmethod
    def from_dict(cls, data: Any) -> "RoomModel":
        if not isinstance(data, dict):
            raise ValidationError("room document must be a JSON object")
        try:
            coordinate_system = data["coordinate_system"]
            room = cls(
                schema_version=str(data["schema_version"]),
                room_id=str(data["room_id"]),
                units=str(coordinate_system["units"]),
                up_axis=str(coordinate_system["up_axis"]),
                ceiling_height_m=float(data["ceiling_height_m"]),
                ceiling_height_source=SourceRef.from_dict(
                    data["ceiling_height_source"]
                ),
                scale_source=SourceRef.from_dict(data["scale_source"]),
                floor_polygon=tuple(
                    Vec2.from_value(point) for point in data["floor_polygon"]
                ),
                walls=tuple(Wall.from_dict(item) for item in data["walls"]),
                openings=tuple(
                    Opening.from_dict(item) for item in data["openings"]
                ),
                proxies=tuple(
                    ProxyObject.from_dict(item) for item in data["proxies"]
                ),
                provenance=tuple(
                    SourceRef.from_dict(item) for item in data["provenance"]
                ),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValidationError(f"invalid room document: {error}") from error
        room.validate()
        return room


def _polygon_area(points: tuple[Vec2, ...]) -> float:
    area = 0.0
    for start, end in zip(points, points[1:] + points[:1], strict=True):
        area += start.x * end.y - end.x * start.y
    return area / 2.0


def _ensure_unique(kind: str, values: Any) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValidationError(f"duplicate {kind} id {value!r}")
        seen.add(value)
