import json
import unittest
from pathlib import Path

from astra_house.errors import ValidationError
from astra_house.measurements import MeasurementSet


class MeasurementSetTest(unittest.TestCase):
    def test_loads_confirmed_room_measurements(self) -> None:
        data = json.loads(
            Path("projects/dorm-right-bedroom/measurements.json").read_text()
        )
        measurements = MeasurementSet.from_dict(data)

        self.assertEqual(measurements.room_id, "dorm-right-bedroom")
        self.assertAlmostEqual(
            measurements.value_for("bed-full", "size_x"), 2.13
        )
        self.assertAlmostEqual(
            measurements.value_for("window-east", "height"), 1.78
        )
        self.assertEqual(
            measurements.record_for("wall-02", "length").application,
            "audit_only",
        )
        self.assertAlmostEqual(
            measurements.value_for("window-west", "offset"), 0.79
        )
        self.assertAlmostEqual(
            measurements.value_for("window-east", "offset"), 2.55
        )
        self.assertAlmostEqual(
            measurements.value_for("bath-door-south", "width"), 0.91
        )
        self.assertAlmostEqual(
            measurements.value_for("bath-door-south", "height"), 2.37
        )
        self.assertEqual(len(measurements.measurements), 20)

    def test_rejects_duplicate_target_dimensions(self) -> None:
        source = {
            "kind": "confirmed_measurement",
            "reference": "test",
            "confidence": 1.0,
        }
        record = {
            "id": "one",
            "target_kind": "proxy",
            "target_id": "bed",
            "dimension": "size_x",
            "value_m": 2.0,
            "application": "exact_override",
            "source": source,
        }
        data = {
            "schema_version": "1.0",
            "room_id": "room",
            "measurements": [record, {**record, "id": "two"}],
        }
        with self.assertRaisesRegex(ValidationError, "duplicate measurement"):
            MeasurementSet.from_dict(data)
