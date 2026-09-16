"""Human-review artifacts for the plan trace and logical model."""

from __future__ import annotations

import base64
import html
import json
import os
import tempfile
from collections import Counter
from pathlib import Path

from .manifest import sha256_file
from .model import RoomModel, SourceRef
from .plan import PlanAnnotation, PlanCalibration

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WARNINGS = [
    "provisional_scale",
    "assumed_opening_heights",
    "untextured_proxy_geometry",
]


def write_plan_overlay(
    annotation: PlanAnnotation, room: RoomModel, output: Path
) -> None:
    """Write a portable SVG showing every traced plan-space fact."""
    annotation.validate()
    room.validate()
    if annotation.target.room_id != room.room_id:
        raise ValueError("annotation and room identifiers do not match")

    image_path = _asset_path(annotation.image.path)
    image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    width = annotation.image.width_px
    height = annotation.image.height_px
    calibration = PlanCalibration.from_annotation(annotation)
    polygon = " ".join(
        f"{_number(point.x)},{_number(point.y)}"
        for point in annotation.target.floor_polygon_px
    )

    elements = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}" role="img" '
            'aria-labelledby="title description">'
        ),
        "<title id=\"title\">ASTRA right-bedroom plan review</title>",
        (
            "<description id=\"description\">Source plan with reviewed target, "
            "openings, furniture proxies, scale, and provisional-value warnings.</description>"
        ),
        "<style>"
        ".label{font:700 13px -apple-system,BlinkMacSystemFont,sans-serif;paint-order:stroke;stroke:#fff;stroke-width:3px;stroke-linejoin:round}"
        ".meta{font:700 15px -apple-system,BlinkMacSystemFont,sans-serif;fill:#fff}"
        "</style>",
        (
            f'<image href="data:image/png;base64,{image_data}" x="0" y="0" '
            f'width="{width}" height="{height}" opacity="0.5"/>'
        ),
        (
            f'<polygon points="{polygon}" fill="#2075ff" fill-opacity="0.12" '
            'stroke="#1261d7" stroke-width="5" stroke-linejoin="round"/>'
        ),
    ]

    for opening in annotation.openings:
        label = html.escape(opening.id, quote=True)
        midpoint_x = (opening.start_px.x + opening.end_px.x) / 2.0
        midpoint_y = (opening.start_px.y + opening.end_px.y) / 2.0
        elements.extend(
            [
                (
                    f'<line x1="{_number(opening.start_px.x)}" '
                    f'y1="{_number(opening.start_px.y)}" '
                    f'x2="{_number(opening.end_px.x)}" '
                    f'y2="{_number(opening.end_px.y)}" '
                    'stroke="#f27c22" stroke-width="9" stroke-linecap="round"/>'
                ),
                (
                    f'<text class="label" fill="#b64b00" x="{_number(midpoint_x + 5)}" '
                    f'y="{_number(midpoint_y - 8)}">{label}</text>'
                ),
            ]
        )

    for item in annotation.objects:
        left, top, right, bottom = item.bbox_px
        label = html.escape(item.id, quote=True)
        elements.extend(
            [
                (
                    f'<rect x="{_number(left)}" y="{_number(top)}" '
                    f'width="{_number(right - left)}" height="{_number(bottom - top)}" '
                    'fill="#26a269" fill-opacity="0.09" stroke="#17884f" '
                    'stroke-width="3" stroke-dasharray="8 5"/>'
                ),
                (
                    f'<text class="label" fill="#0b6a3b" x="{_number(left + 4)}" '
                    f'y="{_number(top + 16)}">{label}</text>'
                ),
            ]
        )

    meta_text = (
        f"scale {calibration.meters_per_pixel:.10f} m/px · "
        f"ceiling {room.ceiling_height_m:.4f} m"
    )
    elements.extend(
        [
            '<rect x="18" y="18" width="440" height="74" rx="8" fill="#10243e" fill-opacity="0.9"/>',
            f'<text class="meta" x="34" y="47">{html.escape(meta_text)}</text>',
            '<text class="meta" x="34" y="75" fill="#ffd166">⚠ Door/window heights are provisional</text>',
            '<g transform="translate(22 620)">',
            '<rect width="374" height="42" rx="7" fill="#fff" fill-opacity="0.9"/>',
            '<line x1="13" y1="13" x2="49" y2="13" stroke="#1261d7" stroke-width="5"/>',
            '<text x="57" y="18" font-family="sans-serif" font-size="13">target</text>',
            '<line x1="123" y1="13" x2="159" y2="13" stroke="#f27c22" stroke-width="7"/>',
            '<text x="167" y="18" font-family="sans-serif" font-size="13">opening</text>',
            '<rect x="249" y="5" width="34" height="17" fill="none" stroke="#17884f" stroke-width="3"/>',
            '<text x="291" y="18" font-family="sans-serif" font-size="13">proxy</text>',
            '</g>',
            '</svg>',
        ]
    )
    _atomic_write_text(Path(output), "\n".join(elements) + "\n")


def write_quality_report(
    annotation: PlanAnnotation, room: RoomModel, output: Path
) -> None:
    """Write a stable, machine-readable summary of facts and uncertainties."""
    annotation.validate()
    room.validate()
    calibration = PlanCalibration.from_annotation(annotation)
    image_path = _asset_path(annotation.image.path)
    proxy_counts = Counter(proxy.kind for proxy in room.proxies)

    report = {
        "schema_version": "1.0",
        "room_id": room.room_id,
        "plan": {
            "path": annotation.image.path,
            "sha256": sha256_file(image_path),
            "width_px": annotation.image.width_px,
            "height_px": annotation.image.height_px,
        },
        "meters_per_pixel": calibration.meters_per_pixel,
        "ceiling_height_m": room.ceiling_height_m,
        "counts_by_semantic_kind": {
            "walls": len(room.walls),
            "openings": len(room.openings),
            "proxies": dict(sorted(proxy_counts.items())),
        },
        "sources": {
            "room": {
                "scale": _source(room.scale_source),
                "ceiling_height": _source(room.ceiling_height_source),
            },
            "walls": [
                {
                    "id": wall.id,
                    "geometry": _source(wall.geometry_source),
                    "thickness": _source(wall.thickness_source),
                }
                for wall in room.walls
            ],
            "openings": [
                {
                    "id": opening.id,
                    "position": _source(opening.position_source),
                    "vertical": _source(opening.vertical_source),
                }
                for opening in room.openings
            ],
            "proxies": [
                {
                    "id": proxy.id,
                    "footprint": _source(proxy.footprint_source),
                    "height": _source(proxy.height_source),
                }
                for proxy in room.proxies
            ],
        },
        "warnings": WARNINGS,
    }
    _atomic_write_text(
        Path(output),
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    )


def _source(source: SourceRef) -> dict[str, object]:
    return {
        "kind": source.kind,
        "reference": source.reference,
        "confidence": source.confidence,
    }


def _asset_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPOSITORY_ROOT / path


def _number(value: float) -> str:
    return f"{value:g}"


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
