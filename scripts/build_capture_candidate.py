"""Build a separate, unapproved route candidate without altering frozen sources.

This deterministic proposal uses full measured anchor spans and local wall
patches. It changes shot counts/semantics and must be reviewed before adoption.
It passes the same production geometry gate; it never writes coverage approval.
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path

from astra_house.capture import CapturePlan
from astra_house.capture_geometry import (
    first_boundary_hit, quantize_deg, quantize_m, segment_inside_polygon,
)
from astra_house.capture_pack import write_capture_pack
from astra_house.io import load_room
from astra_house.measurements import MeasurementSet
from astra_house.model import Vec2
from astra_house.plan import PlanAnnotation


def wall_points(wall, fraction=0.5, z=1.45):
    """A recognisable 1 m wall patch, bounded by the actual segment."""
    half = min(0.5 / wall.length_m, 0.4)
    center = min(1 - half, max(half, fraction))
    return [[wall.start.x + t * (wall.end.x - wall.start.x),
             wall.start.y + t * (wall.end.y - wall.start.y), z]
            for t in (center - half, center + half)]


def anchor_points(room, target_id):
    """Preserve full measured width/depth, or the full bed/desk top outline."""
    opening = next((o for o in room.openings if o.id == target_id), None)
    if opening:
        wall = next(w for w in room.walls if w.id == opening.wall_id)
        return [[wall.start.x + d * (wall.end.x - wall.start.x) / wall.length_m,
                 wall.start.y + d * (wall.end.y - wall.start.y) / wall.length_m,
                 1.45] for d in (opening.offset_m, opening.offset_m + opening.width_m)]
    proxy = next(p for p in room.proxies if p.id == target_id)
    if abs(proxy.yaw_rad) > 1e-9:
        raise ValueError("Candidate authoring recipe requires reviewed axis-aligned proxies")
    x0, x1 = proxy.center.x - proxy.size.x / 2, proxy.center.x + proxy.size.x / 2
    y0, y1 = proxy.center.y - proxy.size.y / 2, proxy.center.y + proxy.size.y / 2
    if target_id == "closet":
        return [[x0, y1, 1.45], [x1, y1, 1.45]]
    z = proxy.center.z + proxy.size.z / 2
    return [[x, y, z] for x, y in ((x0, y0), (x0, y1), (x1, y1), (x1, y0))]


def feasible_view(station, points, room, optics):
    origin = Vec2.from_value(station["standing_point_m"])
    xy = [Vec2(p[0], p[1]) for p in points]
    if any(not segment_inside_polygon(origin, p, room.floor_polygon) for p in xy):
        return None
    angles = [math.degrees(math.atan2(p.y-origin.y, p.x-origin.x)) for p in xy]
    unwrapped = [angles[0] + (a-angles[0]+180) % 360 - 180 for a in angles]
    usable = optics["horizontal_fov_deg"] - 2 * optics["coverage_margin_deg"]
    if quantize_deg(max(unwrapped)-min(unwrapped)) > usable:
        return None
    angle = math.radians((max(unwrapped)+min(unwrapped))/2)
    aim, distance = first_boundary_hit(origin, Vec2(origin.x+math.cos(angle), origin.y+math.sin(angle)), room.floor_polygon)
    if distance < 0.5:
        return None
    vertical = [math.degrees(math.atan2(p[2]-height, math.hypot(p[0]-origin.x, p[1]-origin.y)))
                for p in points for height in (optics["camera_height_m"]-optics["camera_height_tolerance_m"],
                                                optics["camera_height_m"]+optics["camera_height_tolerance_m"])]
    pitch_options = list(range(-45, -19)) + list(range(-15, 11)) + list(range(15, 46))
    good = [pitch for pitch in pitch_options if all(abs(quantize_deg(a-pitch)) <= optics["vertical_fov_deg"]/2 for a in vertical)]
    if not good:
        return None
    pitch = min(good, key=lambda p: (abs(p-(max(vertical)+min(vertical))/2), abs(p)))
    return {"aim_point_m": [quantize_m(aim.x), quantize_m(aim.y)],
            "framing_points_m": [[quantize_m(v) for v in point] for point in points],
            "pitch": "up" if pitch >= 15 else "down" if pitch <= -20 else "level", "pitch_deg": pitch}


def make_candidate(source, room):
    data = copy.deepcopy(source)
    data.pop("coverage_review", None)
    data["capture_id"] = source["capture_id"] + "-candidate-02"
    data["modes"] = []
    stations = data["stations"]
    required = [a["id"] for a in data["scale_anchors"]]
    views = []

    def add_views(target_id, points, count, purpose, instruction):
        candidates = [(s, feasible_view(s, points, room, data["device_profile"])) for s in stations]
        candidates = [(s, v) for s, v in candidates if v is not None]
        # Closet depth is the visible east side; do not choose its hidden back.
        if target_id == "closet":
            candidates = [(s, v) for s, v in candidates if s["standing_point_m"][1] > points[0][1]]
        if len(candidates) < count:
            raise ValueError(f"{target_id}: need {count} feasible distinct stations, got {len(candidates)}")
        selected = []
        while len(selected) < count:
            def rank(item):
                station, _ = item
                pos = station["standing_point_m"]
                baseline = min((math.dist(pos, prev[0]["standing_point_m"]) for prev in selected), default=0)
                used = sum(v[0] == station["id"] for v in views)
                return (baseline, -used, -station["number"])
            choice = max(candidates, key=rank)
            candidates.remove(choice); selected.append(choice)
        if count >= 2 and max(math.dist(a[0]["standing_point_m"], b[0]["standing_point_m"]) for a in selected for b in selected) < 0.5:
            raise ValueError(f"{target_id}: insufficient baseline")
        batch = [(s["id"], {**v, "target_ids": [target_id], "instruction": instruction}, purpose) for s, v in selected]
        views.extend(batch)
        return batch

    for wall in room.walls:
        add_views(wall.id, wall_points(wall), 2, "Structure",
                  f"Frame the central approximately 1 m patch of {wall.id} at lens height, retaining texture and local wall context. Do not try to fit the entire wall.")
    for anchor in data["scale_anchors"]:
        target = anchor["target_id"]
        extent = "the full top outline (all four corners)" if target in {"bed-full", "desk"} else "both ends of the measured depth" if target == "closet" else "both ends of this opening's measured width at lens height"
        add_views(target, anchor_points(room, target), 2, "Measured anchors",
                  f"Frame {target}: keep {extent} visible in one photograph. This width/depth view does not require the entire opening height. Keep both doors closed.")
    for wall in room.walls:
        add_views(wall.id, wall_points(wall, z=0), 1, "Floor seams",
                  f"Tilt down to include a continuous approximately 1 m floor-to-wall seam on {wall.id}; keep visible floor texture around it. Record a skip if furniture hides the seam.")
    lite = list(views)
    for wall in room.walls:
        for fraction in (0.25, 0.75):
            add_views(wall.id, wall_points(wall, fraction=fraction), 1, "Additional wall patches",
                      f"Frame the local {wall.id} patch centered {fraction:.0%} along its modeled segment; retain textured context and overlap with adjacent patches.")
    for wall in room.walls:
        add_views(wall.id, wall_points(wall, z=room.ceiling_height_m), 1, "Ceiling seams",
                  f"Tilt up toward the central ceiling-to-wall seam of {wall.id}. Keep a continuous seam and surrounding wall visible.")
    for anchor in data["scale_anchors"]:
        # Select four distinct stations then add only the two not used in lite.
        target = anchor["target_id"]
        base = [v for v in lite if v[1]["target_ids"] == [target] and v[2] == "Measured anchors"]
        feasible = [(s, feasible_view(s, anchor_points(room, target), room, data["device_profile"])) for s in stations]
        feasible = [(s,v) for s,v in feasible if v is not None and s["id"] not in {a[0] for a in base} and (target != "closet" or s["standing_point_m"][1] > anchor_points(room,target)[0][1])]
        detail_only = False
        if len(feasible) < 2 and target == "bed-full":
            # The full bed is already measured from two stations. Nearer views
            # intentionally add surface texture, not another whole-bed claim.
            proxy = next(p for p in room.proxies if p.id == target)
            patch = [[proxy.center.x+dx, proxy.center.y+dy, proxy.center.z+proxy.size.z/2]
                     for dx,dy in ((-.3,-.3),(-.3,.3),(.3,.3),(.3,-.3))]
            feasible = [(s, feasible_view(s, patch, room, data["device_profile"])) for s in stations if s["id"] not in {a[0] for a in base}]
            feasible = [(s,v) for s,v in feasible if v is not None]
            detail_only = True
        if len(feasible) < 2:
            raise ValueError(f"{target}: additional independent views unavailable")
        feasible.sort(key=lambda item: (-min(math.dist(item[0]["standing_point_m"], next(s for s in stations if s["id"] == prev[0])["standing_point_m"]) for prev in base), item[0]["number"]))
        for station, view in feasible[:2]:
            instruction = "Frame the central 60 cm square of bed-top texture. This is an additional local detail image, not a whole-bed scale measurement." if detail_only else base[0][1]["instruction"] + " Additional independent station view."
            views.append((station["id"], {**view, "target_ids": [target], "instruction": instruction}, "Additional anchors and detail"))
    for prefix, rows in (("CL", lite), ("CS", views)):
        passes = []
        for purpose in dict.fromkeys(row[2] for row in rows):
            groups = []
            for station in stations:
                selected = [(i, row) for i, row in enumerate(rows, 1) if row[0] == station["id"] and row[2] == purpose]
                if not selected:
                    continue
                groups.append({"id": f"{prefix}-G{len(passes)+1}-{station['id']}", "title": f"{purpose} at station {station['number']}", "purpose": purpose,
                               "station_id": station["id"], "next_hint": "Move only after recording this group; reconfirm after changing station.",
                               "shots": [{"id": f"{prefix}-{i:03d}", **row[1]} for i,row in selected]})
            passes.append({"id": f"{prefix}-P{len(passes)+1}", "title": purpose, "purpose": purpose, "groups": groups})
        data["modes"].append({"id": f"candidate-{'lite' if prefix == 'CL' else 'standard'}-{len(rows)}", "title": f"Draft candidate · {len(rows)} photographs",
                              "description": "Separate proposed route; geometry checks are provisional and do not certify texture, physical occlusion or reconstruction success.",
                              "expected_image_count": len(rows), "risk_note": "UNAPPROVED CANDIDATE. Keep both doors closed; restart under a new capture ID if door state changes. Check actual visibility and station safety in the room. Phone/FOV trial and route review remain required.",
                              "required_scale_anchor_ids": required, "passes": passes})
    return data


def main():
    project = Path("projects/dorm-right-bedroom")
    source = json.loads((project / "capture-plan.json").read_text())
    room = load_room(project / "room.json")
    data = make_candidate(source, room)
    plan = CapturePlan.from_dict(data)
    measurements = MeasurementSet.from_dict(json.loads((project / "measurements.json").read_text()))
    annotation = PlanAnnotation.from_dict(json.loads((project / "plan-annotation.json").read_text()))
    plan.validate(room, measurements)
    output = Path("build/dorm-right-bedroom/capture-candidate")
    result = write_capture_pack(plan, annotation, room, measurements, Path(annotation.image.path), output)
    # Keep proposed source outside the exact three-file package for review.
    (output.parent / "capture-plan-candidate.json").write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n")
    report = json.loads((output / "capture-pack-report.json").read_text())
    print(json.dumps({"preview": str(result), "status": report["status"], "counts": report["mode_counts"],
                      "warnings": {mode["mode_id"]: len(mode["issues"]) for mode in report["coverage"]}}, indent=2))


if __name__ == "__main__":
    main()
