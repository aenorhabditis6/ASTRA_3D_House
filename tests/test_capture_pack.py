from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from astra_house.capture import CapturePlan
from astra_house.capture_pack import write_capture_pack
from astra_house.errors import ValidationError
from astra_house.io import load_room
from astra_house.measurements import MeasurementSet
from astra_house.plan import PlanAnnotation


PROJECT = Path("projects/dorm-right-bedroom")
CAPTURE_PLAN = PROJECT / "capture-plan.json"
ANNOTATION = PROJECT / "plan-annotation.json"
ROOM = PROJECT / "room.json"
MEASUREMENTS = PROJECT / "measurements.json"


class CapturePackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.capture_data = json.loads(CAPTURE_PLAN.read_text(encoding="utf-8"))
        cls.plan = CapturePlan.from_dict(cls.capture_data)
        cls.annotation = PlanAnnotation.from_dict(
            json.loads(ANNOTATION.read_text(encoding="utf-8"))
        )
        cls.room = load_room(ROOM)
        cls.measurements = MeasurementSet.from_dict(
            json.loads(MEASUREMENTS.read_text(encoding="utf-8"))
        )
        cls.source_png = Path(cls.annotation.image.path)

    def test_writes_three_deterministic_self_contained_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            index = write_capture_pack(
                self.plan,
                self.annotation,
                self.room,
                self.measurements,
                self.source_png,
                output,
            )
            self.assertEqual(index.name, "index.html")
            self.assertEqual(
                sorted(path.name for path in output.iterdir()),
                ["capture-intake.json", "capture-pack-report.json", "index.html"],
            )

            html = index.read_text(encoding="utf-8")
            self.assertIn("data:image/png;base64,", html)
            self.assertIn("Xiaomi 17 Ultra", html)
            self.assertIn("1× Leica 23 mm", html)
            self.assertIn("ARCore: optional / unverified", html)
            self.assertIn("wall-02", html)
            self.assertIn("bath-door-south", html)
            self.assertIn("wall-03", html)
            for shot in self.plan.shots:
                self.assertIn(shot.id, html)

            intake = json.loads(
                (output / "capture-intake.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(intake["shots"]), 48)
            self.assertTrue(
                all(item["source_filename"] is None for item in intake["shots"])
            )
            report = json.loads(
                (output / "capture-pack-report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["status"], "valid")
            self.assertEqual(report["shot_count"], 48)
            self.assertIn(report["source_hashes"]["capture_plan_sha256"], html)

            first = {path.name: path.read_bytes() for path in output.iterdir()}
            write_capture_pack(
                self.plan,
                self.annotation,
                self.room,
                self.measurements,
                self.source_png,
                output,
            )
            second = {path.name: path.read_bytes() for path in output.iterdir()}
            self.assertEqual(first, second)

    def test_invalid_plan_does_not_replace_existing_outputs(self) -> None:
        invalid_data = json.loads(json.dumps(self.capture_data))
        invalid_data["wall_review"]["wall-00"]["opening_ids"].remove(
            "window-west"
        )
        invalid_data["wall_review"]["wall-01"]["opening_ids"].append(
            "window-west"
        )
        invalid_plan = CapturePlan.from_dict(invalid_data)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            sentinels = {
                "index.html": b"old html",
                "capture-intake.json": b"old intake",
                "capture-pack-report.json": b"old report",
            }
            for name, value in sentinels.items():
                (output / name).write_bytes(value)

            with self.assertRaisesRegex(
                ValidationError,
                "window-west.*wall-01.*wall-00",
            ):
                write_capture_pack(
                    invalid_plan,
                    self.annotation,
                    self.room,
                    self.measurements,
                    self.source_png,
                    output,
                )

            self.assertEqual(
                {name: (output / name).read_bytes() for name in sentinels},
                sentinels,
            )


if __name__ == "__main__":
    unittest.main()
