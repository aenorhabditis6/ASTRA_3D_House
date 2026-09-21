from __future__ import annotations

import copy
import hashlib
import json
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from astra_house.capture import CapturePlan
from astra_house.errors import ValidationError
from astra_house.io import load_room
from astra_house.measurements import MeasurementSet
from astra_house.model import Vec2


ROOM = Path("projects/dorm-right-bedroom/room.json")
MEASUREMENTS = Path("projects/dorm-right-bedroom/measurements.json")
CAPTURE_PLAN = Path("projects/dorm-right-bedroom/capture-plan.json")
LEGACY_CAPTURE_PLAN = Path("tests/fixtures/dorm-right-bedroom-capture-plan-v1.json")


def load_measurements(path: Path) -> MeasurementSet:
    return MeasurementSet.from_dict(json.loads(path.read_text(encoding="utf-8")))


def valid_capture_data_v2() -> dict[str, object]:
    return {
        "schema_version": "2.0",
        "room_id": "dorm-right-bedroom",
        "capture_id": "domain-test",
        "device_profile": {
            "make": "Xiaomi", "model": "Xiaomi 17 Ultra",
            "lens": "1x Leica 23 mm main", "orientation": "landscape",
            "aspect_ratio": "4:3", "file_format": "JPG",
            "arcore_status": "unverified_optional",
            "equivalent_focal_length_mm": 23.0,
            "horizontal_fov_deg": 70.0, "vertical_fov_deg": 55.0,
            "fov_source": "test fixture", "fov_confidence": 0.5,
            "camera_height_m": 1.45, "camera_height_tolerance_m": 0.10,
            "coverage_margin_deg": 5.0,
        },
        "wall_review": {
            "wall-00": {"role": "east", "opening_ids": ["window-west", "window-east"]},
            "wall-01": {"role": "south", "opening_ids": []},
            "wall-02": {"role": "bath", "opening_ids": ["bath-door-south"]},
            "wall-03": {"role": "return", "opening_ids": []},
            "wall-04": {"role": "entry", "opening_ids": ["entry-door"]},
            "wall-05": {"role": "north", "opening_ids": []},
        },
        "scale_anchors": [{
            "id": "window-west", "target_id": "window-west",
            "measurement_ids": ["window-west-width"],
        }],
        "stations": [
            {"id": "S01", "number": 1, "standing_point_m": [2.0, 2.0], "label": "first"},
            {"id": "S02", "number": 2, "standing_point_m": [3.0, 2.0], "label": "second"},
        ],
        "modes": [{
            "id": "test-2", "title": "Test", "description": "Generic mode",
            "expected_image_count": 2, "risk_note": "Fixture only",
            "required_scale_anchor_ids": ["window-west"],
            "passes": [{
                "id": "P", "title": "Pass", "purpose": "Domain fixture",
                "groups": [{
                    "id": "G01", "title": "Group", "purpose": "Two views",
                    "station_id": "S01", "next_hint": None,
                    "shots": [
                        {
                            "id": "T01", "aim_point_m": [1.425, 4.2266],
                            "framing_points_m": [[0.79, 4.2266, 1.66], [2.06, 4.2266, 1.66]],
                            "pitch": "level", "pitch_deg": 0.0,
                            "target_ids": ["wall-00", "window-west"],
                            "instruction": "Frame the west window and surrounding east wall."
                        },
                        {
                            "id": "T02", "aim_point_m": [0.0, 2.0],
                            "framing_points_m": [[0.0, 2.0, 1.45]],
                            "pitch": "level", "pitch_deg": 0.0,
                            "target_ids": ["wall-05"],
                            "instruction": "Frame the north wall."
                        },
                    ],
                }],
            }],
        }],
    }


def legacy_tuple(shot: dict[str, object]) -> tuple[object, ...]:
    return (
        shot["id"], tuple(shot["standing_point_m"]), shot["pitch"],
        tuple(shot["target_ids"]), shot["instruction"],
    )


def normalized_tuple(
    plan: CapturePlan, group: object, shot: object
) -> tuple[object, ...]:
    station = plan.station(group.station_id)
    return (
        shot.id, tuple(station.standing_point_m.to_list()), shot.pitch,
        tuple(shot.target_ids), shot.instruction,
    )


