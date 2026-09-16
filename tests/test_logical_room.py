import json
import unittest
from pathlib import Path

from astra_house.logical_room import build_logical_room
from astra_house.plan import PlanAnnotation


class LogicalRoomTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        raw = json.loads(
            Path("projects/dorm-right-bedroom/plan-annotation.json").read_text()
        )
        cls.room = build_logical_room(PlanAnnotation.from_dict(raw))

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
            {"window-north", "bath-door-south", "entry-door"},
        )
        bed = next(item for item in self.room.proxies if item.id == "bed-full")
        self.assertAlmostEqual(bed.size.x, 1.905)
        self.assertAlmostEqual(bed.size.y, 1.3716)

    def test_provisional_values_are_not_marked_confirmed(self) -> None:
        confidence = {
            opening.id: opening.vertical_source.confidence
            for opening in self.room.openings
        }
        self.assertLess(confidence["window-north"], 0.5)
        self.assertLess(confidence["entry-door"], 0.5)

