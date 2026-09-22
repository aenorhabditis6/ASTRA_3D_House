from __future__ import annotations

import copy
import json
import re
import tempfile
import unittest
from dataclasses import asdict, replace
from html import escape
from html.parser import HTMLParser
from pathlib import Path

from astra_house.capture import CapturePlan
from astra_house.capture_geometry import analyze_capture_plan
from astra_house.capture_pack import build_capture_intake, build_capture_report, write_capture_pack
from astra_house.capture_web import render_capture_html
from astra_house.errors import ValidationError
from astra_house.io import load_room
from astra_house.measurements import MeasurementSet
from astra_house.plan import PlanAnnotation
from tests.test_capture_geometry import valid_geometry_data

PROJECT = Path("projects/dorm-right-bedroom")


class Tags(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class CapturePackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capture_data = json.loads((PROJECT / "capture-plan.json").read_text())
        cls.project_plan = CapturePlan.from_dict(cls.capture_data)
        cls.plan = CapturePlan.from_dict(valid_geometry_data())
        cls.annotation = PlanAnnotation.from_dict(json.loads((PROJECT / "plan-annotation.json").read_text()))
        cls.room = load_room(PROJECT / "room.json")
        cls.measurements = MeasurementSet.from_dict(json.loads((PROJECT / "measurements.json").read_text()))
        cls.source_png = Path(cls.annotation.image.path)
        cls.coverage = analyze_capture_plan(cls.plan, cls.room, "a" * 64)
        cls.project_coverage = analyze_capture_plan(cls.project_plan, cls.room, "a" * 64)

    def write(self, output, plan=None):
        return write_capture_pack(plan or self.plan, self.annotation, self.room, self.measurements, self.source_png, output)

    def preview(self, plan=None):
        # This tests only rendering of the reviewed route, whose actual geometry
        # is release-blocked. No coverage issue is removed from embedded data.
        plan = plan or self.project_plan
        coverage = analyze_capture_plan(plan, self.room, "a" * 64)
        report = {
            "status": "blocked — SIMULATION ONLY", "generator_version": "test/2.0",
            "source_hashes": {}, "mode_plan_sha256": {c.mode_id: c.mode_plan_sha256 for c in coverage},
            "coverage_review_status": {c.mode_id: "blocked" for c in coverage},
        }
        return render_capture_html(plan, self.annotation, self.source_png.read_bytes(), coverage, report)

    def test_writes_three_deterministic_self_contained_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            self.write(output)
            first = {p.name: p.read_bytes() for p in output.iterdir()}
            self.assertEqual(sorted(first), ["capture-intake.json", "capture-pack-report.json", "index.html"])
            intake = json.loads(first["capture-intake.json"])
            report = json.loads(first["capture-pack-report.json"])
            self.assertEqual(intake["schema_version"], "2.0")
            self.assertEqual(report["schema_version"], "2.0")
            self.assertEqual(report["status"], "draft")
            self.assertEqual(report["mode_counts"], {"test-2": 2})
            self.assertEqual(report["group_counts"], {"test-2": 2})
            self.assertEqual(report["station_counts"], {"test-2": 2})
            self.assertEqual(report["pass_counts"], {"test-2": {"P": 2}})
            self.assertEqual(report["coverage_review_status"], {"test-2": "missing"})
            self.assertEqual(report["coverage_review_digests"], {"test-2": None})
            self.assertEqual(len(report["source_hashes"]), 4)
            self.assertEqual(report["generator_version"], "astra-house-capture-pack/2.0")
            self.write(output)
            self.assertEqual(first, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_intake_has_both_ordered_ledgers_and_exact_null_metadata(self):
        intake = build_capture_intake(self.project_plan, self.project_coverage)
        ids = []
        for mode in self.project_plan.modes:
            rows = intake["modes"][mode.id]["shots"]
            self.assertEqual([r["assigned_shot_id"] for r in rows], [s.id for s in mode.shots])
            self.assertEqual([r["planned_order"] for r in rows], list(range(1, len(rows) + 1)))
            self.assertEqual(len(rows), mode.expected_image_count)
            for row in rows:
                ids.append(row["assigned_shot_id"])
                self.assertEqual(set(row), {"assigned_shot_id", "pass_id", "group_id", "station_id", "planned_order", "source_filename", "sha256", "dimensions_px", "exif"})
                self.assertIsNone(row["source_filename"])
                self.assertEqual(row["exif"], {"date_time_original": None, "sub_sec_time_original": None, "offset_time_original": None, "orientation": None})
        self.assertEqual(len(set(ids)), 72)

    def test_exact_reviews_are_required_for_publishability(self):
        data = valid_geometry_data()
        coverage = self.coverage[0]
        codes = sorted(i.code for i in coverage.issues if i.severity == "warning")
        self.assertTrue(codes)
        data["coverage_review"] = {"test-2": {"mode_plan_sha256": coverage.mode_plan_sha256,
            "warning_codes": codes, "reviewer": "test", "reviewed_at": "2026-09-21T20:00:00Z"}}
        current = CapturePlan.from_dict(data)
        report = build_capture_report(current, self.coverage, {})
        self.assertEqual(report["status"], "publishable")
        self.assertEqual(report["coverage_review_status"], {"test-2": "current"})
        self.assertRegex(report["coverage_review_digests"]["test-2"], r"^[a-f0-9]{64}$")
        data["coverage_review"]["test-2"]["warning_codes"] = []
        self.assertEqual(build_capture_report(CapturePlan.from_dict(data), self.coverage, {})["coverage_review_status"]["test-2"], "stale_codes")
        data["coverage_review"]["test-2"]["mode_plan_sha256"] = "b" * 64
        self.assertEqual(build_capture_report(CapturePlan.from_dict(data), self.coverage, {})["coverage_review_status"]["test-2"], "stale_hash")
        self.assertEqual(analyze_capture_plan(current, self.room, "a" * 64)[0].mode_plan_sha256, coverage.mode_plan_sha256)

    def test_geometry_errors_do_not_replace_any_existing_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            sentinels = {name: b"old" for name in ("index.html", "capture-intake.json", "capture-pack-report.json")}
            for name, value in sentinels.items():
                (output / name).write_bytes(value)
            with self.assertRaisesRegex(ValidationError, "capture coverage errors"):
                self.write(output, self.project_plan)
            self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, sentinels)

    def test_invalid_plan_and_png_fail_before_output_creation(self):
        data = valid_geometry_data()
        data["wall_review"]["wall-00"]["opening_ids"].remove("window-west")
        data["wall_review"]["wall-01"]["opening_ids"].append("window-west")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            with self.assertRaises(ValidationError):
                self.write(output, CapturePlan.from_dict(data))
            self.assertFalse(output.exists())
            malformed = Path(directory) / "bad.png"
            malformed.write_bytes(b"not a PNG")
            with self.assertRaisesRegex(ValidationError, "valid PNG"):
                write_capture_pack(self.plan, self.annotation, self.room, self.measurements, malformed, output)
            self.assertFalse(output.exists())

    def test_static_html_contains_complete_routes_and_geometry(self):
        html = self.preview()
        tags = Tags(html).tags
        self.assertEqual(len([a for t, a in tags if a.get("class") == "station-marker"]), 8)
        self.assertEqual(len([a for t, a in tags if a.get("class") == "shot-ray"]), 72)
        self.assertEqual(len([a for t, a in tags if a.get("class") == "shot-cone"]), 72)
        static_ids = {a["data-static-shot-id"] for t, a in tags if "data-static-shot-id" in a}
        self.assertEqual(static_ids, {s.id for mode in self.project_plan.modes for s in mode.shots})
        embedded = json.loads(re.search(r'<script id="capture-data" type="application/json">(.*?)</script>', html, re.S)[1])
        for mode in self.project_plan.modes:
            for shot in mode.shots:
                self.assertIn(escape(shot.instruction, quote=True), html)
                self.assertIn(shot.id, embedded["shot_geometry"])
        self.assertEqual(len(embedded["station_geometry"]), 8)
        self.assertEqual([m["id"] for m in embedded["modes"]], [m.id for m in self.project_plan.modes])
        for phrase in ("both doors closed", "Xiaomi 17 Ultra", "1× Leica 23 mm", "AI-scene", "Dynamic Shot", "wall-03 has no opening", "original filenames", "EXIF", "aria-live=\"polite\""):
            self.assertIn(phrase, html)
        for coverage in self.project_coverage:
            for issue in coverage.issues:
                self.assertIn(escape(issue.code), html)

    def test_hostile_text_is_escaped_in_static_html_and_json(self):
        data = copy.deepcopy(self.capture_data)
        hostile = '</script><img src=x onerror=alert(1)> & \u2028\u2029'
        data["modes"][0]["passes"][0]["groups"][0]["shots"][0]["instruction"] = hostile
        html = self.preview(CapturePlan.from_dict(data))
        self.assertIn(escape(hostile, quote=True), html)
        embedded = json.loads(re.search(r'<script id="capture-data" type="application/json">(.*?)</script>', html, re.S)[1])
        self.assertEqual(embedded["modes"][0]["passes"][0]["groups"][0]["shots"][0]["instruction"], hostile)
        self.assertFalse(any(t == "img" for t, a in Tags(html).tags))

    def test_no_runtime_network_dependencies(self):
        html = self.preview()
        for tag, attrs in Tags(html).tags:
            self.assertNotEqual(tag, "link")
            if tag in {"script", "img", "image", "iframe"}:
                for attribute in ("src", "href"):
                    self.assertFalse(re.match(r"(?:https?:)?//", attrs.get(attribute, "")))
        for forbidden in ("fetch(", "XMLHttpRequest", "serviceWorker.register"):
            self.assertNotIn(forbidden, html)


if __name__ == "__main__":
    unittest.main()
