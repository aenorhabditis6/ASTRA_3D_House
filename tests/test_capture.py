from __future__ import annotations

import json
import unittest
from pathlib import Path

from astra_house.capture import CapturePlan
from astra_house.errors import ValidationError
from astra_house.io import load_room


ROOM = Path("projects/dorm-right-bedroom/room.json")
CAPTURE_PLAN = Path("projects/dorm-right-bedroom/capture-plan.json")


def valid_capture_data() -> dict[str, object]:
    counts = {"A": 24, "B": 8, "C": 8, "D": 8}
    passes = []
    for pass_id, count in counts.items():
        passes.append(
            {
                "id": pass_id,
                "title": f"Pass {pass_id}",
                "purpose": "validation fixture",
                "shots": [
                    {
                        "id": f"{pass_id}{index:02d}",
                        "standing_point_m": [2.0, 2.0],
                        "pitch": "level",
                        "target_ids": ["wall-00"],
                        "instruction": (
                            "Keep wall-00 and both neighboring edges visible."
                        ),
                    }
                    for index in range(1, count + 1)
                ],
            }
        )
    return {
        "schema_version": "1.0",
        "room_id": "dorm-right-bedroom",
        "capture_id": "dorm-right-bedroom-diagnostic-01",
        "expected_image_count": 48,
        "device_profile": {
            "make": "Xiaomi",
            "model": "Xiaomi 17 Ultra",
            "lens": "1x Leica 23 mm main",
            "orientation": "landscape",
            "aspect_ratio": "4:3",
            "file_format": "JPG",
            "arcore_status": "unverified_optional",
        },
        "wall_review": {
            "wall-00": {
                "role": "east double-window wall",
                "opening_ids": ["window-west", "window-east"],
            },
            "wall-01": {"role": "south long wall", "opening_ids": []},
            "wall-02": {
                "role": "west-facing bathroom-door wall",
                "opening_ids": ["bath-door-south"],
            },
            "wall-03": {"role": "connecting return", "opening_ids": []},
            "wall-04": {
                "role": "west-facing entry wall",
                "opening_ids": ["entry-door"],
            },
            "wall-05": {"role": "north measured wall", "opening_ids": []},
        },
        "passes": passes,
    }


class CapturePlanTest(unittest.TestCase):
    def test_project_capture_plan_has_expected_passes_and_device(self) -> None:
        plan = CapturePlan.from_dict(json.loads(CAPTURE_PLAN.read_text()))
        plan.validate(load_room(ROOM))
        self.assertEqual([item.id for item in plan.passes], ["A", "B", "C", "D"])
        self.assertEqual([len(item.shots) for item in plan.passes], [24, 8, 8, 8])
        self.assertEqual(plan.device_profile.model, "Xiaomi 17 Ultra")
        self.assertEqual(plan.device_profile.lens, "1x Leica 23 mm main")
        self.assertEqual(plan.device_profile.arcore_status, "unverified_optional")
        review = {item.wall_id: item for item in plan.wall_review}
        self.assertEqual(review["wall-02"].opening_ids, ("bath-door-south",))
        self.assertEqual(review["wall-03"].opening_ids, ())

    def test_accepts_48_unique_shots_and_reviewed_openings(self) -> None:
        plan = CapturePlan.from_dict(valid_capture_data())
        plan.validate(load_room(ROOM))
        self.assertEqual(plan.expected_image_count, 48)
        self.assertEqual(len(plan.shots), 48)

    def test_rejects_bath_door_on_return_wall(self) -> None:
        data = valid_capture_data()
        data["wall_review"]["wall-02"]["opening_ids"] = []
        data["wall_review"]["wall-03"]["opening_ids"] = ["bath-door-south"]
        plan = CapturePlan.from_dict(data)
        with self.assertRaisesRegex(
            ValidationError,
            "bath-door-south.*wall-03.*wall-02",
        ):
            plan.validate(load_room(ROOM))

    def test_rejects_point_in_l_shape_notch(self) -> None:
        data = valid_capture_data()
        data["passes"][0]["shots"][0]["standing_point_m"] = [1.0, 0.5]
        with self.assertRaisesRegex(ValidationError, "outside floor polygon"):
            CapturePlan.from_dict(data).validate(load_room(ROOM))

    def test_rejects_duplicate_ids_and_wrong_total(self) -> None:
        duplicate = valid_capture_data()
        duplicate["passes"][0]["shots"][1]["id"] = "A01"
        with self.assertRaisesRegex(ValidationError, "duplicate shot id"):
            CapturePlan.from_dict(duplicate).validate(load_room(ROOM))

        short = valid_capture_data()
        short["passes"][0]["shots"].pop()
        with self.assertRaisesRegex(ValidationError, "expected 48.*found 47"):
            CapturePlan.from_dict(short).validate(load_room(ROOM))


if __name__ == "__main__":
    unittest.main()
