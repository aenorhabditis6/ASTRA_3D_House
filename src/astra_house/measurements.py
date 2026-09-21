"""Validated real-world measurements for a reconstruction project."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .errors import ValidationError
from .model import SourceRef

SCHEMA_VERSION = "1.0"
APPLICATIONS = {"exact_override", "audit_only"}
TARGET_KINDS = {"opening", "proxy", "wall"}


@dataclass(frozen=True)
class MeasurementRecord:
    id: str
    target_kind: str
    target_id: str
    dimension: str
    value_m: float
    application: str
    source: SourceRef

    @classmethod
    def from_dict(cls, data: Any) -> "MeasurementRecord":
        if not isinstance(data, dict):
            raise ValidationError("measurement record must be an object")
        try:
            record = cls(
                id=str(data["id"]),
                target_kind=str(data["target_kind"]),
                target_id=str(data["target_id"]),
                dimension=str(data["dimension"]),
                value_m=float(data["value_m"]),
                application=str(data["application"]),
                source=SourceRef.from_dict(data["source"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValidationError(f"invalid measurement record: {error}") from error
        record.validate()
        return record

    def validate(self) -> None:
        if not self.id.strip():
            raise ValidationError("measurement id must not be empty")
        if self.target_kind not in TARGET_KINDS:
            raise ValidationError(
                f"measurement {self.id!r} has unsupported target kind"
            )
        if not self.target_id.strip() or not self.dimension.strip():
            raise ValidationError(
                f"measurement {self.id!r} target and dimension must not be empty"
            )
        if not math.isfinite(self.value_m) or self.value_m <= 0:
            raise ValidationError(
                f"measurement {self.id!r} value must be positive and finite"
            )
        if self.application not in APPLICATIONS:
            raise ValidationError(
                f"measurement {self.id!r} has unsupported application"
            )
        self.source.validate()


@dataclass(frozen=True)
class MeasurementSet:
    schema_version: str
    room_id: str
    measurements: tuple[MeasurementRecord, ...]

    @classmethod
    def from_dict(cls, data: Any) -> "MeasurementSet":
        if not isinstance(data, dict):
            raise ValidationError("measurement set must be an object")
        try:
            result = cls(
                schema_version=str(data["schema_version"]),
                room_id=str(data["room_id"]),
                measurements=tuple(
                    MeasurementRecord.from_dict(item)
                    for item in data["measurements"]
                ),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValidationError(f"invalid measurement set: {error}") from error
        result.validate()
        return result

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValidationError(
                f"unsupported measurement schema_version {self.schema_version!r}"
            )
        if not self.room_id.strip():
            raise ValidationError("measurement room_id must not be empty")
        ids: set[str] = set()
        targets: set[tuple[str, str]] = set()
        for record in self.measurements:
            record.validate()
            if record.id in ids:
                raise ValidationError(f"duplicate measurement id {record.id!r}")
            ids.add(record.id)
            key = (record.target_id, record.dimension)
            if key in targets:
                raise ValidationError(
                    "duplicate measurement for "
                    f"{record.target_id!r} dimension {record.dimension!r}"
                )
            targets.add(key)

    def record_for(self, target_id: str, dimension: str) -> MeasurementRecord:
        for record in self.measurements:
            if record.target_id == target_id and record.dimension == dimension:
                return record
        raise ValidationError(
            f"missing measurement for {target_id!r} dimension {dimension!r}"
        )

    def value_for(self, target_id: str, dimension: str) -> float:
        return self.record_for(target_id, dimension).value_m

    def optional_record_for(
        self, target_id: str, dimension: str
    ) -> MeasurementRecord | None:
        try:
            return self.record_for(target_id, dimension)
        except ValidationError:
            return None
