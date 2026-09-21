"""Render a validated capture plan as a self-contained offline field guide."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import struct
import tempfile
from dataclasses import asdict
from html import escape
from pathlib import Path
from typing import Any

from .capture import CapturePass, CapturePlan, CaptureShot
from .errors import ValidationError
from .model import RoomModel
from .plan import PlanAnnotation, PlanCalibration


GENERATOR_VERSION = "astra-house-capture-pack/1.0"


def write_capture_pack(
    plan: CapturePlan,
    annotation: PlanAnnotation,
    room: RoomModel,
    source_plan_path: Path,
    output_dir: Path,
) -> Path:
    """Validate and atomically write the three-file offline capture package."""
    plan.validate(room)
    annotation.validate()
    if annotation.target.room_id != room.room_id:
        raise ValidationError(
            f"annotation room_id {annotation.target.room_id!r} does not match "
            f"{room.room_id!r}"
        )
    if plan.room_id != annotation.target.room_id:
        raise ValidationError(
            f"capture room_id {plan.room_id!r} does not match annotation "
            f"{annotation.target.room_id!r}"
        )

    source_plan_path = Path(source_plan_path)
    try:
        plan_image = source_plan_path.read_bytes()
    except OSError as error:
        raise ValidationError(
            f"cannot read source floor plan {source_plan_path}: {error}"
        ) from error
    _validate_png(plan_image, annotation)

    canonical_plan = _json_bytes(asdict(plan))
    canonical_room = _json_bytes(room.to_dict())
    hashes = {
        "capture_plan_sha256": hashlib.sha256(canonical_plan).hexdigest(),
        "floorplan_sha256": hashlib.sha256(plan_image).hexdigest(),
        "room_model_sha256": hashlib.sha256(canonical_room).hexdigest(),
    }
    intake = _build_intake(plan)
    report = {
        "capture_id": plan.capture_id,
        "generator_version": GENERATOR_VERSION,
        "pass_counts": {item.id: len(item.shots) for item in plan.passes},
        "room_id": room.room_id,
        "shot_count": len(plan.shots),
        "source_hashes": hashes,
        "status": "valid",
    }
    html = _render_html(plan, annotation, plan_image, hashes)

    rendered = {
        "capture-intake.json": _json_bytes(intake),
        "capture-pack-report.json": _json_bytes(report),
        "index.html": html.encode("utf-8"),
    }
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in rendered.items():
        _atomic_write(output_dir / name, content)
    return output_dir / "index.html"


def _validate_png(data: bytes, annotation: PlanAnnotation) -> None:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValidationError("source floor plan must be a valid PNG")
    width, height = struct.unpack(">II", data[16:24])
    if (width, height) != (annotation.image.width_px, annotation.image.height_px):
        raise ValidationError(
            "source floor-plan dimensions do not match annotation: "
            f"expected {annotation.image.width_px}x{annotation.image.height_px}, "
            f"found {width}x{height}"
        )


def _build_intake(plan: CapturePlan) -> dict[str, Any]:
    pass_by_shot = {
        shot.id: capture_pass.id
        for capture_pass in plan.passes
        for shot in capture_pass.shots
    }
    return {
        "capture_id": plan.capture_id,
        "room_id": plan.room_id,
        "schema_version": "1.0",
        "shots": [
            {
                "assigned_shot_id": shot.id,
                "dimensions_px": None,
                "exif_capture_time": None,
                "exif_orientation": None,
                "pass_id": pass_by_shot[shot.id],
                "planned_order": index,
                "sha256": None,
                "source_filename": None,
            }
            for index, shot in enumerate(plan.shots, start=1)
        ],
    }


def _render_html(
    plan: CapturePlan,
    annotation: PlanAnnotation,
    plan_image: bytes,
    hashes: dict[str, str],
) -> str:
    image_data = base64.b64encode(plan_image).decode("ascii")
    map_svg = _render_route_svg(plan, annotation, image_data)
    wall_rows = "".join(
        "<tr>"
        f"<th scope=\"row\"><code>{escape(review.wall_id)}</code></th>"
        f"<td>{escape(review.role)}</td>"
        f"<td>{escape(', '.join(review.opening_ids) or 'none')}</td>"
        "</tr>"
        for review in plan.wall_review
    )
    pass_sections = "".join(_render_pass(plan, item) for item in plan.passes)
    lens_label = plan.device_profile.lens.replace("1x ", "1× ")
    source_hash = hashes["floorplan_sha256"]

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>宿舍右卧室 · 48 张诊断拍摄包</title>
  <style>
    :root {{ color-scheme: light; --ink:#18211c; --muted:#5d6b63; --paper:#f6f4ed;
      --card:#fffef9; --line:#d8d4c7; --green:#145f45; --mint:#dff2e9;
      --orange:#bd5b24; --blue:#245b78; }}
    * {{ box-sizing:border-box; }}
    html {{ background:#e9e5da; }}
    body {{ margin:0; color:var(--ink); background:var(--paper); font:16px/1.55
      ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    main {{ width:min(1180px, 100%); margin:auto; padding:28px 22px 72px; }}
    h1 {{ margin:.15em 0; font-size:clamp(2rem,5vw,4.8rem); line-height:1.02;
      letter-spacing:-.045em; max-width:880px; }}
    h2 {{ margin:2.2rem 0 .8rem; font-size:clamp(1.45rem,3vw,2.2rem); }}
    h3 {{ margin:.15rem 0 .55rem; line-height:1.2; }}
    p {{ max-width:78ch; }}
    code {{ font-family:ui-monospace, SFMono-Regular, Menlo, monospace; font-size:.9em; }}
    .eyebrow {{ color:var(--green); font-weight:800; letter-spacing:.13em;
      text-transform:uppercase; }}
    .lede {{ font-size:1.12rem; color:var(--muted); max-width:72ch; }}
    .hero-meta, .grid-2, .check-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; }}
    .hero-meta {{ grid-template-columns:repeat(4,minmax(0,1fr)); margin:28px 0; }}
    .stat, .card, .shot, .map-card {{ background:var(--card); border:1px solid var(--line);
      border-radius:16px; box-shadow:0 8px 26px rgba(37,48,41,.06); }}
    .stat {{ padding:15px; }}
    .stat strong {{ display:block; font-size:1.3rem; }}
    .card {{ padding:20px; }}
    .notice {{ border-left:5px solid var(--orange); }}
    .ok {{ border-left:5px solid var(--green); }}
    table {{ width:100%; border-collapse:collapse; background:var(--card); }}
    th, td {{ padding:10px 12px; border-bottom:1px solid var(--line); text-align:left;
      vertical-align:top; }}
    thead th {{ color:#fff; background:var(--green); }}
    .table-wrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:14px; }}
    .orientation {{ display:grid; grid-template-columns:84px 1fr; gap:18px; align-items:center; }}
    .compass {{ width:80px; aspect-ratio:1; border:1px solid var(--line); border-radius:50%;
      display:grid; place-items:center; position:relative; font-weight:800; color:var(--green); }}
    .compass span {{ position:absolute; font-size:.72rem; }}
    .compass .n {{ top:2px; }} .compass .s {{ bottom:2px; }}
    .compass .e {{ right:5px; }} .compass .w {{ left:5px; }}
    .compass b {{ font-size:1.35rem; transform:rotate(45deg); }}
    .map-card {{ padding:12px; overflow:hidden; }}
    .map-card svg {{ display:block; width:100%; height:auto; background:#fff; border-radius:10px; }}
    .legend {{ display:flex; flex-wrap:wrap; gap:14px; margin:10px 4px 2px; color:var(--muted); font-size:.9rem; }}
    .swatch {{ display:inline-block; width:20px; height:4px; margin-right:6px; vertical-align:middle; }}
    .pass-head {{ display:flex; gap:14px; align-items:baseline; flex-wrap:wrap; margin-top:36px; }}
    .pass-pill {{ background:var(--green); color:white; border-radius:999px; padding:5px 11px; font-weight:800; }}
    .shot-grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }}
    .shot {{ padding:15px; break-inside:avoid; }}
    .shot-id {{ color:var(--green); font:800 1.1rem ui-monospace, SFMono-Regular, monospace; }}
    .shot-meta {{ color:var(--muted); font-size:.85rem; margin:.2rem 0 .6rem; }}
    .targets {{ display:flex; flex-wrap:wrap; gap:5px; margin-top:10px; }}
    .target {{ background:var(--mint); color:#124633; border-radius:999px; padding:3px 8px;
      font:700 .74rem ui-monospace, SFMono-Regular, monospace; }}
    ul.checks {{ list-style:none; padding:0; margin:.5rem 0; }}
    ul.checks li {{ margin:.55rem 0; padding-left:1.7rem; position:relative; }}
    ul.checks li::before {{ content:"□"; position:absolute; left:0; color:var(--green); font-weight:900; }}
    .hash {{ overflow-wrap:anywhere; font-size:.76rem; color:var(--muted); }}
    footer {{ margin-top:48px; padding-top:18px; border-top:1px solid var(--line); color:var(--muted); }}
    @media (max-width:900px) {{ .hero-meta {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
      .shot-grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} }}
    @media (max-width:720px) {{ main {{ padding:20px 14px 52px; }}
      .grid-2, .check-grid, .shot-grid, .hero-meta {{ grid-template-columns:1fr; }}
      .orientation {{ grid-template-columns:72px 1fr; }} th, td {{ padding:8px; font-size:.84rem; }} }}
    @media print {{ html, body {{ background:white; }} main {{ width:100%; padding:0; }}
      .stat, .card, .shot, .map-card {{ box-shadow:none; }} .shot-grid {{ grid-template-columns:repeat(2,1fr); }} }}
  </style>
</head>
<body>
<main>
  <header>
    <div class="eyebrow">Diagnostic capture 01 · 可离线使用</div>
    <h1>宿舍右卧室<br>48 张拍摄路线</h1>
    <p class="lede">目标不是拍“好看照片”，而是先验证相机能否沿一条连续路线恢复位置。站位可以为避开家具小幅移动，但顺序、目标和相邻照片的重叠不要改变。</p>
    <div class="hero-meta">
      <div class="stat"><small>设备</small><strong>{escape(plan.device_profile.model)}</strong></div>
      <div class="stat"><small>镜头</small><strong>{escape(lens_label)}</strong></div>
      <div class="stat"><small>格式</small><strong>{escape(plan.device_profile.orientation)} · {escape(plan.device_profile.aspect_ratio)} · {escape(plan.device_profile.file_format)}</strong></div>
      <div class="stat"><small>照片总数</small><strong>{plan.expected_image_count}</strong></div>
    </div>
  </header>

  <section class="grid-2">
    <article class="card ok">
      <h2 style="margin-top:0">Xiaomi 17 Ultra 设置</h2>
      <ul class="checks">
        <li>普通“照片”模式，横屏 4:3，JPG。</li>
        <li>全程只用 <strong>{escape(lens_label)}</strong> 主摄；不要切超广角或长焦。</li>
        <li>关闭 50 MP、RAW、人像、全景、长曝光、连拍、动态照片、数字变焦和视频。</li>
        <li>固定一种 Leica 风格；关闭滤镜和水印。</li>
        <li>闪光灯关闭；房灯、窗帘和显示屏状态全程不变。</li>
      </ul>
    </article>
    <article class="card notice">
      <h2 style="margin-top:0">定位能力说明</h2>
      <p><strong>Laser focus ≠ LiDAR。</strong> 小米的激光对焦只帮助相机对焦，本流程不会把它当作房间深度扫描。</p>
      <p><strong>ARCore: optional / unverified。</strong> 本批次不依赖 ARCore；普通照片的位置会在后处理阶段通过相邻照片的视觉重叠求解。</p>
      <p><strong>不要混用手机。</strong> 这 48 张全部用同一台 Xiaomi 17 Ultra。iPhone 重拍应建立新的 capture ID。</p>
    </article>
  </section>

  <section>
    <h2>先确认方向与墙体</h2>
    <div class="grid-2">
      <div class="card orientation">
        <div class="compass"><span class="n">东 E</span><span class="e">南 S</span><span class="s">西 W</span><span class="w">北 N</span><b>↑</b></div>
        <p><strong>户型图方向：</strong>上方是东（双窗），右边是南，左边是北，下方两段朝西。圆弧只表示门扇，不用于判断门属于哪面墙。</p>
      </div>
      <div class="card notice">
        <p><strong>浴室门位置锁定：</strong><code>bath-door-south</code> 位于 <code>wall-02</code>（衣柜旁、图中下方的朝西墙）。<code>wall-03</code> 只是连接回墙，没有门洞。</p>
      </div>
    </div>
    <div class="table-wrap" style="margin-top:18px">
      <table>
        <thead><tr><th>墙 ID</th><th>复核角色</th><th>开口</th></tr></thead>
        <tbody>{wall_rows}</tbody>
      </table>
    </div>
  </section>

  <section>
    <h2>路线图：先顺时针走 A01 → A08</h2>
    <p>圆点是近似站位，不是测量控制点。若站位被床、椅子或杂物挡住，就移动到最近的安全空位；不要挪家具，也不要改变拍摄顺序。</p>
    <div class="map-card">
      {map_svg}
      <div class="legend"><span><i class="swatch" style="background:#145f45"></i>结构环拍路线</span><span><i class="swatch" style="background:#bd5b24"></i>门窗开口</span><span><i class="swatch" style="background:#245b78"></i>房间边界</span></div>
    </div>
  </section>

  <section>
    <h2>现场清单</h2>
    <div class="check-grid">
      <article class="card"><h3>拍摄前</h3><ul class="checks"><li>擦净主摄镜头。</li><li>确认电量与至少 2 GB 空间。</li><li>房灯全部打开，窗帘固定；之后不要改变。</li><li>暂停电视、风扇和会动的屏幕。</li><li>确认当前为 1×、4:3、JPG、横屏。</li></ul></article>
      <article class="card"><h3>拍摄中</h3><ul class="checks"><li>双手持机，约胸口高度。</li><li>每次按快门前停稳一拍。</li><li>相邻照片保留约 70–80% 重叠。</li><li>窗玻璃、镜子、纯色墙都要连同有纹理的边缘一起拍。</li><li>明显模糊立即补拍，但先不要删除原片。</li></ul></article>
      <article class="card"><h3>拍摄后</h3><ul class="checks"><li>应有 48 张计划照片；补拍可多，不可少。</li><li>快速检查四个 pass 都已完成。</li><li>不要在手机上改名、裁切、调色或压缩。</li><li>记下跳过、重复或大幅移动过的站位。</li></ul></article>
      <article class="card"><h3>上传</h3><ul class="checks"><li>把本批次所有原图放入一个文件夹或 ZIP。</li><li>一次性上传原文件，不经聊天软件转发。</li><li>另附一条备注：哪些编号跳过、重拍或移动过。</li><li>文件名先保持手机原样，之后用 EXIF 时间映射编号。</li></ul></article>
    </div>
  </section>

  <section><h2>48 张逐张指引</h2>{pass_sections}</section>

  <footer>
    <div>Capture ID: <code>{escape(plan.capture_id)}</code> · Generator: <code>{GENERATOR_VERSION}</code></div>
    <div class="hash">Floor-plan SHA-256: <code>{source_hash}</code></div>
    <div class="hash">Capture-plan SHA-256: <code>{hashes['capture_plan_sha256']}</code></div>
  </footer>
</main>
</body>
</html>
"""


