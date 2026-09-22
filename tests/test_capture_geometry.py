from __future__ import annotations

import copy
import hashlib
import json
import math
import unittest
from dataclasses import replace
from pathlib import Path

from astra_house.capture import CapturePlan
from astra_house.capture_geometry import (
    analyze_capture_plan,
    first_boundary_hit,
    intersect_intervals,
    mode_plan_sha256,
    point_strictly_inside_polygon,
    quantize_deg,
    quantize_m,
    raise_for_coverage_errors,
    relative_bearing_deg,
    segment_inside_polygon,
    _shot_wall_intervals,
    _wall_floor_seam_is_covered,
)
from astra_house.errors import ValidationError
from astra_house.io import load_room
from astra_house.measurements import MeasurementSet
from astra_house.model import Vec2
from tests.test_capture import valid_capture_data_v2


ROOM = Path("projects/dorm-right-bedroom/room.json")
MEASUREMENTS = Path("projects/dorm-right-bedroom/measurements.json")
CAPTURE_PLAN = Path("projects/dorm-right-bedroom/capture-plan.json")


def load_plan_data() -> dict[str, object]:
    return json.loads(CAPTURE_PLAN.read_text(encoding="utf-8"))


def room_digest() -> str:
    room = load_room(ROOM)
    return hashlib.sha256(
        json.dumps(room.to_dict(), sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def mode_data(data: dict[str, object], mode_id: str) -> dict[str, object]:
    return next(item for item in data["modes"] if item["id"] == mode_id)


def shot_data(mode: dict[str, object], shot_id: str) -> dict[str, object]:
    return next(
        shot
        for capture_pass in mode["passes"]
        for group in capture_pass["groups"]
        for shot in group["shots"]
        if shot["id"] == shot_id
    )


def group_data(mode: dict[str, object], group_id: str) -> dict[str, object]:
    return next(
        group
        for capture_pass in mode["passes"]
        for group in capture_pass["groups"]
        if group["id"] == group_id
    )


def analyze_data(data: dict[str, object]):
    return analyze_capture_plan(
        CapturePlan.from_dict(data), load_room(ROOM), room_digest()
    )


def issue_codes(data: dict[str, object], mode_id: str = "lite-24") -> set[str]:
    coverage = next(item for item in analyze_data(data) if item.mode_id == mode_id)
    return {issue.code for issue in coverage.issues}


def valid_geometry_data() -> dict[str, object]:
    """Synthetic two-station window survey; never substitutes for project data."""
    data = valid_capture_data_v2()
    capture_pass = data["modes"][0]["passes"][0]
    first = capture_pass["groups"][0]
    first["shots"] = [first["shots"][0]]
    second = copy.deepcopy(first)
    second.update(id="G02", station_id="S02")
    second["shots"][0]["id"] = "T02"
    capture_pass["groups"] = [first, second]
    return data


class GeometryPrimitiveTest(unittest.TestCase):
    def test_quantizes_derived_geometry_half_up(self) -> None:
        self.assertEqual(quantize_m(1.23456), 1.2346)
        self.assertEqual(quantize_deg(-12.345), -12.35)

    def test_strict_containment_uses_one_centimetre_tolerance(self) -> None:
        polygon = (Vec2(0, 0), Vec2(4, 0), Vec2(4, 4), Vec2(0, 4))
        self.assertFalse(point_strictly_inside_polygon(Vec2(0.005, 2), polygon))
        self.assertTrue(point_strictly_inside_polygon(Vec2(0.011, 2), polygon))
        self.assertFalse(point_strictly_inside_polygon(Vec2(0.01004, 2), polygon))
        self.assertTrue(point_strictly_inside_polygon(Vec2(0.01006, 2), polygon))

    def test_rejects_segment_that_crosses_concave_notch(self) -> None:
        polygon = (
            Vec2(0, 0),
            Vec2(4, 0),
            Vec2(4, 4),
            Vec2(2, 4),
            Vec2(2, 2),
            Vec2(0, 2),
        )
        self.assertFalse(
            segment_inside_polygon(Vec2(1, 1), Vec2(3, 4), polygon)
        )
        # The brief's (1,1)->(3,3) example touches the reflex corner but
        # never leaves the polygon; inside/on interval semantics accept it.
        self.assertTrue(segment_inside_polygon(Vec2(1, 1), Vec2(3, 3), polygon))
        self.assertTrue(segment_inside_polygon(Vec2(2, 2), Vec2(2, 4), polygon))

    def test_accepts_quantized_boundary_endpoint_within_tolerance(self) -> None:
        polygon = (Vec2(0, 0), Vec2(4, 0), Vec2(4, 4), Vec2(0, 4))
        self.assertTrue(
            segment_inside_polygon(Vec2(1, 1), Vec2(4.00005, 3), polygon)
        )

    def test_finds_first_boundary_hit_from_aim_bearing(self) -> None:
        polygon = (Vec2(0, 0), Vec2(4, 0), Vec2(4, 4), Vec2(0, 4))
        hit, distance = first_boundary_hit(Vec2(1, 1), Vec2(2, 1), polygon)
        self.assertEqual(hit, Vec2(4.0, 1.0))
        self.assertEqual(distance, 3.0)

    def test_first_boundary_hit_does_not_skip_concave_occluder(self) -> None:
        polygon = (Vec2(0, 0), Vec2(4, 0), Vec2(4, 4), Vec2(2, 4), Vec2(2, 2), Vec2(0, 2))
        hit, distance = first_boundary_hit(Vec2(1, 1), Vec2(3, 4), polygon)
        self.assertEqual(hit, Vec2(1.6667, 2.0))
        self.assertEqual(distance, 1.2019)

    def test_relative_bearing_wraps_across_both_sides_of_180(self) -> None:
        def direction(degrees: float) -> Vec2:
            import math

            radians = math.radians(degrees)
            return Vec2(math.cos(radians), math.sin(radians))

        origin = Vec2(0, 0)
        self.assertEqual(
            quantize_deg(
                relative_bearing_deg(
                    origin, direction(179.0), direction(-179.0)
                )
            ),
            2.0,
        )
        self.assertEqual(
            quantize_deg(
                relative_bearing_deg(
                    origin, direction(-179.0), direction(179.0)
                )
            ),
            -2.0,
        )

    def test_intersects_parameter_intervals_analytically(self) -> None:
        self.assertEqual(
            intersect_intervals(((0.0, 0.4), (0.6, 1.0)), ((0.2, 0.8),)),
            ((0.2, 0.4), (0.6, 0.8)),
        )


class CoverageAnalysisTest(unittest.TestCase):
    def test_synthetic_feasible_route_has_no_errors_and_two_anchor_stations(self) -> None:
        data = valid_geometry_data()
        plan = CapturePlan.from_dict(data)
        plan.validate(load_room(ROOM), MeasurementSet.from_dict(json.loads(MEASUREMENTS.read_text())))
        coverage = analyze_data(data)
        raise_for_coverage_errors(coverage)
        self.assertEqual(coverage[0].anchor_station_baselines_m, (("window-west", 2, 1.0),))

    def test_checks_every_explicit_height_even_when_another_point_is_at_camera_height(self) -> None:
        data = valid_geometry_data()
        shot = data["modes"][0]["passes"][0]["groups"][0]["shots"][0]
        shot["framing_points_m"] += [[1.425, 4.2266, 1.45], [1.425, 4.2266, 3.3528]]
        self.assertIn("E_VERTICAL_FOV:T01", issue_codes(data, "test-2"))

    def test_occluded_wall_interval_splits_at_reflex_vertex(self) -> None:
        room = load_room(ROOM)
        polygon = (Vec2(0, 0), Vec2(4, 0), Vec2(4, 4), Vec2(2, 4), Vec2(2, 2), Vec2(0, 2))
        room = replace(room, floor_polygon=polygon)
        wall = replace(room.walls[0], start=Vec2(2, 4), end=Vec2(4, 4))
        shot = CapturePlan.from_dict(valid_geometry_data()).modes[0].shots[0]
        shot = replace(shot, aim_point_m=Vec2(3, 4))
        intervals = _shot_wall_intervals(Vec2(1, 0.5), shot, wall, room, 60.0)
        self.assertEqual(len(intervals), 1)
        self.assertAlmostEqual(intervals[0][0], 2.0 / 3.0)
        self.assertAlmostEqual(intervals[0][1], 1.0)

    def test_floor_seam_finds_visible_end_intervals_when_midpoint_is_above_frame(self) -> None:
        data = valid_geometry_data()
        data["stations"][0]["standing_point_m"] = [5.0, 1.0]
        data["modes"][0]["passes"][0]["groups"] = data["modes"][0]["passes"][0]["groups"][:1]
        shot = data["modes"][0]["passes"][0]["groups"][0]["shots"][0]
        shot.update(aim_point_m=[5.0, 10.0], pitch="up", pitch_deg=18.0)
        plan = CapturePlan.from_dict(data)
        room = load_room(ROOM)
        room = replace(room, floor_polygon=(Vec2(0, 0), Vec2(10, 0), Vec2(10, 10), Vec2(0, 10)))
        wall = replace(room.walls[0], start=Vec2(0, 10), end=Vec2(10, 10))
        self.assertLess(math.degrees(math.atan2(-1.55, 9.0)), -9.5)
        self.assertTrue(_wall_floor_seam_is_covered(plan, plan.modes[0], room, wall))

    def test_vertical_overlap_requires_compatible_horizontal_bearings(self) -> None:
        data = valid_geometry_data()
        group = data["modes"][0]["passes"][0]["groups"][0]
        up = copy.deepcopy(group["shots"][0])
        up.update(id="UP", aim_point_m=[2.0, 1.2694], pitch="up", pitch_deg=30.0)
        group["shots"].append(up)
        self.assertIn("W_VERTICAL_OVERLAP:S01", issue_codes(data, "test-2"))

    def test_horizontal_threshold_compares_quantized_angles(self) -> None:
        data = valid_geometry_data()
        group = data["modes"][0]["passes"][0]["groups"][0]
        shot = group["shots"][0]
        shot.update(aim_point_m=[2.0, 4.2266], target_ids=["wall-00"])
        def points(angle: float) -> list[list[float]]:
            return [[2.0 + (4.2266 - 2.0) * math.tan(math.radians(angle)), 4.2266, 1.45]]
        shot["framing_points_m"] = points(30.004)
        self.assertNotIn("E_HORIZONTAL_FOV:T01", issue_codes(data, "test-2"))
        shot["framing_points_m"] = points(30.006)
        self.assertIn("E_HORIZONTAL_FOV:T01", issue_codes(data, "test-2"))

    def test_unseen_anchor_points_do_not_earn_redundancy_credit(self) -> None:
        data = valid_geometry_data()
        data["modes"][0]["passes"][0]["groups"][1]["shots"][0]["aim_point_m"] = [3.0, 0.0]
        coverage = analyze_data(data)[0]
        self.assertEqual(coverage.anchor_station_baselines_m, (("window-west", 1, 0.0),))

    def test_route_adjacency_includes_return_leg_in_first_visit_order(self) -> None:
        coverage = analyze_data(load_plan_data())[0]
        self.assertEqual(coverage.adjacent_shared_spans_m[-1][:2], ("S08", "S01"))
        data = load_plan_data()
        data["stations"].reverse()
        self.assertEqual(analyze_data(data)[0].adjacent_shared_spans_m, coverage.adjacent_shared_spans_m)

    def test_reports_release_blocking_geometry_codes_with_stable_subjects(self) -> None:
        cases: list[tuple[str, str, object]] = []

        los = load_plan_data()
        shot_data(mode_data(los, "lite-24"), "L01-A")["aim_point_m"] = [3.0, 0.5]
        cases.append(("line of sight", "E_LOS_OUTSIDE_ROOM:L01-A", los))

        blocked = load_plan_data()
        next(item for item in blocked["stations"] if item["id"] == "S04")[
            "standing_point_m"
        ] = [3.8, 3.0]
        cases.append(("blocked station", "E_STATION_BLOCKED:S04", blocked))

        anchor = load_plan_data()
        lite = mode_data(anchor, "lite-24")
        for group_id in ("L05", "L07", "L10", "L11"):
            group_data(lite, group_id)["station_id"] = "S06"
        cases.append(
            ("anchor baseline", "E_ANCHOR_BASELINE:window-west", anchor)
        )

        horizontal = load_plan_data()
        shot = shot_data(mode_data(horizontal, "lite-24"), "L11-A")
        shot["aim_point_m"] = [2.2, 4.2266]
        shot["framing_points_m"] = [[4.2, 4.2266, 1.45]]
        shot["target_ids"] = ["wall-00"]
        cases.append(("horizontal FOV", "E_HORIZONTAL_FOV:L11-A", horizontal))

        vertical = load_plan_data()
        shot = shot_data(mode_data(vertical, "lite-24"), "L11-A")
        shot["aim_point_m"] = [2.2, 4.2266]
        shot["framing_points_m"] = [[2.2, 4.2266, 3.3528]]
        shot["target_ids"] = ["wall-00"]
        cases.append(("vertical FOV", "E_VERTICAL_FOV:L11-A", vertical))

        behind = load_plan_data()
        shot = shot_data(mode_data(behind, "lite-24"), "L11-A")
        shot["aim_point_m"] = [2.2, 4.2266]
        shot["framing_points_m"] = [[2.2, 1.2694, 1.45]]
        shot["target_ids"] = ["wall-04"]
        cases.append(
            ("target behind bearing", "E_TARGET_BEHIND_BEARING:L11-A", behind)
        )

        for label, expected, data in cases:
            with self.subTest(label):
                self.assertIn(expected, issue_codes(data))

    def test_reports_each_advisory_geometry_code(self) -> None:
        paired = load_plan_data()
        lite = mode_data(paired, "lite-24")
        left = shot_data(lite, "L01-A")
        left["aim_point_m"] = [0.0, 1.65]
        left["framing_points_m"] = [[0.0, 2.0, 1.45]]
        left["target_ids"] = ["wall-05"]
        right = shot_data(lite, "L01-B")
        right["aim_point_m"] = [4.9381, 1.65]
        right["framing_points_m"] = [[4.9381, 2.0, 1.45]]
        right["target_ids"] = ["wall-01"]
        self.assertIn("W_PAIRED_BEARING_GAP:L01", issue_codes(paired))

        adjacent = load_plan_data()
        lite = mode_data(adjacent, "lite-24")
        first = copy.deepcopy(group_data(lite, "L01"))
        second = copy.deepcopy(group_data(lite, "L02"))
        first["shots"] = [first["shots"][0]]
        second["shots"] = [second["shots"][0]]
        first["shots"][0].update(
            aim_point_m=[0.0, 2.0],
            framing_points_m=[[0.0, 2.0, 1.45]],
            target_ids=["wall-05"],
        )
        second["shots"][0].update(
            aim_point_m=[4.9381, 2.0],
            framing_points_m=[[4.9381, 2.0, 1.45]],
            target_ids=["wall-01"],
        )
        lite["passes"] = [
            {
                "id": "ADJ",
                "title": "Adjacent",
                "purpose": "Trigger shared span warning",
                "groups": [first, second],
            }
        ]
        lite["expected_image_count"] = 2
        lite["required_scale_anchor_ids"] = []
        self.assertIn(
            "W_ADJACENT_SHARED_SPAN:S01-S02", issue_codes(adjacent)
        )

        clearance = load_plan_data()
        next(item for item in clearance["stations"] if item["id"] == "S02")[
            "standing_point_m"
        ] = [2.15, 1.55]
        self.assertIn("W_STATION_CLEARANCE:S02", issue_codes(clearance))

        short_ray = load_plan_data()
        next(item for item in short_ray["stations"] if item["id"] == "S06")[
            "standing_point_m"
        ] = [2.2, 3.7]
        shot = shot_data(mode_data(short_ray, "lite-24"), "L11-A")
        shot["aim_point_m"] = [2.2, 4.2266]
        shot["framing_points_m"] = [[2.2, 4.2266, 1.45]]
        shot["target_ids"] = ["wall-00"]
        self.assertIn("W_SHORT_BOUNDARY_RAY:L11-A", issue_codes(short_ray))

        overlap = load_plan_data()
        lite = mode_data(overlap, "lite-24")
        group = copy.deepcopy(group_data(lite, "L11"))
        level = group["shots"][0]
        level.update(
            id="OVER-L",
            aim_point_m=[2.2, 4.2266],
            framing_points_m=[[2.2, 4.2266, 1.45]],
            pitch="level",
            pitch_deg=0.0,
            target_ids=["wall-00"],
        )
        up = copy.deepcopy(level)
        up.update(
            id="OVER-U",
            framing_points_m=[[2.2, 4.2266, 3.3528]],
            pitch="up",
            pitch_deg=45.0,
        )
        down = copy.deepcopy(level)
        down.update(
            id="OVER-D",
            framing_points_m=[[2.2, 4.2266, 0.0]],
            pitch="down",
            pitch_deg=-45.0,
        )
        group["id"] = "OVER"
        group["shots"] = [level, up, down]
        lite["passes"] = [
            {
                "id": "OVERLAP",
                "title": "Overlap",
                "purpose": "Trigger vertical overlap warning",
                "groups": [group],
            }
        ]
        lite["expected_image_count"] = 3
        lite["required_scale_anchor_ids"] = []
        self.assertIn("W_VERTICAL_OVERLAP:S06", issue_codes(overlap))

        seam = load_plan_data()
        lite = mode_data(seam, "lite-24")
        group = copy.deepcopy(group_data(lite, "L11"))
        group["shots"] = [group["shots"][0]]
        lite["passes"] = [
            {
                "id": "SEAM",
                "title": "Seam",
                "purpose": "Leave structural seams uncovered",
                "groups": [group],
            }
        ]
        lite["expected_image_count"] = 1
        lite["required_scale_anchor_ids"] = []
        self.assertIn("W_FLOOR_SEAM_GAP:wall-02", issue_codes(seam))
        self.assertIn("W_WALL_REDUNDANCY:wall-00", issue_codes(seam))

    @unittest.skip("Blocked: frozen stations/targets cannot fit 60-degree usable FOV; route revision required")
    def test_project_routes_have_no_geometry_errors(self) -> None:
        plan = CapturePlan.from_dict(load_plan_data())
        room = load_room(ROOM)
        measurements = MeasurementSet.from_dict(
            json.loads(MEASUREMENTS.read_text(encoding="utf-8"))
        )
        plan.validate(room, measurements)
        coverage = analyze_capture_plan(plan, room, room_digest())
        errors = [
            issue
            for mode in coverage
            for issue in mode.issues
            if issue.severity == "error"
        ]
        self.assertEqual(errors, [])
        lite = next(item for item in coverage if item.mode_id == "lite-24")
        self.assertIn(
            "W_WALL_REDUNDANCY:wall-03",
            {issue.code for issue in lite.issues},
        )
        self.assertTrue(
            all(
                count >= 2 and baseline >= 0.5
                for _, count, baseline in lite.anchor_station_baselines_m
            )
        )

    def test_project_routes_truthfully_reject_known_infeasible_shots(self) -> None:
        coverage = analyze_data(load_plan_data())
        with self.assertRaisesRegex(ValidationError, "E_HORIZONTAL_FOV:C04-A"):
            raise_for_coverage_errors(coverage)
        for mode_id, shot_id in (("lite-24", "L01-A"), ("standard-48", "C04-A")):
            issues = next(mode.issues for mode in coverage if mode.mode_id == mode_id)
            self.assertIn("E_HORIZONTAL_FOV:" + shot_id, {issue.code for issue in issues})
        self.assertIn("W_WALL_REDUNDANCY:wall-03", {issue.code for issue in coverage[0].issues})

    def test_fixed_entry_door_and_north_wall_cannot_share_a_usable_frame(self) -> None:
        plan = CapturePlan.from_dict(load_plan_data())
        room = load_room(ROOM)
        station = plan.station("S01").standing_point_m
        wall = next(w for w in room.walls if w.id == "wall-05")
        owner = next(w for w in room.walls if w.id == "wall-04")
        door = next(o for o in room.openings if o.id == "entry-door")
        # These are the nearest horizontal angular endpoints of the two
        # disjoint target silhouettes, independent of the selected aim point.
        door_left = Vec2(owner.start.x - door.width_m, owner.start.y)
        minimum_span = abs(relative_bearing_deg(station, wall.start, door_left))
        self.assertEqual(quantize_deg(minimum_span), 77.47)
        usable_fov = plan.device_profile.horizontal_fov_deg - 2 * plan.device_profile.coverage_margin_deg
        self.assertGreater(minimum_span, usable_fov)

    def test_outputs_are_quantized_and_diagnostics_are_stably_sorted(self) -> None:
        coverage = analyze_data(load_plan_data())
        for mode in coverage:
            self.assertEqual(len(mode.floor_seam_spans_m), 6)
            self.assertEqual(len(mode.ceiling_seam_spans_m), 6)
            for _, span in mode.floor_seam_spans_m + mode.ceiling_seam_spans_m:
                self.assertEqual(span, quantize_m(span))
                self.assertGreaterEqual(span, 0.0)
            self.assertEqual(
                [issue.code for issue in mode.issues],
                sorted(issue.code for issue in mode.issues),
            )
            for shot in mode.shots:
                self.assertEqual(shot.bearing_deg, quantize_deg(shot.bearing_deg))
                self.assertEqual(
                    shot.boundary_distance_m, quantize_m(shot.boundary_distance_m)
                )
                self.assertEqual(
                    shot.boundary_hit_m,
                    Vec2(
                        quantize_m(shot.boundary_hit_m.x),
                        quantize_m(shot.boundary_hit_m.y),
                    ),
                )

    def test_seam_union_does_not_double_count_repeated_shots(self) -> None:
        data = valid_geometry_data()
        shot = data["modes"][0]["passes"][0]["groups"][0]["shots"][0]
        shot.update(pitch="down", pitch_deg=-35.0)
        before = analyze_data(data)[0].floor_seam_spans_m
        self.assertGreater(dict(before)["wall-00"], 0.0)
        duplicate = copy.deepcopy(shot)
        duplicate["id"] = "DUP"
        data["modes"][0]["passes"][0]["groups"][0]["shots"].append(duplicate)
        self.assertEqual(analyze_data(data)[0].floor_seam_spans_m, before)

    def test_raise_for_coverage_errors_names_the_stable_code(self) -> None:
        data = load_plan_data()
        shot_data(mode_data(data, "lite-24"), "L01-A")["aim_point_m"] = [
            3.0,
            0.5,
        ]
        with self.assertRaisesRegex(ValidationError, "E_LOS_OUTSIDE_ROOM:L01-A"):
            raise_for_coverage_errors(analyze_data(data))


class CoverageHashTest(unittest.TestCase):
    def test_mode_hash_isolated_from_other_modes_and_coverage_review(self) -> None:
        plan = CapturePlan.from_dict(load_plan_data())
        digest = room_digest()
        lite_before = mode_plan_sha256(plan, plan.mode("lite-24"), digest)
        standard_before = mode_plan_sha256(plan, plan.mode("standard-48"), digest)
        changed_data = load_plan_data()
        changed_data["modes"][1]["passes"][0]["groups"][0]["shots"][0][
            "instruction"
        ] += " Recheck."
        changed = CapturePlan.from_dict(changed_data)
        self.assertEqual(
            lite_before,
            mode_plan_sha256(changed, changed.mode("lite-24"), digest),
        )
        self.assertNotEqual(
            standard_before,
            mode_plan_sha256(changed, changed.mode("standard-48"), digest),
        )
        changed_data["coverage_review"] = {
            "lite-24": {
                "mode_plan_sha256": lite_before,
                "warning_codes": [],
                "reviewer": "hash exclusion test",
                "reviewed_at": "2026-09-21T20:00:00Z",
            }
        }
        reviewed = CapturePlan.from_dict(changed_data)
        self.assertEqual(
            mode_plan_sha256(changed, changed.mode("lite-24"), digest),
            mode_plan_sha256(reviewed, reviewed.mode("lite-24"), digest),
        )
        self.assertEqual(
            mode_plan_sha256(changed, changed.mode("standard-48"), digest),
            mode_plan_sha256(reviewed, reviewed.mode("standard-48"), digest),
        )


if __name__ == "__main__":
    unittest.main()