class CapturePlanTest(unittest.TestCase):
    def validate(self, data: dict[str, object]) -> CapturePlan:
        plan = CapturePlan.from_dict(data)
        plan.validate(load_room(ROOM), load_measurements(MEASUREMENTS))
        return plan

    def test_frozen_schema_v1_fixture_is_the_reviewed_raw_source(self) -> None:
        raw = LEGACY_CAPTURE_PLAN.read_bytes()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            "2e8549b60a862eff8a58a75fcbce4812358325a372da33f4a03c819067fdd170",
        )
        data = json.loads(raw)
        self.assertEqual(data["schema_version"], "1.0")
        self.assertEqual(
            [shot["id"] for item in data["passes"] for shot in item["shots"]],
            [
                *(f"A{station:02d}-{view}" for station in range(1, 9) for view in ("L", "C", "R")),
                *(f"B{station:02d}-{view}" for station in range(1, 5) for view in ("U", "D")),
                *(f"C{station:02d}-{view}" for station in range(1, 5) for view in ("A", "B")),
                *(f"D{station:02d}" for station in range(1, 9)),
            ],
        )

    def test_parses_and_validates_immutable_schema_v2_domain(self) -> None:
        plan = self.validate(valid_capture_data_v2())
        self.assertEqual(plan.station("S01").number, 1)
        self.assertEqual(plan.mode("test-2").shots[0].aim_point_m, Vec2(1.425, 4.2266))
        self.assertEqual(plan.mode("test-2").groups[0].id, "G01")
        with self.assertRaises(FrozenInstanceError):
            plan.station("S01").number = 7

    def test_schema_v2_validation_requires_measurements(self) -> None:
        plan = CapturePlan.from_dict(valid_capture_data_v2())
        with self.assertRaises(TypeError):
            plan.validate(load_room(ROOM))

    def test_rejects_schema_v1(self) -> None:
        data = json.loads(LEGACY_CAPTURE_PLAN.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(ValidationError, "unsupported.*schema.*'1.0'"):
            CapturePlan.from_dict(data).validate(load_room(ROOM), load_measurements(MEASUREMENTS))

    def test_rejects_duplicate_station_id(self) -> None:
        data = valid_capture_data_v2()
        data["stations"][1]["id"] = "S01"
        with self.assertRaisesRegex(ValidationError, "duplicate station id 'S01'"):
            self.validate(data)

    def test_rejects_duplicate_station_number(self) -> None:
        data = valid_capture_data_v2()
        data["stations"][1]["number"] = 1
        with self.assertRaisesRegex(ValidationError, "duplicate station number 1"):
            self.validate(data)

    def test_rejects_duplicate_mode_id(self) -> None:
        data = valid_capture_data_v2()
        data["modes"].append(copy.deepcopy(data["modes"][0]))
        with self.assertRaisesRegex(ValidationError, "duplicate mode id 'test-2'"):
            self.validate(data)

    def test_rejects_duplicate_pass_and_group_ids_within_mode(self) -> None:
        duplicate_pass = valid_capture_data_v2()
        duplicate_pass["modes"][0]["passes"].append(copy.deepcopy(duplicate_pass["modes"][0]["passes"][0]))
        with self.assertRaisesRegex(ValidationError, "duplicate capture pass id 'P'"):
            self.validate(duplicate_pass)

        duplicate_group = valid_capture_data_v2()
        duplicate_group["modes"][0]["passes"][0]["groups"].append(
            copy.deepcopy(duplicate_group["modes"][0]["passes"][0]["groups"][0])
        )
        with self.assertRaisesRegex(ValidationError, "duplicate capture group id 'G01'"):
            self.validate(duplicate_group)

    def test_rejects_globally_duplicate_shot_ids(self) -> None:
        data = valid_capture_data_v2()
        third = copy.deepcopy(data["modes"][0])
        third["id"] = "another"
        data["modes"].append(third)
        with self.assertRaisesRegex(ValidationError, "duplicate shot id 'T01'"):
            self.validate(data)

    def test_rejects_unknown_group_station(self) -> None:
        data = valid_capture_data_v2()
        data["modes"][0]["passes"][0]["groups"][0]["station_id"] = "S99"
        with self.assertRaisesRegex(ValidationError, "unknown station 'S99'"):
            self.validate(data)

    def test_rejects_unknown_target(self) -> None:
        data = valid_capture_data_v2()
        data["modes"][0]["passes"][0]["groups"][0]["shots"][0]["target_ids"] = ["missing-target"]
        with self.assertRaisesRegex(ValidationError, "unknown target 'missing-target'"):
            self.validate(data)

    def test_rejects_empty_group_and_mode_count_mismatch(self) -> None:
        empty = valid_capture_data_v2()
        empty["modes"][0]["passes"][0]["groups"][0]["shots"] = []
        with self.assertRaisesRegex(ValidationError, "capture group 'G01' has no shots"):
            self.validate(empty)

        short = valid_capture_data_v2()
        short["modes"][0]["passes"][0]["groups"][0]["shots"].pop()
        with self.assertRaisesRegex(ValidationError, "expected 2 shots, found 1"):
            self.validate(short)

    def test_rejects_invalid_pitch_category_and_range(self) -> None:
        unsupported = valid_capture_data_v2()
        unsupported["modes"][0]["passes"][0]["groups"][0]["shots"][0]["pitch"] = "sideways"
        with self.assertRaisesRegex(ValidationError, "unsupported pitch 'sideways'"):
            self.validate(unsupported)

        mismatched = valid_capture_data_v2()
        mismatched["modes"][0]["passes"][0]["groups"][0]["shots"][0]["pitch_deg"] = 30.0
        with self.assertRaisesRegex(ValidationError, "pitch_deg 30.0.*'level'"):
            self.validate(mismatched)

    def test_rejects_aim_point_too_close_or_outside_floor(self) -> None:
        close = valid_capture_data_v2()
        close["modes"][0]["passes"][0]["groups"][0]["shots"][0]["aim_point_m"] = [2.1, 2.0]
        with self.assertRaisesRegex(ValidationError, "at least 0.50 m"):
            self.validate(close)

        outside = valid_capture_data_v2()
        outside["modes"][0]["passes"][0]["groups"][0]["shots"][0]["aim_point_m"] = [-1.0, 3.0]
        with self.assertRaisesRegex(ValidationError, "aim point is outside floor polygon"):
            self.validate(outside)

    def test_quantizes_aim_distance_half_up_before_threshold(self) -> None:
        rounds_to_boundary = valid_capture_data_v2()
        rounds_to_boundary["modes"][0]["passes"][0]["groups"][0]["shots"][0][
            "aim_point_m"
        ] = [2.49996, 2.0]
        try:
            self.validate(rounds_to_boundary)
        except ValidationError as error:
            self.fail(f"0.49996 m should quantize to the accepted boundary: {error}")

        remains_below = valid_capture_data_v2()
        remains_below["modes"][0]["passes"][0]["groups"][0]["shots"][0][
            "aim_point_m"
        ] = [2.49994, 2.0]
        with self.assertRaisesRegex(ValidationError, "at least 0.50 m"):
            self.validate(remains_below)

    def test_rejects_station_on_boundary_or_in_concave_notch(self) -> None:
        boundary = valid_capture_data_v2()
        boundary["stations"][0]["standing_point_m"] = [0.0, 2.0]
        with self.assertRaisesRegex(ValidationError, "station 'S01'.*strictly inside"):
            self.validate(boundary)

        notch = valid_capture_data_v2()
        notch["stations"][0]["standing_point_m"] = [1.0, 0.5]
        with self.assertRaisesRegex(ValidationError, "station 'S01'.*strictly inside"):
            self.validate(notch)

    def test_rejects_invalid_optics(self) -> None:
        data = valid_capture_data_v2()
        data["device_profile"]["horizontal_fov_deg"] = 9.0
        with self.assertRaisesRegex(ValidationError, "horizontal_fov_deg"):
            self.validate(data)

    def test_rejects_bad_scale_anchor_measurements(self) -> None:
        wrong_target = valid_capture_data_v2()
        wrong_target["scale_anchors"][0]["measurement_ids"] = ["window-east-width"]
        with self.assertRaisesRegex(ValidationError, "window-east-width.*window-west"):
            self.validate(wrong_target)

        audit_only = valid_capture_data_v2()
        audit_only["scale_anchors"][0] = {
            "id": "wall-00", "target_id": "wall-00",
            "measurement_ids": ["east-window-wall-length"],
        }
        audit_only["modes"][0]["required_scale_anchor_ids"] = ["wall-00"]
        with self.assertRaisesRegex(ValidationError, "east-window-wall-length.*exact_override"):
            self.validate(audit_only)

    def test_rejects_bath_door_on_return_wall(self) -> None:
        data = valid_capture_data_v2()
        data["wall_review"]["wall-02"]["opening_ids"] = []
        data["wall_review"]["wall-03"]["opening_ids"] = ["bath-door-south"]
        with self.assertRaisesRegex(ValidationError, "bath-door-south.*wall-03.*wall-02"):
            self.validate(data)

    def test_accepts_a_third_fixed_count_mode_without_known_id_branch(self) -> None:
        data = valid_capture_data_v2()
        third = copy.deepcopy(data["modes"][0])
        third["id"] = "production-fixture"
        third["passes"][0]["id"] = "P3"
        third["passes"][0]["groups"][0]["id"] = "G3"
        for shot in third["passes"][0]["groups"][0]["shots"]:
            shot["id"] = f"P3-{shot['id']}"
        data["modes"].append(third)
        plan = self.validate(data)
        self.assertEqual(plan.mode("production-fixture").expected_image_count, 2)

    def test_project_plan_v2_invariants(self) -> None:
        plan = CapturePlan.from_dict(json.loads(CAPTURE_PLAN.read_text(encoding="utf-8")))
        plan.validate(load_room(ROOM), load_measurements(MEASUREMENTS))

        self.assertEqual(tuple(mode.id for mode in plan.modes), ("lite-24", "standard-48"))
        self.assertEqual(tuple(len(mode.shots) for mode in plan.modes), (24, 48))
        self.assertEqual(tuple(len(mode.groups) for mode in plan.modes), (14, 28))
        door_state_rule = (
            "Keep both the entry and bathroom doors closed for the entire route. "
            "If either door state changes, finish and restart under a new capture ID."
        )
        for mode in plan.modes:
            self.assertIn(
                door_state_rule,
                f"{mode.description} {mode.risk_note}",
                mode.id,
            )
        self.assertEqual(
            tuple(
                (capture_pass.id, len(capture_pass.groups), len(capture_pass.shots))
                for mode in plan.modes for capture_pass in mode.passes
            ),
            (
                ("L-STRUCTURE", 8, 16), ("L-VERTICAL", 2, 4), ("L-ANCHORS", 4, 4),
                ("A", 8, 24), ("B", 4, 8), ("C", 8, 8), ("D", 8, 8),
            ),
        )
        self.assertEqual(
            tuple((station.id, station.number, tuple(station.standing_point_m.to_list())) for station in plan.stations),
            (
                ("S01", 1, (1.35, 1.65)), ("S02", 2, (2.15, 1.55)),
                ("S03", 3, (3.10, 1.45)), ("S04", 4, (3.65, 1.80)),
                ("S05", 5, (2.55, 2.10)), ("S06", 6, (2.20, 2.80)),
                ("S07", 7, (1.55, 2.75)), ("S08", 8, (1.10, 2.10)),
            ),
        )
        self.assertEqual(
            tuple((anchor.id, anchor.target_id, anchor.measurement_ids) for anchor in plan.scale_anchors),
            (
                ("window-west", "window-west", ("window-west-width",)),
                ("window-east", "window-east", ("window-east-width",)),
                ("entry-door", "entry-door", ("entry-door-width",)),
                ("bath-door-south", "bath-door-south", ("bath-door-width",)),
                ("bed-full", "bed-full", ("bed-length", "bed-width")),
                ("desk", "desk", ("desk-width",)),
                ("closet", "closet", ("closet-depth",)),
            ),
        )

        lite = plan.mode("lite-24")
        self.assertEqual(
            tuple((group.id, group.station_id) for group in lite.groups),
            (
                ("L01", "S01"), ("L02", "S02"), ("L03", "S03"), ("L04", "S04"),
                ("L05", "S05"), ("L06", "S06"), ("L07", "S07"), ("L08", "S08"),
                ("L09", "S03"), ("L10", "S07"), ("L11", "S06"), ("L12", "S06"),
                ("L13", "S04"), ("L14", "S02"),
            ),
        )
        self.assertEqual(
            tuple((shot.pitch, shot.pitch_deg) for shot in lite.shots),
            tuple([("level", -10.0)] * 16 + [("up", 25.0), ("down", -35.0)] * 2 + [("level", -10.0)] * 4),
        )

        standard = plan.mode("standard-48")
        self.assertEqual(
            tuple((group.id, group.station_id) for group in standard.groups),
            (
                ("STD-A01", "S01"), ("STD-A02", "S02"), ("STD-A03", "S03"), ("STD-A04", "S04"),
                ("STD-A05", "S05"), ("STD-A06", "S06"), ("STD-A07", "S07"), ("STD-A08", "S08"),
                ("STD-B01", "S01"), ("STD-B02", "S03"), ("STD-B03", "S05"), ("STD-B04", "S07"),
                ("STD-C01A", "S07"), ("STD-C01B", "S08"), ("STD-C02A", "S04"), ("STD-C02B", "S05"),
                ("STD-C03A", "S03"), ("STD-C03B", "S04"), ("STD-C04A", "S01"), ("STD-C04B", "S02"),
                ("STD-D01", "S07"), ("STD-D02", "S06"), ("STD-D03", "S05"), ("STD-D04", "S01"),
                ("STD-D05", "S02"), ("STD-D06", "S03"), ("STD-D07", "S04"), ("STD-D08", "S06"),
            ),
        )
        self.assertEqual(
            tuple((shot.pitch, shot.pitch_deg) for shot in standard.shots),
            tuple([("level", 0.0)] * 24 + [("up", 30.0), ("down", -35.0)] * 4 + [("level", 0.0)] * 16),
        )

        legacy_data = json.loads(LEGACY_CAPTURE_PLAN.read_text(encoding="utf-8"))
        legacy = tuple(
            legacy_tuple(shot) for capture_pass in legacy_data["passes"] for shot in capture_pass["shots"]
        )
        normalized = tuple(
            normalized_tuple(plan, group, shot)
            for capture_pass in standard.passes for group in capture_pass.groups for shot in group.shots
        )
        self.assertEqual(len(normalized), 48)
        self.assertEqual(normalized, legacy)


if __name__ == "__main__":
    unittest.main()
