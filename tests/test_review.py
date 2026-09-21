import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from astra_house.io import load_room
from astra_house.measurements import MeasurementSet
from astra_house.plan import PlanAnnotation
from astra_house.review import write_plan_overlay, write_quality_report


class ReviewArtifactTest(unittest.TestCase):
    def test_overlay_and_report_expose_provisional_values(self) -> None:
        annotation = PlanAnnotation.from_dict(
            json.loads(
                Path("projects/dorm-right-bedroom/plan-annotation.json").read_text()
            )
        )
        measurements = MeasurementSet.from_dict(
            json.loads(
                Path("projects/dorm-right-bedroom/measurements.json").read_text()
            )
        )
        room = load_room(Path("projects/dorm-right-bedroom/room.json"))
        with tempfile.TemporaryDirectory() as directory:
            overlay = Path(directory) / "plan-review.svg"
            report = Path(directory) / "quality-report.json"
            write_plan_overlay(annotation, room, overlay, measurements)
            write_quality_report(annotation, room, report, measurements)
            root = ET.parse(overlay).getroot()
            self.assertEqual(root.attrib["viewBox"], "0 0 1000 680")
            result = json.loads(report.read_text())
            self.assertEqual(result["room_id"], "dorm-right-bedroom")
            self.assertNotIn("provisional_scale", result["warnings"])
            self.assertIn("assumed_door_heights", result["warnings"])
            self.assertIn(
                "measurement_residuals_require_review", result["warnings"]
            )
            audit = {item["id"]: item for item in result["measurement_audit"]}
            self.assertAlmostEqual(audit["bed-length"]["residual_percent"], 0.0)
            self.assertEqual(audit["bath-wall-length"]["status"], "needs_review")
            self.assertGreater(
                abs(audit["bath-wall-length"]["residual_percent"]), 50.0
            )
