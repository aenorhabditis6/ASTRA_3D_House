import unittest

from astra_house.geometry import build_opening_boxes, build_wall_boxes
from astra_house.model import Opening, RoomModel, SourceRef, Vec2, Wall


class WallGeometryTest(unittest.TestCase):
    def test_door_splits_wall_into_jambs_and_header(self) -> None:
        source = SourceRef("test", "fixture", 1.0)
        room = RoomModel(
            schema_version="1.0",
            room_id="door",
            units="meters",
            up_axis="Z",
            ceiling_height_m=3.0,
            ceiling_height_source=source,
            scale_source=source,
            floor_polygon=(Vec2(0, 0), Vec2(4, 0), Vec2(4, 3), Vec2(0, 3)),
            walls=(Wall("wall", Vec2(0, 0), Vec2(4, 0), 0.12, source, source),),
            openings=(
                Opening("door", "wall", 1.0, 0.9, 0.0, 2.1, source, source),
            ),
            proxies=(),
            provenance=(source,),
        )
        boxes = build_wall_boxes(room)
        self.assertEqual(
            [box.id for box in boxes],
            ["wall:span-00", "wall:span-01", "wall:door:header"],
        )
        self.assertAlmostEqual(
            sum(box.size.x * box.size.z for box in boxes), 10.11, places=6
        )

    def test_window_creates_sill_header_and_two_sides(self) -> None:
        source = SourceRef("test", "fixture", 1.0)
        room = RoomModel(
            schema_version="1.0",
            room_id="window",
            units="meters",
            up_axis="Z",
            ceiling_height_m=3.0,
            ceiling_height_source=source,
            scale_source=source,
            floor_polygon=(Vec2(0, 0), Vec2(4, 0), Vec2(4, 3), Vec2(0, 3)),
            walls=(Wall("wall", Vec2(0, 0), Vec2(4, 0), 0.12, source, source),),
            openings=(
                Opening("window", "wall", 1.0, 1.5, 0.8, 1.2, source, source),
            ),
            proxies=(),
            provenance=(source,),
        )
        self.assertEqual(len(build_wall_boxes(room)), 4)
        opening_box = build_opening_boxes(room)[0]
        self.assertEqual(opening_box.id, "window")
        self.assertEqual(opening_box.collection, "OPENINGS")