def _render_route_svg(
    plan: CapturePlan, annotation: PlanAnnotation, image_data: str
) -> str:
    calibration = PlanCalibration.from_annotation(annotation)
    width = annotation.image.width_px
    height = annotation.image.height_px
    floor_points = " ".join(
        f"{point.x:g},{point.y:g}" for point in annotation.target.floor_polygon_px
    )
    opening_lines = "".join(
        f'<line x1="{item.start_px.x:g}" y1="{item.start_px.y:g}" '
        f'x2="{item.end_px.x:g}" y2="{item.end_px.y:g}">'
        f"<title>{escape(item.id)}</title></line>"
        for item in annotation.openings
    )

    structure_pass = next(item for item in plan.passes if item.id == "A")
    stations = [
        (
            group.shots[0].id.split("-")[0],
            plan.station(group.station_id).standing_point_m,
            list(group.shots),
        )
        for group in structure_pass.groups
    ]
    projected = [calibration.room_to_pixel(point) for _, point, _ in stations]
    route_points = projected + projected[:1]
    route = " ".join(f"{point.x:.2f},{point.y:.2f}" for point in route_points)
    markers = "".join(
        _render_station_marker(index, station_id, point, shots, pixel)
        for index, ((station_id, point, shots), pixel) in enumerate(
            zip(stations, projected, strict=True), start=1
        )
    )
    return f"""<svg viewBox="0 0 {width} {height}" role="img" aria-labelledby="map-title map-desc">
  <title id="map-title">宿舍右卧室 8 点顺时针拍摄路线</title>
  <desc id="map-desc">在原始户型图上叠加房间边界、门窗和 A01 到 A08 的近似站位。</desc>
  <defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#145f45"/></marker></defs>
  <image href="data:image/png;base64,{image_data}" x="0" y="0" width="{width}" height="{height}" opacity=".58"/>
  <polygon points="{floor_points}" fill="#dff2e9" fill-opacity=".38" stroke="#245b78" stroke-width="5"/>
  <g stroke="#bd5b24" stroke-width="8" stroke-linecap="round">{opening_lines}</g>
  <polyline points="{route}" fill="none" stroke="#145f45" stroke-width="5" stroke-linejoin="round" stroke-dasharray="10 7" marker-end="url(#arrow)"/>
  <g>{markers}</g>
</svg>"""


