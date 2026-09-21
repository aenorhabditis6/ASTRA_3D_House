"""Convert reviewed plan annotations into the versioned logical room model."""

from __future__ import annotations

from .errors import ValidationError
from .measurements import MeasurementRecord, MeasurementSet
from .model import Opening, ProxyObject, RoomModel, SourceRef, Vec2, Vec3, Wall
from .plan import PlanAnnotation, PlanCalibration


def build_logical_room(
    annotation: PlanAnnotation, measurements: MeasurementSet | None = None
) -> RoomModel:
    """Build and validate a deterministic metric model from *annotation*."""
    annotation.validate()
    if measurements is not None:
        measurements.validate()
        if measurements.room_id != annotation.target.room_id:
            raise ValidationError(
                "measurement room_id does not match plan annotation room_id"
            )
    calibration = PlanCalibration.from_annotation(annotation)

    plan_source = SourceRef(
        "trusted_floorplan", "dorm-suite-floorplan.png", 1.0
    )
    bed_scale_source = _scale_source(measurements)
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
        offset_record = _measurement(measurements, item.id, "offset")
        width_record = _measurement(measurements, item.id, "width")
        height_record = _measurement(measurements, item.id, "height")
        sill_record = _measurement(measurements, item.id, "sill")
        width_m = (
            width_record.value_m
            if width_record is not None
            and width_record.application == "exact_override"
            else endpoint_a.distance_to(endpoint_b)
        )
        offset_m = (
            offset_record.value_m
            if offset_record is not None
            and offset_record.application == "exact_override"
            else min(distance_a, distance_b)
        )
        sill_m = (
            sill_record.value_m
            if sill_record is not None
            and sill_record.application == "exact_override"
            else item.sill_m
        )
        height_m = (
            height_record.value_m
            if height_record is not None
            and height_record.application == "exact_override"
            else item.height_m
        )
        horizontal_records = tuple(
            record for record in (offset_record, width_record) if record is not None
        )
        horizontal_source = (
            _combined_measurement_source(horizontal_records)
            if len(horizontal_records) == 2
            else _hybrid_source(horizontal_records[0])
            if horizontal_records
            else plan_source
        )
        vertical_records = tuple(
            record for record in (sill_record, height_record) if record is not None
        )
        vertical_source = (
            _combined_measurement_source(vertical_records)
            if vertical_records
            else assumption_source
        )
        openings.append(
            Opening(
                id=item.id,
                wall_id=wall.id,
                offset_m=offset_m,
                width_m=width_m,
                sill_m=sill_m,
                height_m=height_m,
                position_source=horizontal_source,
                vertical_source=vertical_source,
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
        size_x_record = _measurement(measurements, item.id, "size_x")
        size_y_record = _measurement(measurements, item.id, "size_y")
        if size_x_record is not None and size_x_record.application == "exact_override":
            size_x = size_x_record.value_m
        if size_y_record is not None and size_y_record.application == "exact_override":
            size_y = size_y_record.value_m
        footprint_records = tuple(
            record
            for record in (size_x_record, size_y_record)
            if record is not None
        )
        footprint_source = (
            _combined_measurement_source(footprint_records)
            if len(footprint_records) == 2
            else _hybrid_source(footprint_records[0])
            if footprint_records
            else plan_source
        )
        proxies.append(
            ProxyObject(
                id=item.id,
                kind=item.kind,
                center=Vec3(center_xy.x, center_xy.y, item.height_m / 2.0),
                size=Vec3(size_x, size_y, item.height_m),
                yaw_rad=0.0,
                footprint_source=footprint_source,
                height_source=assumption_source,
            )
        )

    measurement_sources = (
        tuple(record.source for record in measurements.measurements)
        if measurements is not None
        else ()
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
        )
        + measurement_sources,
    )
    room.validate()
    return room


def _measurement(
    measurements: MeasurementSet | None, target_id: str, dimension: str
) -> MeasurementRecord | None:
    if measurements is None:
        return None
    return measurements.optional_record_for(target_id, dimension)


def _scale_source(measurements: MeasurementSet | None) -> SourceRef:
    if measurements is None:
        return SourceRef("provisional_scale", "full-bed plan symbol", 0.6)
    length = measurements.record_for("bed-full", "size_x")
    width = measurements.record_for("bed-full", "size_y")
    return SourceRef(
        "confirmed_measurement",
        f"{length.source.reference}; {width.source.reference}",
        min(length.source.confidence, width.source.confidence),
    )


def _hybrid_source(record: MeasurementRecord) -> SourceRef:
    return SourceRef(
        "hybrid_plan_measurement",
        f"floorplan position; {record.source.reference}",
        min(0.9, record.source.confidence),
    )


def _combined_measurement_source(
    records: tuple[MeasurementRecord, ...],
) -> SourceRef:
    return SourceRef(
        "confirmed_measurement",
        "; ".join(record.source.reference for record in records),
        min(record.source.confidence for record in records),
    )
