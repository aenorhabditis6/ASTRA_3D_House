"""Deterministic capture-route coverage geometry and diagnostics."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP

from .capture import (
    CaptureMode,
    CapturePlan,
    CaptureShot,
    _framing_point_belongs_to_target,
)
from .errors import ValidationError
from .model import ProxyObject, RoomModel, Vec2, Vec3, Wall


METER_QUANTUM = Decimal("0.0001")
ANGLE_QUANTUM = Decimal("0.01")
GEOMETRY_TOLERANCE_M = 0.01
MIN_ANCHOR_BASELINE_M = 0.50
MIN_ADJACENT_SHARED_SPAN_M = 0.50
MIN_STATION_CLEARANCE_M = 0.30
MIN_BOUNDARY_RAY_M = 1.0
MIN_VERTICAL_OVERLAP = 0.30


@dataclass(frozen=True)
class CoverageIssue:
    code: str
    severity: str
    mode_id: str
    subject_id: str
    message: str


@dataclass(frozen=True)
class ShotCoverage:
    shot_id: str
    station_id: str
    bearing_deg: float
    boundary_hit_m: Vec2
    boundary_distance_m: float
    usable_horizontal_fov_deg: float
    horizontal_span_deg: float
    vertical_interval_deg: tuple[float, float]
    visible_target_ids: tuple[str, ...]
    cone_polygon_m: tuple[Vec2, ...]


@dataclass(frozen=True)
class ModeCoverage:
    mode_id: str
    mode_plan_sha256: str
    shots: tuple[ShotCoverage, ...]
    adjacent_shared_spans_m: tuple[tuple[str, str, float], ...]
    wall_station_baselines_m: tuple[tuple[str, int, float], ...]
    anchor_station_baselines_m: tuple[tuple[str, int, float], ...]
    issues: tuple[CoverageIssue, ...]
    floor_seam_spans_m: tuple[tuple[str, float], ...] = ()
    ceiling_seam_spans_m: tuple[tuple[str, float], ...] = ()


def quantize_m(value: float) -> float:
    return float(
        Decimal(str(value)).quantize(METER_QUANTUM, rounding=ROUND_HALF_UP)
    )


def quantize_deg(value: float) -> float:
    return float(
        Decimal(str(value)).quantize(ANGLE_QUANTUM, rounding=ROUND_HALF_UP)
    )


def relative_bearing_deg(origin: Vec2, aim: Vec2, point: Vec2) -> float:
    axis = math.degrees(math.atan2(aim.y - origin.y, aim.x - origin.x))
    bearing = math.degrees(math.atan2(point.y - origin.y, point.x - origin.x))
    return (bearing - axis + 180.0) % 360.0 - 180.0


def point_strictly_inside_polygon(
    point: Vec2,
    polygon: tuple[Vec2, ...],
    tolerance_m: float = GEOMETRY_TOLERANCE_M,
) -> bool:
    if not _point_in_or_on_polygon(point, polygon):
        return False
    return all(
        quantize_m(_distance_to_segment(point, start, end)) > tolerance_m
        for start, end in _polygon_edges(polygon)
    )


def segment_inside_polygon(
    start: Vec2, end: Vec2, polygon: tuple[Vec2, ...]
) -> bool:
    """Return whether every open subsegment is inside or on the polygon."""
    if not _point_in_or_on_polygon(start, polygon) or not _point_in_or_on_polygon(
        end, polygon
    ):
        return False
    parameters = [0.0, 1.0]
    for edge_start, edge_end in _polygon_edges(polygon):
        intersections = _segment_edge_intersection_parameters(
            start, end, edge_start, edge_end
        )
        parameters.extend(intersections)
    ordered = _dedupe_sorted(parameters)
    for left, right in zip(ordered, ordered[1:]):
        if right - left <= 1e-10:
            continue
        midpoint = (left + right) / 2.0
        sample = _lerp(start, end, midpoint)
        if not _point_in_or_on_polygon(sample, polygon):
            return False
    return True


def first_boundary_hit(
    origin: Vec2, aim: Vec2, polygon: tuple[Vec2, ...]
) -> tuple[Vec2, float]:
    dx = aim.x - origin.x
    dy = aim.y - origin.y
    length = math.hypot(dx, dy)
    if length <= 1e-12:
        raise ValidationError("capture aim bearing has zero length")
    direction = Vec2(dx / length, dy / length)
    candidates: list[tuple[float, Vec2]] = []
    for edge_start, edge_end in _polygon_edges(polygon):
        intersection = _ray_segment_intersection(origin, direction, edge_start, edge_end)
        if intersection is not None and intersection[0] > 1e-9:
            candidates.append(intersection)
    if not candidates:
        raise ValidationError("capture aim bearing does not meet the room boundary")
    distance, point = min(candidates, key=lambda item: item[0])
    return (
        Vec2(quantize_m(point.x), quantize_m(point.y)),
        quantize_m(distance),
    )


def intersect_intervals(
    left: tuple[tuple[float, float], ...],
    right: tuple[tuple[float, float], ...],
) -> tuple[tuple[float, float], ...]:
    result: list[tuple[float, float]] = []
    for left_start, left_end in left:
        for right_start, right_end in right:
            start, end = max(left_start, right_start), min(left_end, right_end)
            if end > start:
                result.append((start, end))
    return tuple(result)


def mode_plan_sha256(
    plan: CapturePlan, mode: CaptureMode, room_sha256: str
) -> str:
    station_ids = {
        group.station_id
        for capture_pass in mode.passes
        for group in capture_pass.groups
    }
    payload = {
        "schema_version": plan.schema_version,
        "room_id": plan.room_id,
        "capture_id": plan.capture_id,
        "device_profile": asdict(plan.device_profile),
        "wall_review": [asdict(item) for item in plan.wall_review],
        "scale_anchors": [asdict(item) for item in plan.scale_anchors],
        "mode": asdict(mode),
        "stations": [
            asdict(station)
            for station in plan.stations
            if station.id in station_ids
        ],
        "room_model_sha256": room_sha256,
    }
    encoded = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def analyze_capture_plan(
    plan: CapturePlan, room: RoomModel, room_sha256: str
) -> tuple[ModeCoverage, ...]:
    return tuple(
        _analyze_mode(plan, mode, room, room_sha256) for mode in plan.modes
    )


def raise_for_coverage_errors(coverage: tuple[ModeCoverage, ...]) -> None:
    errors = sorted(
        (
            issue
            for mode in coverage
            for issue in mode.issues
            if issue.severity == "error"
        ),
        key=lambda issue: (issue.mode_id, issue.code),
    )
    if errors:
        raise ValidationError(
            "capture coverage errors: "
            + ", ".join(issue.code for issue in errors)
        )


def _analyze_mode(
    plan: CapturePlan,
    mode: CaptureMode,
    room: RoomModel,
    room_sha256: str,
) -> ModeCoverage:
    issues: dict[str, CoverageIssue] = {}

    def add_issue(
        base_code: str, severity: str, subject_id: str, message: str
    ) -> None:
        code = f"{base_code}:{subject_id}"
        issues.setdefault(
            code,
            CoverageIssue(
                code=code,
                severity=severity,
                mode_id=mode.id,
                subject_id=subject_id,
                message=message,
            ),
        )

    groups_by_shot = {
        shot.id: group
        for capture_pass in mode.passes
        for group in capture_pass.groups
        for shot in group.shots
    }
    # First visits define route order; catalog order is not a travel itinerary.
    station_ids = tuple(dict.fromkeys(group.station_id for group in mode.groups))
    ordered_stations = tuple(
        plan.station(station_id) for station_id in station_ids
    )

    for station in ordered_stations:
        blocked = not point_strictly_inside_polygon(
            station.standing_point_m, room.floor_polygon
        ) or any(
            _point_in_proxy_footprint(station.standing_point_m, proxy)
            for proxy in room.proxies
        )
        if blocked:
            add_issue(
                "E_STATION_BLOCKED",
                "error",
                station.id,
                "station lies on a boundary or inside a proxy footprint",
            )
        clearance = min(
            [
                _distance_to_segment(station.standing_point_m, wall.start, wall.end)
                for wall in room.walls
            ]
            + [
                _distance_to_proxy_footprint(station.standing_point_m, proxy)
                for proxy in room.proxies
            ]
        )
        clearance = quantize_m(clearance)
        if not blocked and clearance < MIN_STATION_CLEARANCE_M:
            add_issue(
                "W_STATION_CLEARANCE",
                "warning",
                station.id,
                f"station clearance is {clearance:.4f} m",
            )

    shot_coverage_by_id: dict[str, ShotCoverage] = {}
    for shot in mode.shots:
        group = groups_by_shot[shot.id]
        station = plan.station(group.station_id)
        origin = station.standing_point_m
        usable_fov = quantize_deg(
            plan.device_profile.horizontal_fov_deg
            - 2.0 * plan.device_profile.coverage_margin_deg
        )
        half_fov = usable_fov / 2.0
        bearing = _bearing_deg(origin, shot.aim_point_m)
        hit, boundary_distance = first_boundary_hit(
            origin, shot.aim_point_m, room.floor_polygon
        )
        left_hit, _ = _boundary_hit_for_bearing(
            origin, bearing + half_fov, room.floor_polygon
        )
        right_hit, _ = _boundary_hit_for_bearing(
            origin, bearing - half_fov, room.floor_polygon
        )
        relative_angles = tuple(
            quantize_deg(relative_bearing_deg(
                origin, shot.aim_point_m, Vec2(point.x, point.y)
            ))
            for point in shot.framing_points_m
        )
        horizontal_span = _smallest_circular_span_deg(
            tuple(
                math.degrees(
                    math.atan2(point.y - origin.y, point.x - origin.x)
                )
                for point in shot.framing_points_m
            )
        )
        target_points = {
            target_id: tuple(
                point
                for point in shot.framing_points_m
                if _framing_point_belongs_to_target(point, target_id, room)
            )
            for target_id in shot.target_ids
        }
        visible_targets = tuple(
            target_id
            for target_id in shot.target_ids
            if target_points[target_id]
            and all(
                abs(
                    quantize_deg(relative_bearing_deg(
                        origin, shot.aim_point_m, Vec2(point.x, point.y)
                    ))
                )
                <= half_fov + 1e-9
                and segment_inside_polygon(
                    origin, Vec2(point.x, point.y), room.floor_polygon
                )
                for point in target_points[target_id]
            )
            and _vertical_points_fit(target_points[target_id], origin, shot, plan)
        )
        vertical_interval = (
            quantize_deg(shot.pitch_deg - plan.device_profile.vertical_fov_deg / 2.0),
            quantize_deg(shot.pitch_deg + plan.device_profile.vertical_fov_deg / 2.0),
        )
        shot_coverage_by_id[shot.id] = ShotCoverage(
            shot_id=shot.id,
            station_id=station.id,
            bearing_deg=quantize_deg(bearing),
            boundary_hit_m=hit,
            boundary_distance_m=boundary_distance,
            usable_horizontal_fov_deg=usable_fov,
            horizontal_span_deg=quantize_deg(horizontal_span),
            vertical_interval_deg=vertical_interval,
            visible_target_ids=visible_targets,
            cone_polygon_m=(
                Vec2(quantize_m(origin.x), quantize_m(origin.y)),
                left_hit,
                right_hit,
            ),
        )

        if not segment_inside_polygon(origin, shot.aim_point_m, room.floor_polygon):
            add_issue(
                "E_LOS_OUTSIDE_ROOM",
                "error",
                shot.id,
                "station-to-aim segment leaves the floor polygon",
            )
        elif any(
            not segment_inside_polygon(
                origin, Vec2(point.x, point.y), room.floor_polygon
            )
            for point in shot.framing_points_m
        ):
            add_issue(
                "E_LOS_OUTSIDE_ROOM",
                "error",
                shot.id,
                "station-to-framing-point segment leaves the floor polygon",
            )
        behind = any(
            points
            and all(
                abs(
                    quantize_deg(relative_bearing_deg(
                        origin, shot.aim_point_m, Vec2(point.x, point.y)
                    ))
                )
                > 90.0
                for point in points
            )
            for points in target_points.values()
        )
        if behind:
            add_issue(
                "E_TARGET_BEHIND_BEARING",
                "error",
                shot.id,
                "a declared target lies behind the shot bearing",
            )
        elif any(abs(angle) > half_fov + 1e-9 for angle in relative_angles):
            add_issue(
                "E_HORIZONTAL_FOV",
                "error",
                shot.id,
                f"framing span {quantize_deg(horizontal_span):.2f} degrees; "
                f"maximum bearing offset {max(abs(a) for a in relative_angles):.2f} "
                f"degrees exceeds the {half_fov:.2f} degree half-field",
            )
        if not _vertical_points_fit(
            shot.framing_points_m, origin, shot, plan
        ):
            add_issue(
                "E_VERTICAL_FOV",
                "error",
                shot.id,
                "required vertical framing exceeds the usable vertical field",
            )
        if boundary_distance < MIN_BOUNDARY_RAY_M:
            add_issue(
                "W_SHORT_BOUNDARY_RAY",
                "warning",
                shot.id,
                f"first boundary ray is {boundary_distance:.4f} m",
            )

    for group in mode.groups:
        coverages = [shot_coverage_by_id[shot.id] for shot in group.shots]
        if any(
            quantize_deg(_angular_difference(left.bearing_deg, right.bearing_deg))
            > quantize_deg(0.7 * plan.device_profile.horizontal_fov_deg)
            for left, right in zip(coverages, coverages[1:])
        ):
            add_issue(
                "W_PAIRED_BEARING_GAP",
                "warning",
                group.id,
                "paired shot bearings exceed the provisional overlap threshold",
            )

    for station in ordered_stations:
        level = [
            shot_coverage_by_id[shot.id]
            for group in mode.groups
            if group.station_id == station.id
            for shot in group.shots
            if shot.pitch == "level"
        ]
        pitched = [
            shot_coverage_by_id[shot.id]
            for group in mode.groups
            if group.station_id == station.id
            for shot in group.shots
            if shot.pitch in {"up", "down"}
        ]
        if level and pitched and any(
            max((
                _interval_overlap_ratio(item.vertical_interval_deg, candidate.vertical_interval_deg)
                for candidate in level
                if quantize_deg(_angular_difference(item.bearing_deg, candidate.bearing_deg))
                < item.usable_horizontal_fov_deg
            ), default=0.0)
            < MIN_VERTICAL_OVERLAP
            for item in pitched
        ):
            add_issue(
                "W_VERTICAL_OVERLAP",
                "warning",
                station.id,
                "pitched coverage overlaps compatible level coverage by less than 30%",
            )

    wall_intervals_by_station: dict[
        str, dict[str, tuple[tuple[float, float], ...]]
    ] = {}
    for station in ordered_stations:
        station_shots = [
            shot
            for group in mode.groups
            if group.station_id == station.id
            for shot in group.shots
        ]
        wall_intervals_by_station[station.id] = {
            wall.id: _merge_intervals(
                tuple(
                    interval
                    for shot in station_shots
                    for interval in _shot_wall_intervals(
                        station.standing_point_m,
                        shot,
                        wall,
                        room,
                        plan.device_profile.horizontal_fov_deg
                        / 2.0
                        - plan.device_profile.coverage_margin_deg,
                    )
                )
            )
            for wall in room.walls
        }

    adjacent_spans: list[tuple[str, str, float]] = []
    adjacent_pairs = list(zip(ordered_stations, ordered_stations[1:]))
    if len(ordered_stations) > 2:
        adjacent_pairs.append((ordered_stations[-1], ordered_stations[0]))
    for left, right in adjacent_pairs:
        shared = max(
            (
                sum(
                    end - start
                    for start, end in intersect_intervals(
                        wall_intervals_by_station[left.id][wall.id],
                        wall_intervals_by_station[right.id][wall.id],
                    )
                )
                * wall.length_m
                for wall in room.walls
            ),
            default=0.0,
        )
        shared = quantize_m(shared)
        pair_id = f"{left.id}-{right.id}"
        adjacent_spans.append((left.id, right.id, shared))
        if shared < MIN_ADJACENT_SHARED_SPAN_M:
            add_issue(
                "W_ADJACENT_SHARED_SPAN",
                "warning",
                pair_id,
                f"maximum shared structural span is {shared:.4f} m",
            )

    floor_seam_spans = tuple(
        (wall.id, _wall_seam_coverage_m(plan, mode, room, wall, 0.0))
        for wall in room.walls
    )
    ceiling_seam_spans = tuple(
        (wall.id, _wall_seam_coverage_m(plan, mode, room, wall, room.ceiling_height_m))
        for wall in room.walls
    )
    for wall_id, span in floor_seam_spans:
        if span == 0.0:
            add_issue(
                "W_FLOOR_SEAM_GAP",
                "warning",
                wall_id,
                "no planned shot covers this required floor-wall seam",
            )

    wall_baselines: list[tuple[str, int, float]] = []
    for wall in room.walls:
        stations = _target_station_points(plan, mode, wall.id, shot_coverage_by_id)
        baseline = _maximum_baseline(stations)
        wall_baselines.append((wall.id, len(stations), baseline))
        if len(stations) < 2 or baseline < MIN_ANCHOR_BASELINE_M:
            add_issue(
                "W_WALL_REDUNDANCY",
                "warning",
                wall.id,
                f"wall has {len(stations)} station(s), baseline {baseline:.4f} m",
            )

    anchor_by_id = {anchor.id: anchor for anchor in plan.scale_anchors}
    anchor_baselines: list[tuple[str, int, float]] = []
    for anchor_id in mode.required_scale_anchor_ids:
        target_id = anchor_by_id[anchor_id].target_id
        stations = _target_station_points(plan, mode, target_id, shot_coverage_by_id)
        baseline = _maximum_baseline(stations)
        anchor_baselines.append((anchor_id, len(stations), baseline))
        if len(stations) < 2 or baseline < MIN_ANCHOR_BASELINE_M:
            add_issue(
                "E_ANCHOR_BASELINE",
                "error",
                anchor_id,
                f"anchor has {len(stations)} station(s), baseline {baseline:.4f} m",
            )

    return ModeCoverage(
        mode_id=mode.id,
        mode_plan_sha256=mode_plan_sha256(plan, mode, room_sha256),
        shots=tuple(shot_coverage_by_id[shot.id] for shot in mode.shots),
        adjacent_shared_spans_m=tuple(adjacent_spans),
        wall_station_baselines_m=tuple(wall_baselines),
        anchor_station_baselines_m=tuple(anchor_baselines),
        issues=tuple(issues[code] for code in sorted(issues)),
        floor_seam_spans_m=floor_seam_spans,
        ceiling_seam_spans_m=ceiling_seam_spans,
    )


def _polygon_edges(
    polygon: tuple[Vec2, ...]
) -> tuple[tuple[Vec2, Vec2], ...]:
    return tuple(zip(polygon, polygon[1:] + polygon[:1], strict=True))


def _point_in_or_on_polygon(point: Vec2, polygon: tuple[Vec2, ...]) -> bool:
    if not math.isfinite(point.x) or not math.isfinite(point.y):
        return False
    inside = False
    for start, end in _polygon_edges(polygon):
        if quantize_m(_distance_to_segment(point, start, end)) <= GEOMETRY_TOLERANCE_M:
            return True
        if (start.y > point.y) != (end.y > point.y):
            cross_x = start.x + (
                (point.y - start.y) * (end.x - start.x) / (end.y - start.y)
            )
            if point.x < cross_x:
                inside = not inside
    return inside


def _distance_to_segment(point: Vec2, start: Vec2, end: Vec2) -> float:
    dx = end.x - start.x
    dy = end.y - start.y
    length_squared = dx * dx + dy * dy
    if length_squared <= 1e-18:
        return point.distance_to(start)
    parameter = max(
        0.0,
        min(
            1.0,
            ((point.x - start.x) * dx + (point.y - start.y) * dy)
            / length_squared,
        ),
    )
    return point.distance_to(Vec2(start.x + parameter * dx, start.y + parameter * dy))


def _segment_edge_intersection_parameters(
    start: Vec2, end: Vec2, edge_start: Vec2, edge_end: Vec2
) -> tuple[float, ...]:
    direction = Vec2(end.x - start.x, end.y - start.y)
    edge = Vec2(edge_end.x - edge_start.x, edge_end.y - edge_start.y)
    offset = Vec2(edge_start.x - start.x, edge_start.y - start.y)
    denominator = _cross(direction, edge)
    if abs(denominator) <= 1e-12:
        if abs(_cross(offset, direction)) > 1e-10:
            return ()
        length_squared = direction.x * direction.x + direction.y * direction.y
        if length_squared <= 1e-18:
            return ()
        values = tuple(
            (
                (point.x - start.x) * direction.x
                + (point.y - start.y) * direction.y
            )
            / length_squared
            for point in (edge_start, edge_end)
        )
        return tuple(value for value in values if -1e-10 <= value <= 1.0 + 1e-10)
    parameter = _cross(offset, edge) / denominator
    edge_parameter = _cross(offset, direction) / denominator
    if -1e-10 <= parameter <= 1.0 + 1e-10 and -1e-10 <= edge_parameter <= 1.0 + 1e-10:
        return (min(1.0, max(0.0, parameter)),)
    return ()


def _dedupe_sorted(values: list[float]) -> tuple[float, ...]:
    result: list[float] = []
    for value in sorted(values):
        if not result or abs(value - result[-1]) > 1e-9:
            result.append(value)
    return tuple(result)


def _lerp(start: Vec2, end: Vec2, parameter: float) -> Vec2:
    return Vec2(
        start.x + (end.x - start.x) * parameter,
        start.y + (end.y - start.y) * parameter,
    )


def _cross(left: Vec2, right: Vec2) -> float:
    return left.x * right.y - left.y * right.x


def _ray_segment_intersection(
    origin: Vec2, direction: Vec2, start: Vec2, end: Vec2
) -> tuple[float, Vec2] | None:
    edge = Vec2(end.x - start.x, end.y - start.y)
    offset = Vec2(start.x - origin.x, start.y - origin.y)
    denominator = _cross(direction, edge)
    if abs(denominator) <= 1e-12:
        return None
    ray_parameter = _cross(offset, edge) / denominator
    edge_parameter = _cross(offset, direction) / denominator
    if ray_parameter >= -1e-10 and -1e-10 <= edge_parameter <= 1.0 + 1e-10:
        return (
            max(0.0, ray_parameter),
            Vec2(
                origin.x + ray_parameter * direction.x,
                origin.y + ray_parameter * direction.y,
            ),
        )
    return None


def _boundary_hit_for_bearing(
    origin: Vec2, bearing_deg: float, polygon: tuple[Vec2, ...]
) -> tuple[Vec2, float]:
    radians = math.radians(bearing_deg)
    aim = Vec2(origin.x + math.cos(radians), origin.y + math.sin(radians))
    return first_boundary_hit(origin, aim, polygon)


def _bearing_deg(origin: Vec2, aim: Vec2) -> float:
    return (math.degrees(math.atan2(aim.y - origin.y, aim.x - origin.x)) + 180.0) % 360.0 - 180.0


def _smallest_circular_span_deg(bearings: tuple[float, ...]) -> float:
    if len(bearings) < 2:
        return 0.0
    normalized = sorted(item % 360.0 for item in bearings)
    gaps = [
        right - left for left, right in zip(normalized, normalized[1:])
    ] + [normalized[0] + 360.0 - normalized[-1]]
    return 360.0 - max(gaps)


def _vertical_points_fit(
    points: tuple[Vec3, ...], origin: Vec2, shot: CaptureShot, plan: CapturePlan
) -> bool:
    half_fov = plan.device_profile.vertical_fov_deg / 2.0
    lower = quantize_deg(shot.pitch_deg - half_fov)
    upper = quantize_deg(shot.pitch_deg + half_fov)
    heights = (
        plan.device_profile.camera_height_m
        - plan.device_profile.camera_height_tolerance_m,
        plan.device_profile.camera_height_m
        + plan.device_profile.camera_height_tolerance_m,
    )
    return all(
        lower
        <= quantize_deg(
            math.degrees(
                math.atan2(
                    point.z - height,
                    math.hypot(point.x - origin.x, point.y - origin.y),
                )
            )
        )
        <= upper
        for point in points
        for height in heights
    )


def _angular_difference(left: float, right: float) -> float:
    return abs((right - left + 180.0) % 360.0 - 180.0)


def _interval_overlap_ratio(
    left: tuple[float, float], right: tuple[float, float]
) -> float:
    overlap = quantize_deg(max(0.0, min(left[1], right[1]) - max(left[0], right[0])))
    smaller = quantize_deg(min(left[1] - left[0], right[1] - right[0]))
    return 0.0 if smaller <= 0 else overlap / smaller


def _point_in_proxy_footprint(point: Vec2, proxy: ProxyObject) -> bool:
    local_x, local_y = _proxy_local_xy(point, proxy)
    return (
        quantize_m(abs(local_x) - proxy.size.x / 2.0) <= GEOMETRY_TOLERANCE_M
        and quantize_m(abs(local_y) - proxy.size.y / 2.0) <= GEOMETRY_TOLERANCE_M
    )


def _distance_to_proxy_footprint(point: Vec2, proxy: ProxyObject) -> float:
    local_x, local_y = _proxy_local_xy(point, proxy)
    outside_x = max(abs(local_x) - proxy.size.x / 2.0, 0.0)
    outside_y = max(abs(local_y) - proxy.size.y / 2.0, 0.0)
    if outside_x > 0.0 or outside_y > 0.0:
        return math.hypot(outside_x, outside_y)
    return min(
        proxy.size.x / 2.0 - abs(local_x),
        proxy.size.y / 2.0 - abs(local_y),
    )


def _proxy_local_xy(point: Vec2, proxy: ProxyObject) -> tuple[float, float]:
    dx = point.x - proxy.center.x
    dy = point.y - proxy.center.y
    cosine = math.cos(proxy.yaw_rad)
    sine = math.sin(proxy.yaw_rad)
    return cosine * dx + sine * dy, -sine * dx + cosine * dy


def _shot_wall_intervals(
    station: Vec2,
    shot: CaptureShot,
    wall: Wall,
    room: RoomModel,
    half_fov: float,
) -> tuple[tuple[float, float], ...]:
    axis = _bearing_deg(station, shot.aim_point_m)
    candidates = [0.0, 1.0]
    # Visibility can change at a reflex vertex even when neither FOV edge
    # crosses this wall. Split there before classifying open intervals.
    bearings = [axis - half_fov, axis + half_fov]
    bearings.extend(_bearing_deg(station, vertex) for vertex in room.floor_polygon)
    for bearing in bearings:
        radians = math.radians(bearing)
        direction = Vec2(math.cos(radians), math.sin(radians))
        intersection = _ray_segment_intersection(
            station, direction, wall.start, wall.end
        )
        if intersection is not None:
            point = intersection[1]
            wall_dx = wall.end.x - wall.start.x
            wall_dy = wall.end.y - wall.start.y
            candidates.append(
                (
                    (point.x - wall.start.x) * wall_dx
                    + (point.y - wall.start.y) * wall_dy
                )
                / (wall.length_m * wall.length_m)
            )
    ordered = _dedupe_sorted(
        [min(1.0, max(0.0, value)) for value in candidates]
    )
    result: list[tuple[float, float]] = []
    for start, end in zip(ordered, ordered[1:]):
        midpoint = _lerp(wall.start, wall.end, (start + end) / 2.0)
        if (
            abs(quantize_deg(relative_bearing_deg(station, shot.aim_point_m, midpoint)))
            <= half_fov + 1e-9
            and segment_inside_polygon(station, midpoint, room.floor_polygon)
        ):
            result.append((start, end))
    return tuple(result)


def _merge_intervals(
    intervals: tuple[tuple[float, float], ...]
) -> tuple[tuple[float, float], ...]:
    if not intervals:
        return ()
    ordered = sorted(intervals)
    merged: list[list[float]] = [[ordered[0][0], ordered[0][1]]]
    for start, end in ordered[1:]:
        if start <= merged[-1][1] + 1e-10:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return tuple((start, end) for start, end in merged)


def _wall_floor_seam_is_covered(
    plan: CapturePlan, mode: CaptureMode, room: RoomModel, wall: Wall
) -> bool:
    return _wall_seam_coverage_m(plan, mode, room, wall, 0.0) > 0.0


def _wall_seam_coverage_m(
    plan: CapturePlan, mode: CaptureMode, room: RoomModel, wall: Wall,
    seam_height_m: float,
) -> float:
    half_horizontal = (
        plan.device_profile.horizontal_fov_deg / 2.0
        - plan.device_profile.coverage_margin_deg
    )
    half_vertical = plan.device_profile.vertical_fov_deg / 2.0
    heights = (
        plan.device_profile.camera_height_m
        - plan.device_profile.camera_height_tolerance_m,
        plan.device_profile.camera_height_m
        + plan.device_profile.camera_height_tolerance_m,
    )
    accepted: list[tuple[float, float]] = []
    for group in mode.groups:
        station = plan.station(group.station_id).standing_point_m
        for shot in group.shots:
            for start, end in _shot_wall_intervals(
                station, shot, wall, room, half_horizontal
            ):
                candidates = [start, end]
                # At fixed z each vertical FOV boundary is a circle about the
                # station. Its wall intersections partition visibility exactly.
                for height in heights:
                    for elevation in (shot.pitch_deg - half_vertical, shot.pitch_deg + half_vertical):
                        if -90.0 < elevation < 90.0 and elevation != 0.0:
                            distance = (seam_height_m - height) / math.tan(math.radians(elevation))
                            if distance <= 0.0:
                                continue
                            candidates.extend(
                                t for t in _wall_distance_parameters(station, wall, distance)
                                if start < t < end
                            )
                ordered = _dedupe_sorted(candidates)
                for left, right in zip(ordered, ordered[1:]):
                    if quantize_m((right - left) * wall.length_m) <= 0.0:
                        continue
                    point = _lerp(wall.start, wall.end, (left + right) / 2.0)
                    if _vertical_points_fit((Vec3(point.x, point.y, seam_height_m),), station, shot, plan):
                        accepted.append((left, right))
    return quantize_m(sum(end - start for start, end in _merge_intervals(tuple(accepted))) * wall.length_m)


def _wall_distance_parameters(station: Vec2, wall: Wall, distance: float) -> tuple[float, ...]:
    dx, dy = wall.end.x - wall.start.x, wall.end.y - wall.start.y
    ox, oy = wall.start.x - station.x, wall.start.y - station.y
    a = dx * dx + dy * dy
    b = 2.0 * (dx * ox + dy * oy)
    c = ox * ox + oy * oy - distance * distance
    discriminant = b * b - 4.0 * a * c
    if discriminant < 0.0:
        return ()
    root = math.sqrt(discriminant)
    return ((-b - root) / (2.0 * a), (-b + root) / (2.0 * a))


def _target_station_points(
    plan: CapturePlan, mode: CaptureMode, target_id: str,
    shot_coverages: dict[str, ShotCoverage],
) -> dict[str, Vec2]:
    result: dict[str, Vec2] = {}
    for group in mode.groups:
        station = plan.station(group.station_id)
        for shot in group.shots:
            if target_id not in shot.target_ids:
                continue
            if target_id in shot_coverages[shot.id].visible_target_ids:
                result[station.id] = station.standing_point_m
                break
    return result


def _maximum_baseline(stations: dict[str, Vec2]) -> float:
    points = list(stations.values())
    if len(points) < 2:
        return 0.0
    return quantize_m(
        max(
            left.distance_to(right)
            for index, left in enumerate(points)
            for right in points[index + 1 :]
        )
    )
