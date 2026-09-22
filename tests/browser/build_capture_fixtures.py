"""Render explicitly blocked UI simulations; never bypass package validation.

The unchanged pilot routes currently have hard geometry errors. These fixtures
exercise their complete operator interface through the real renderer while
retaining all diagnostics. They are not build-capture-pack release artifacts.
"""

import json
import hashlib
from pathlib import Path
from astra_house.capture import CapturePlan
from astra_house.capture_geometry import analyze_capture_plan
from astra_house.capture_web import render_capture_html
from astra_house.io import load_room
from astra_house.plan import PlanAnnotation


THIRD_MODE = {
    "id": "test-3",
    "title": "Third-mode fixture",
    "description": "Proves the renderer and controller are data-driven.",
    "expected_image_count": 1,
    "risk_note": "Browser-test fixture only.",
    "required_scale_anchor_ids": [],
    "passes": [{
        "id": "T-PASS", "title": "Fixture pass", "purpose": "Complete one generic mode.",
        "groups": [{
            "id": "T-G01", "title": "Fixture group", "purpose": "One wall view.",
            "station_id": "S01", "next_hint": None,
            "shots": [{
                "id": "T-ONLY", "aim_point_m": [0.0, 2.0],
                "framing_points_m": [[0.0, 2.0, 1.45]],
                "pitch": "level", "pitch_deg": 0.0, "target_ids": ["wall-05"],
                "instruction": "Frame the north wall from station 1.",
            }],
        }],
    }],
}


def main() -> None:
    project = Path("projects/dorm-right-bedroom")
    capture_data = json.loads((project / "capture-plan.json").read_text(encoding="utf-8"))
    capture_data.pop("coverage_review", None)
    annotation = PlanAnnotation.from_dict(json.loads((project / "plan-annotation.json").read_text()))
    room = load_room(project / "room.json")
    room_hash = hashlib.sha256(json.dumps(room.to_dict(), sort_keys=True).encode()).hexdigest()
    image = Path(annotation.image.path).read_bytes()
    for suffix in ("", "-third-mode"):
        if suffix:
            capture_data["modes"].append(THIRD_MODE)
        plan = CapturePlan.from_dict(capture_data)
        coverage = analyze_capture_plan(plan, room, room_hash)
        report = {
            "status": "BLOCKED — SIMULATION ONLY; geometry errors prevent field release",
            "generator_version": "astra-house-browser-simulation/2.0",
            "source_hashes": {},
            "mode_plan_sha256": {mode.mode_id: mode.mode_plan_sha256 for mode in coverage},
            "coverage_review_status": {mode.mode_id: "blocked" for mode in coverage},
        }
        output = Path(f"build/browser-simulation/capture-pack{suffix}")
        output.mkdir(parents=True, exist_ok=True)
        (output / "index.html").write_text(render_capture_html(plan, annotation, image, coverage, report), encoding="utf-8")
    print("Built browser-only SIMULATION fixtures; production geometry validation remains required.")


if __name__ == "__main__":
    main()
