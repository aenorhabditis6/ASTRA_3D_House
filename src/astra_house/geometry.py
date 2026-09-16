"""Blender-independent geometry decomposition for logical rooms."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .errors import ValidationError
from .model import Opening, RoomModel, Vec3, Wall


@dataclass(frozen=True)
class BoxSpec:
    """An oriented rectangular solid in room coordinates."""

    id: str
    center: Vec3
    size: Vec3
    yaw_rad: float
    collection: str
    source_id: str


@dataclass(frozen=True)
class PolygonSpec:
    """A planar semantic polygon in room coordinates."""

    id: str
    vertices: tuple[Vec3, ...]
    collection: str
    source_id: str


def build_wall_boxes(room: RoomModel) -> tuple[BoxSpec, ...]:
    """Subtract rectangular apertures by decomposing walls into solid boxes."""
    room.validate()
    result: list[BoxSpec] = []
    openings_by_wall = _openings_by_wall(room)
    for wall in room.walls:
        openings = openings_by_wall[wall.id]
        intervals: list[tuple[float, float]] = []
        cursor = 0.0
        for opening in openings:
            if opening.offset_m < cursor - 1e-9:
                raise ValidationError(
                    f"openings overlap on wall {wall.id!r} near {opening.id!r}"
                )
            if opening.offset_m > cursor + 1e-9:
                intervals.append((cursor, opening.offset_m))
            cursor = opening.offset_m + opening.width_m
        if cursor < wall.length_m - 1e-9:
            intervals.append((cursor, wall.length_m))

        for index, (start, end) in enumerate(intervals):
            result.append(
                _wall_box(
                    wall=wall,
                    identifier=f"{wall.id}:span-{index:02d}",
                    along_start=start,
                    along_end=end,
                    bottom=0.0,
                    top=room.ceiling_height_m,
                    source_id=wall.id,
                )
            )

        for opening in openings:
            if opening.sill_m > 1e-9:
                result.append(
                    _wall_box(
                        wall=wall,
                        identifier=f"{wall.id}:{opening.id}:sill",
                        along_start=opening.offset_m,
                        along_end=opening.offset_m + opening.width_m,
                        bottom=0.0,
                        top=opening.sill_m,
                        source_id=opening.id,
                    )
                )
            header_bottom = opening.sill_m + opening.height_m
            if header_bottom < room.ceiling_height_m - 1e-9:
                result.append(
                    _wall_box(
                        wall=wall,
                        identifier=f"{wall.id}:{opening.id}:header",
                        along_start=opening.offset_m,
                        along_end=opening.offset_m + opening.width_m,
                        bottom=header_bottom,
                        top=room.ceiling_height_m,
                        source_id=opening.id,
                    )
                )
    return tuple(result)


def build_opening_boxes(room: RoomModel) -> tuple[BoxSpec, ...]:
    """Build thin, non-structural aperture placeholders for semantic review."""
    room.validate()
    walls = {wall.id: wall for wall in room.walls}
    result: list[BoxSpec] = []
    for opening in room.openings:
        wall = walls[opening.wall_id]
        along_center = opening.offset_m + opening.width_m / 2.0
        center_x, center_y, yaw = _wall_xy(wall, along_center)
        result.append(
            BoxSpec(
                id=opening.id,
                center=Vec3(
                    center_x,
                    center_y,
                    opening.sill_m + opening.height_m / 2.0,
                ),
                size=Vec3(opening.width_m, min(0.02, wall.thickness_m), opening.height_m),
                yaw_rad=yaw,
                collection="OPENINGS",
                source_id=opening.id,
            )
        )
    return tuple(result)


def build_floor_spec(room: RoomModel) -> PolygonSpec:
    room.validate()
    return PolygonSpec(
        id="floor",
        vertices=tuple(Vec3(point.x, point.y, 0.0) for point in room.floor_polygon),
        collection="STRUCTURE",
        source_id=room.room_id,
    )


def build_ceiling_spec(room: RoomModel) -> PolygonSpec:
    room.validate()
    return PolygonSpec(
        id="ceiling",
        vertices=tuple(
            Vec3(point.x, point.y, room.ceiling_height_m)
            for point in reversed(room.floor_polygon)
        ),
        collection="STRUCTURE",
        source_id=room.room_id,
    )


def _openings_by_wall(room: RoomModel) -> dict[str, list[Opening]]:
    result = {wall.id: [] for wall in room.walls}
    for opening in room.openings:
        result[opening.wall_id].append(opening)
    for openings in result.values():
        openings.sort(key=lambda item: (item.offset_m, item.id))
    return result


def _wall_xy(wall: Wall, distance: float) -> tuple[float, float, float]:
    dx = wall.end.x - wall.start.x
    dy = wall.end.y - wall.start.y
    length = wall.length_m
    unit_x = dx / length
    unit_y = dy / length
    return (
        wall.start.x + unit_x * distance,
        wall.start.y + unit_y * distance,
        math.atan2(dy, dx),
    )


def _wall_box(
    *,
    wall: Wall,
    identifier: str,
    along_start: float,
    along_end: float,
    bottom: float,
    top: float,
    source_id: str,
) -> BoxSpec:
    width = along_end - along_start
    height = top - bottom
    if width <= 0 or height <= 0:
        raise ValidationError(f"cannot create empty wall box {identifier!r}")
    center_x, center_y, yaw = _wall_xy(wall, (along_start + along_end) / 2.0)
    return BoxSpec(
        id=identifier,
        center=Vec3(center_x, center_y, (bottom + top) / 2.0),
        size=Vec3(width, wall.thickness_m, height),
        yaw_rad=yaw,
        collection="STRUCTURE",
        source_id=source_id,
    )
