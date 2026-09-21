import json
import unittest
from pathlib import Path

from astra_house.model import Vec2
from astra_house.plan import PlanAnnotation, PlanCalibration


class PlanCalibrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        data = json.loads(
            Path("projects/dorm-right-bedroom/plan-annotation.json").read_text()
        )
        cls.annotation = PlanAnnotation.from_dict(data)
        cls.calibration = PlanCalibration.from_annotation(cls.annotation)

    def test_isotropic_scale_uses_both_bed_axes(self) -> None:
        self.assertAlmostEqual(
            self.calibration.meters_per_pixel, 0.01394929875, places=9
        )

    def test_coordinate_round_trip(self) -> None:
        pixel = Vec2(849, 82)
        restored = self.calibration.room_to_pixel(
            self.calibration.pixel_to_room(pixel)
        )
        self.assertAlmostEqual(restored.x, pixel.x, places=9)
        self.assertAlmostEqual(restored.y, pixel.y, places=9)

    def test_y_axis_points_up_in_room_space(self) -> None:
        top = self.calibration.pixel_to_room(Vec2(495, 82))
        bottom = self.calibration.pixel_to_room(Vec2(495, 294))
        self.assertGreater(top.y, bottom.y)
