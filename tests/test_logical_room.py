import json
import unittest
from pathlib import Path

from astra_house.logical_room import build_logical_room
from astra_house.measurements import MeasurementSet
from astra_house.plan import PlanAnnotation


class LogicalRoomTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        raw = json.loads(
            Path("projects/dorm-right-bedroom/plan-annotation.json").read_text()
        )
        measurements = MeasurementSet.from_dict(
            json.loads(
                Path("projects/dorm-right-bedroom/measurements.json").read_text()
            )
        )
        cls.room = build_logical_room(PlanAnnotation.from_dict(raw), measurements)

    def test_confirmed_height_and_l_shaped_floor(self) -> None:
        self.assertAlmostEqual(self.room.ceiling_height_m, 3.3528)
        self.assertEqual(len(self.room.floor_polygon), 6)

    def test_semantic_inventory(self) -> None:
        self.assertEqual(
            {item.id for item in self.room.proxies},
            {"bed-full", "desk", "chair", "chest", "pedestal", "closet"},
        )
        self.assertEqual(
            {opening.id for opening in self.room.openings},
            {"window-west", "window-east", "bath-door-south", "entry-door"},
        )
        bed = next(item for item in self.room.proxies if item.id == "bed-full")
        self.assertAlmostEqual(bed.size.x, 2.13)
        self.assertAlmostEqual(bed.size.y, 1.45)

    def test_exact_measurements_override_proxy_and_opening_dimensions(self) -> None:
        proxies = {proxy.id: proxy for proxy in self.room.proxies}
        openings = {opening.id: opening for opening in self.room.openings}
        self.assertAlmostEqual(proxies["desk"].size.y, 1.22)
        self.assertAlmostEqual(proxies["closet"].size.x, 0.73)
        for window_id in ("window-west", "window-east"):
            self.assertAlmostEqual(openings[window_id].width_m, 1.27)
            self.assertAlmostEqual(openings[window_id].height_m, 1.78)
            self.assertAlmostEqual(openings[window_id].sill_m, 0.77)
            self.assertEqual(
                openings[window_id].vertical_source.kind,
                "confirmed_measurement",
            )
        self.assertAlmostEqual(openings["entry-door"].width_m, 1.0)
        self.assertAlmostEqual(openings["entry-door"].height_m, 2.37)
        self.assertAlmostEqual(openings["window-west"].offset_m, 0.79)
        self.assertAlmostEqual(openings["window-east"].offset_m, 2.55)
        self.assertEqual(openings["bath-door-south"].wall_id, "wall-02")
        self.assertAlmostEqual(
            openings["bath-door-south"].offset_m,
            1.2693861862566749,
        )
        self.assertAlmostEqual(openings["bath-door-south"].width_m, 0.91)
        self.assertAlmostEqual(openings["bath-door-south"].height_m, 2.37)
        parent_wall = next(
            wall
            for wall in self.room.walls
            if wall.id == openings["bath-door-south"].wall_id
        )
        remaining_jamb = (
            parent_wall.length_m
            - openings["bath-door-south"].offset_m
            - openings["bath-door-south"].width_m
        )
        self.assertGreater(remaining_jamb, 0.30)

    def test_scale_and_measured_door_heights_are_confirmed(self) -> None:
        openings = {opening.id: opening for opening in self.room.openings}
        self.assertEqual(self.room.scale_source.kind, "confirmed_measurement")
        self.assertEqual(self.room.scale_source.confidence, 1.0)
        self.assertEqual(
            openings["entry-door"].vertical_source.kind,
            "confirmed_measurement",
        )
        self.assertEqual(
            openings["bath-door-south"].vertical_source.kind,
            "confirmed_measurement",
        )