def _render_station_marker(
    index: int,
    station_id: str,
    point: Any,
    shots: list[CaptureShot],
    pixel: Any,
) -> str:
    ids = ", ".join(shot.id for shot in shots)
    title = escape(
        f"{station_id} · ({point.x:.2f}, {point.y:.2f} m) · {ids}"
    )
    return (
        f'<g><circle cx="{pixel.x:.2f}" cy="{pixel.y:.2f}" r="15" '
        'fill="#fffef9" stroke="#145f45" stroke-width="5">'
        f"<title>{title}</title></circle>"
        f'<text x="{pixel.x:.2f}" y="{pixel.y + 5:.2f}" text-anchor="middle" '
        'font-size="13" font-weight="800" fill="#145f45" pointer-events="none">'
        f"{index}</text></g>"
    )


def _render_pass(plan: CapturePlan, capture_pass: CapturePass) -> str:
    shots = "".join(
        _render_shot(shot, plan.station(group.station_id).standing_point_m)
        for group in capture_pass.groups
        for shot in group.shots
    )
    return (
        '<div class="pass-head">'
        f'<span class="pass-pill">Pass {escape(capture_pass.id)}</span>'
        f"<h3>{escape(capture_pass.title)} · {len(capture_pass.shots)} 张</h3>"
        "</div>"
        f"<p>{escape(capture_pass.purpose)}</p>"
        f'<div class="shot-grid">{shots}</div>'
    )


def _render_shot(shot: CaptureShot, standing_point_m: Any) -> str:
    pitch = {"level": "平拍", "up": "向上", "down": "向下"}[shot.pitch]
    targets = "".join(
        f'<span class="target">{escape(target)}</span>' for target in shot.target_ids
    )
    return (
        '<article class="shot">'
        f'<div class="shot-id">□ {escape(shot.id)}</div>'
        f'<div class="shot-meta">站位约 ({standing_point_m.x:.2f}, '
        f'{standing_point_m.y:.2f}) m · {pitch}</div>'
        f"<div>{escape(shot.instruction)}</div>"
        f'<div class="targets">{targets}</div>'
        "</article>"
    )


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _atomic_write(path: Path, content: bytes) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
