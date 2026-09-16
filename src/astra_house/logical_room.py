"""Convert reviewed plan annotations into the versioned logical room model."""

from __future__ import annotations

from .model import Opening, ProxyObject, RoomModel, SourceRef, Vec2, Vec3, Wall
from .plan import PlanAnnotation, PlanCalibration


def build_logical_room(annotation: PlanAnnotation) -> RoomModel:
    """Build and validate a deterministic metric model from *annotation*."""
    annotation.validate()
    calibration = PlanCalibration.from_annotation(annotation)

    plan_source = SourceRef(
        "trusted_floorplan", "dorm-suite-floorplan.png", 1.0
    )
    bed_scale_source = SourceRef(
        "provisional_scale", "full-bed 54x75in", 0.6
    )
    height_source = SourceRef(
        "confirmed_measurement", "user: 11ft", 1.0
    )
    assumption_source = SourceRef(
        "provisional_assumption", "opening/furniture default height", 0.35
    )

    floor_polygon = tuple(
        calibration.pixel_to_room(point)
        for point in annotation.target.floor_polygon_px
    )
    walls = tuple(
        Wall(
            id=f"wall-{index:02d}",
            start=start,
            end=floor_polygon[(index + 1) % len(floor_polygon)],
            thickness_m=annotation.target.wall_thickness_m,
            geometry_source=plan_source,
            thickness_source=assumption_source,
        )
        for index, start in enumerate(floor_polygon)
    )

    openings: list[Opening] = []
    for item in annotation.openings:
        wall = walls[item.edge_index]
        endpoint_a = calibration.pixel_to_room(item.start_px)
        endpoint_b = calibration.pixel_to_room(item.end_px)
        distance_a = wall.start.distance_to(endpoint_a)
        distance_b = wall.start.distance_to(endpoint_b)
        openings.append(
            Opening(
                id=item.id,
                wall_id=wall.id,
                offset_m=min(distance_a, distance_b),
                width_m=endpoint_a.distance_to(endpoint_b),
                sill_m=item.sill_m,
                height_m=item.height_m,
                position_source=plan_source,
                vertical_source=assumption_source,
            )
        )

    proxies: list[ProxyObject] = []
    for item in annotation.objects:
        left, top, right, bottom = item.bbox_px
        center_xy = calibration.pixel_to_room(
            Vec2((left + right) / 2.0, (top + bottom) / 2.0)
        )
        if item.id == "bed-full":
            size_x = annotation.scale_anchor.size_m.x
            size_y = annotation.scale_anchor.size_m.y
        else:
            size_x = (right - left) * calibration.meters_per_pixel
            size_y = (bottom - top) * calibration.meters_per_pixel
        proxies.append(
            ProxyObject(
                id=item.id,
                kind=item.kind,
                center=Vec3(center_xy.x, center_xy.y, item.height_m / 2.0),
                size=Vec3(size_x, size_y, item.height_m),
                yaw_rad=0.0,
                footprint_source=plan_source,
                height_source=assumption_source,
            )
        )

    room = RoomModel(
        schema_version="1.0",
        room_id=annotation.target.room_id,
        units="meters",
        up_axis="Z",
        ceiling_height_m=annotation.target.ceiling_height_m,
        ceiling_height_source=height_source,
        scale_source=bed_scale_source,
        floor_polygon=floor_polygon,
        walls=walls,
        openings=tuple(openings),
        proxies=tuple(proxies),
        provenance=(
            plan_source,
            bed_scale_source,
            height_source,
            assumption_source,
        ),
    )
    room.validate()
    return room
