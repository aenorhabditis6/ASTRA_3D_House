"""Semantic static guide and safe, self-contained browser enhancement assets."""
from __future__ import annotations

import base64
import json
from dataclasses import asdict
from html import escape
from importlib import resources
from typing import Any

from .capture import CapturePlan
from .capture_geometry import ModeCoverage, quantize_m
from .plan import PlanAnnotation, PlanCalibration


def _text(value: Any) -> str:
    return escape(str(value), quote=True)


def _script_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return (encoded.replace("&", "\\u0026").replace("<", "\\u003c")
            .replace(">", "\\u003e").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def _asset_text(name: str) -> str:
    return resources.files("astra_house").joinpath("assets", name).read_text(encoding="utf-8")


def embedded_capture_data(
    plan: CapturePlan, annotation: PlanAnnotation,
    coverage: tuple[ModeCoverage, ...], report: dict[str, Any],
) -> dict[str, Any]:
    calibration = PlanCalibration.from_annotation(annotation)

    def project(point: Any) -> dict[str, float]:
        pixel = calibration.room_to_pixel(point)
        return {"x": quantize_m(pixel.x), "y": quantize_m(pixel.y)}

    station_geometry = {station.id: project(station.standing_point_m) for station in plan.stations}
    shot_by_id = {shot.id: shot for mode in plan.modes for shot in mode.shots}
    shot_geometry = {
        shot.shot_id: {
            "station_id": shot.station_id, "mode_id": mode.mode_id,
            "start_px": station_geometry[shot.station_id],
            "aim_px": project(shot_by_id[shot.shot_id].aim_point_m),
            "boundary_px": project(shot.boundary_hit_m),
            "cone_px": [project(point) for point in shot.cone_polygon_m],
        }
        for mode in coverage for shot in mode.shots
    }
    plan_data = asdict(plan)
    mode_hashes = {item.mode_id: item.mode_plan_sha256 for item in coverage}
    plan_data["modes"] = [{**mode, "mode_plan_sha256": mode_hashes[mode["id"]]} for mode in plan_data["modes"]]
    return {**plan_data, "coverage": [asdict(item) for item in coverage],
            "report": report, "station_geometry": station_geometry,
            "shot_geometry": shot_geometry}


def _map_svg(plan: CapturePlan, annotation: PlanAnnotation, image: bytes, data: dict[str, Any]) -> str:
    polygon = " ".join(f"{point.x:g},{point.y:g}" for point in annotation.target.floor_polygon_px)
    # Crop to the surveyed room to keep stations legible on a phone. The source
    # image retains its original coordinate system and reviewed pixel geometry.
    points = annotation.target.floor_polygon_px
    left, top = min(p.x for p in points) - 32, min(p.y for p in points) - 32
    width = max(p.x for p in points) - left + 32
    height = max(p.y for p in points) - top + 32
    layers = []
    for shot_id, geometry in data["shot_geometry"].items():
        start, aim = geometry["start_px"], geometry["boundary_px"]
        attrs = f'data-shot-id="{_text(shot_id)}" data-mode-id="{_text(geometry["mode_id"])}"'
        cone = " ".join(f'{p["x"]},{p["y"]}' for p in geometry["cone_px"])
        layers.append(f'<polygon class="shot-cone" {attrs} points="{cone}"/>')
        layers.append(f'<line class="shot-ray" {attrs} x1="{start["x"]}" y1="{start["y"]}" x2="{aim["x"]}" y2="{aim["y"]}"><title>{_text(shot_id)}</title></line>')
    markers = []
    for station in plan.stations:
        pixel = data["station_geometry"][station.id]
        label = f"{station.id}: {station.label}"
        markers.append(f'<g class="station-marker" data-station-id="{_text(station.id)}" role="button" tabindex="0" aria-label="{_text(label)}" transform="translate({pixel["x"]} {pixel["y"]})"><title>{_text(label)}</title><circle class="mode-ring" r="14"/><circle class="station-fill" r="10"/><text y="4" text-anchor="middle">{station.number}</text></g>')
    openings = "".join(f'<line x1="{o.start_px.x}" y1="{o.start_px.y}" x2="{o.end_px.x}" y2="{o.end_px.y}"><title>{_text(o.id)}</title></line>' for o in annotation.openings)
    return f'''<svg id="map-view" viewBox="{left} {top} {width} {height}" role="group" aria-labelledby="map-title map-desc">
<title id="map-title">Room stations and capture directions</title><desc id="map-desc">East at the top, south at the right. Numbered station buttons below provide the same navigation. Rays show planned directions, not measured camera positions.</desc>
<defs><marker id="shot-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0 L10,5 L0,10Z" fill="currentColor"/></marker></defs>
<image href="data:image/png;base64,{base64.b64encode(image).decode('ascii')}" width="{annotation.image.width_px}" height="{annotation.image.height_px}" opacity=".45"/>
<polygon class="room-boundary" points="{polygon}"/><g class="openings">{openings}</g>
<g id="shot-geometry">{''.join(layers)}</g><g id="station-markers">{''.join(markers)}</g></svg>'''


def _static_modes(plan: CapturePlan) -> str:
    modes = []
    for mode in plan.modes:
        passes = []
        for capture_pass in mode.passes:
            groups = []
            for group in capture_pass.groups:
                station = plan.station(group.station_id)
                shots = []
                for shot in group.shots:
                    label_id = f"static-{mode.id}-{shot.id}"
                    shots.append(f'''<li class="static-shot" data-static-shot-id="{_text(shot.id)}"><label for="{_text(label_id)}"><input type="checkbox" id="{_text(label_id)}"/> <strong>{_text(shot.id)}</strong> · {_text(shot.pitch)} ({shot.pitch_deg:g}°)</label><p>{_text(shot.instruction)}</p><p class="shot-meta">Targets: {_text(', '.join(shot.target_ids))}. Aim: ({shot.aim_point_m.x:.4f}, {shot.aim_point_m.y:.4f}) m.</p></li>''')
                hint = f'<p>Next: {_text(group.next_hint)}</p>' if group.next_hint else ''
                groups.append(f'<section class="static-group"><h4>{_text(group.id)} · {_text(group.title)}</h4><p>{_text(group.purpose)}</p><p>Station {_text(station.id)} · {_text(station.label)} · ({station.standing_point_m.x:.4f}, {station.standing_point_m.y:.4f}) m</p><ol>{"".join(shots)}</ol>{hint}</section>')
            passes.append(f'<section><h3>{_text(capture_pass.id)} · {_text(capture_pass.title)}</h3><p>{_text(capture_pass.purpose)}</p>{"".join(groups)}</section>')
        modes.append(f'<section data-static-mode-id="{_text(mode.id)}"><h2>{_text(mode.title)} · {mode.expected_image_count} shots</h2><p>{_text(mode.description)}</p><p class="notice">{_text(mode.risk_note)}</p>{"".join(passes)}</section>')
    return ''.join(modes)


def render_capture_html(
    plan: CapturePlan, annotation: PlanAnnotation, plan_image: bytes,
    coverage: tuple[ModeCoverage, ...], report: dict[str, Any],
) -> str:
    data = embedded_capture_data(plan, annotation, coverage, report)
    summaries, warnings = [], []
    for mode in plan.modes:
        recommended = ' · Recommended' if mode.id == 'standard-48' else ''
        summaries.append(f'<article class="mode-card"><h3>{_text(mode.title)}{recommended}</h3><p>{mode.expected_image_count} shots · {len(mode.groups)} groups</p><p>{_text(mode.description)}</p><p>{_text(mode.risk_note)}</p><button type="button" data-mode-id="{_text(mode.id)}">Start {_text(mode.title)}</button><p class="hash">Mode SHA-256: {_text(report["mode_plan_sha256"][mode.id])}</p></article>')
    for mode in coverage:
        issues = ''.join(f'<li><code>{_text(i.code)}</code>: {_text(i.message)}</li>' for i in sorted(mode.issues, key=lambda i: i.code))
        warnings.append(f'<section><h3>{_text(mode.mode_id)} coverage · {_text(report["coverage_review_status"].get(mode.mode_id, "missing"))}</h3><ul>{issues}</ul></section>')
    wall_rows = ''.join(f'<tr><th scope="row">{_text(w.wall_id)}</th><td>{_text(w.role)}</td><td>{_text(", ".join(w.opening_ids) or "none")}</td></tr>' for w in plan.wall_review)
    stations = ''.join(f'<button type="button" data-station-id="{_text(s.id)}">{s.number} · {_text(s.id)} · {_text(s.label)}</button>' for s in plan.stations)
    try:
        javascript = _asset_text('capture-guide.js')
    except FileNotFoundError:
        javascript = ''  # A source checkout can still render the complete static guide.
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><title>{_text(plan.room_id)} · Capture guide</title><style>{_asset_text('capture-guide.css')}</style></head>
<body><main><header><p class="eyebrow">ASTRA · Field capture pilot</p><h1>Room capture guide</h1><p>{_text(plan.room_id)} · Capture ID: <code>{_text(plan.capture_id)}</code></p><p class="notice">Release status: {_text(report['status'])}. Pilot: real Xiaomi device verification is still required.</p></header>
<p id="enhancement-warning" role="status"></p><noscript><p>JavaScript is disabled. Use the complete static guide and manual checkboxes below; export and saved progress are unavailable.</p></noscript>
<section id="interactive-guide" class="interactive-guide"><h2>Choose a route</h2><div id="mode-chooser" class="layout-grid">{''.join(summaries)}</div>
<div id="workflow" hidden><nav class="actions" aria-label="Capture actions"><button id="change-mode" type="button">Change mode</button><button id="export-progress" type="button">Export progress</button><button id="undo-action" type="button">Undo last action</button><button id="reset-mode" type="button">Reset this mode</button></nav><p id="progress-status" aria-live="polite"></p><div id="task-view"></div></div>
<p id="storage-warning" role="status"></p><div id="stale-states"></div>
<section id="export-panel" hidden><h2>Progress export</h2><label for="export-text">Progress JSON — metadata only</label><textarea id="export-text" aria-label="Progress JSON" readonly rows="10"></textarea><button id="copy-export" type="button">Copy JSON</button><button id="select-export" type="button">Select all for manual copy</button></section></section>
<section id="map-section" class="map-card"><h2>Stations and planned directions</h2>{_map_svg(plan, annotation, plan_image, data)}<div id="station-list" class="station-list" aria-label="Station navigation">{stations}</div><button class="interactive-only" id="toggle-diagnostics" type="button" aria-pressed="false">Show coverage diagnostics</button><p>Numbered circles: stations. Arrow: planned shot. Shaded cone: usable field of view. Current, completed, skipped/gap and upcoming states also use labels and line styles.</p></section>
<section id="camera-checklist"><h2>Before starting · Xiaomi 17 Ultra</h2><ul><li>Use the 1× Leica 23 mm main camera, landscape 4:3 JPG, on one phone for the entire route.</li><li>Keep one unchanged Leica style. Turn watermark, filters, AI-scene, HDR, flash, digital zoom and Dynamic Shot off.</li><li>Keep both doors closed: entry and bathroom. If a door state must change, restart under a new capture ID.</li><li>Keep room lights and curtains stable. Stop moving screens; keep people out of the scene. Clean the lens, charge the phone, and check free space.</li><li>Hold steadily at {_text(plan.device_profile.camera_height_m)} m ± {_text(plan.device_profile.camera_height_tolerance_m)} m. Laser focus is not LiDAR. ARCore: optional / unverified.</li></ul><p>Station confirmation is manual and visit-local. This guide cannot verify your position, camera settings, shutter action, or existence of photographs.</p></section>
<section><h2>Room orientation and wall review</h2><p>+X runs north-to-south; +Y runs west-to-east. Map top is east, right is south, left is north. wall-00 is east/double-window; wall-01 is south; wall-05 is north; wall-02 and wall-04 face west. Both legacy-named windows (window-west and window-east) belong to wall-00. bath-door-south belongs to wall-02. wall-03 has no opening.</p><div class="table-wrap"><table><thead><tr><th>Wall</th><th>Role</th><th>Openings</th></tr></thead><tbody>{wall_rows}</tbody></table></div></section>
<details id="coverage-diagnostics"><summary>Coverage warnings and review</summary>{''.join(warnings)}</details>
<details class="static-guide" open><summary>Complete printable instructions — all modes</summary><p>Choose one route per capture. The two ledgers are alternatives, not one combined batch.</p>{_static_modes(plan)}</details>
<section id="upload-guidance"><h2>Finish and upload</h2><p>Export progress JSON alongside all original photos in one folder or ZIP. Keep original filenames, bytes and EXIF. Do not rename, crop, compress, discard extras, or send through a recompressing message app. The export contains metadata only; this guide never reads or stores image bytes.</p><p>Completion is an operator report, not proof of shutter timing. Group order is inferred. EXIF time, subseconds and timezone guide later matching; missing EXIF, repeats, reopened shots or ambiguous matches require manual review. Unassigned images remain available.</p><h3>Keep one stable address</h3><p>Use current Chrome on the Xiaomi at one stable HTTPS URL, or the same Mac LAN HTTP origin for the whole capture. Keep the Mac powered, awake, lid open and server running. Open and reload the exact URL before starting. Direct file/content URLs, in-app browsers, Xiaomi Browser and message-app WebViews have unverified persistence/download. Browser storage may be cleared: export regularly and before reset.</p></section>
<footer><p>{_text(report['generator_version'])}</p>{''.join(f'<p class="hash">{_text(k)}: <code>{_text(v)}</code></p>' for k,v in sorted(report['source_hashes'].items()))}</footer>
</main><script id="capture-data" type="application/json">{_script_json(data)}</script><script>{javascript}</script></body></html>'''
