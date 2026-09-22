"""Validate and package a deterministic, self-contained capture guide."""
from __future__ import annotations

import hashlib
import json
import os
import struct
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .capture import CapturePlan, CoverageReview
from .capture_geometry import ModeCoverage, analyze_capture_plan, raise_for_coverage_errors
from .capture_web import render_capture_html
from .errors import ValidationError
from .measurements import MeasurementSet
from .model import RoomModel
from .plan import PlanAnnotation

GENERATOR_VERSION = "astra-house-capture-pack/2.0"


def write_capture_pack(
    plan: CapturePlan, annotation: PlanAnnotation, room: RoomModel,
    measurements: MeasurementSet, source_plan_path: Path, output_dir: Path,
) -> Path:
    """Validate before atomically replacing each of the three artifacts.

    The CLI verifies the immutable source manifest before calling this function.
    Library callers are responsible for supplying a trusted source PNG.
    """
    plan.validate(room, measurements)
    annotation.validate()
    if annotation.target.room_id != room.room_id:
        raise ValidationError("annotation room_id does not match room model")
    try:
        plan_image = Path(source_plan_path).read_bytes()
    except OSError as error:
        raise ValidationError(f"cannot read source floor plan: {error}") from error
    _validate_png(plan_image, annotation)
    hashes = {
        "capture_plan_sha256": hashlib.sha256(_json_bytes(asdict(plan))).hexdigest(),
        "floorplan_sha256": hashlib.sha256(plan_image).hexdigest(),
        "room_model_sha256": hashlib.sha256(_json_bytes(room.to_dict())).hexdigest(),
        "measurements_sha256": hashlib.sha256(_json_bytes(asdict(measurements))).hexdigest(),
    }
    coverage = analyze_capture_plan(plan, room, hashes["room_model_sha256"])
    raise_for_coverage_errors(coverage)
    report = build_capture_report(plan, coverage, hashes)
    rendered = {
        "capture-intake.json": _json_bytes(build_capture_intake(plan, coverage)),
        "capture-pack-report.json": _json_bytes(report),
        "index.html": render_capture_html(plan, annotation, plan_image, coverage, report).encode("utf-8"),
    }
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in rendered.items():
        _atomic_write(output_dir / name, content)
    return output_dir / "index.html"


def build_capture_intake(plan: CapturePlan, coverage: tuple[ModeCoverage, ...]) -> dict[str, Any]:
    hashes = {item.mode_id: item.mode_plan_sha256 for item in coverage}
    modes = {}
    for mode in plan.modes:
        rows = []
        for capture_pass in mode.passes:
            for group in capture_pass.groups:
                for shot in group.shots:
                    rows.append({
                        "assigned_shot_id": shot.id, "pass_id": capture_pass.id,
                        "group_id": group.id, "station_id": group.station_id,
                        "planned_order": len(rows) + 1, "source_filename": None,
                        "sha256": None, "dimensions_px": None,
                        "exif": {name: None for name in (
                            "date_time_original", "sub_sec_time_original",
                            "offset_time_original", "orientation",
                        )},
                    })
        modes[mode.id] = {"mode_plan_sha256": hashes[mode.id], "shots": rows}
    return {"schema_version": "2.0", "room_id": plan.room_id,
            "capture_id": plan.capture_id, "modes": modes}


def _review_status(review: CoverageReview | None, coverage: ModeCoverage) -> str:
    if review is None:
        return "missing"
    if review.mode_plan_sha256 != coverage.mode_plan_sha256:
        return "stale_hash"
    codes = tuple(sorted(issue.code for issue in coverage.issues if issue.severity == "warning"))
    if tuple(sorted(review.warning_codes)) != codes:
        return "stale_codes"
    return "current"


def build_capture_report(
    plan: CapturePlan, coverage: tuple[ModeCoverage, ...], source_hashes: dict[str, str],
) -> dict[str, Any]:
    raise_for_coverage_errors(coverage)
    reviews = {review.mode_id: review for review in plan.coverage_review}
    statuses = {item.mode_id: _review_status(reviews.get(item.mode_id), item) for item in coverage}
    diagnostics = []
    for item in coverage:
        data = asdict(item)
        data["issues"] = sorted(data["issues"], key=lambda issue: (issue["code"], issue["subject_id"]))
        diagnostics.append(data)
    return {
        "schema_version": "2.0", "generator_version": GENERATOR_VERSION,
        "room_id": plan.room_id, "capture_id": plan.capture_id,
        "status": "publishable" if all(value == "current" for value in statuses.values()) else "draft",
        "source_hashes": source_hashes,
        "mode_counts": {mode.id: len(mode.shots) for mode in plan.modes},
        "group_counts": {mode.id: len(mode.groups) for mode in plan.modes},
        "station_counts": {mode.id: len({group.station_id for group in mode.groups}) for mode in plan.modes},
        "pass_counts": {mode.id: {item.id: len(item.shots) for item in mode.passes} for mode in plan.modes},
        "mode_plan_sha256": {item.mode_id: item.mode_plan_sha256 for item in coverage},
        "coverage_review_digests": {
            item.mode_id: hashlib.sha256(_json_bytes(asdict(reviews[item.mode_id]))).hexdigest()
            if item.mode_id in reviews else None for item in coverage
        },
        "coverage_review_status": statuses, "coverage": diagnostics,
    }


def _validate_png(data: bytes, annotation: PlanAnnotation) -> None:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValidationError("source floor plan must be a valid PNG")
    width, height = struct.unpack(">II", data[16:24])
    if (width, height) != (annotation.image.width_px, annotation.image.height_px):
        raise ValidationError("source floor-plan dimensions do not match annotation")


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _atomic_write(path: Path, content: bytes) -> None:
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary_path = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
