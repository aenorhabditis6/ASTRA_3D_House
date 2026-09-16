import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from astra_house.errors import ValidationError
from astra_house.io import load_room, save_room
from astra_house.model import Opening, RoomModel, SourceRef, Vec2, Wall


class RoomModelTest(unittest.TestCase):
    def make_room(self) -> RoomModel:
        source = SourceRef("confirmed_measurement", "user", 1.0)
        return RoomModel(
            schema_version="1.0",
            room_id="test-room",
            units="meters",
            up_axis="Z",
            ceiling_height_m=3.0,
            ceiling_height_source=source,
            scale_source=source,
            floor_polygon=(Vec2(0, 0), Vec2(4, 0), Vec2(4, 3), Vec2(0, 3)),
            walls=(
                Wall(
                    "north",
                    Vec2(0, 3),
                    Vec2(4, 3),
                    0.12,
                    source,
                    source,
                ),
            ),
            openings=(
                Opening(
                    "door",
                    "north",
                    1.0,
                    0.9,
                    0.0,
                    2.03,
                    source,
                    source,
                ),
            ),
            proxies=(),
            provenance=(source,),
        )

    def test_round_trip_preserves_room(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "room.json"
            room = self.make_room()

            save_room(room, path)

            self.assertEqual(load_room(path), room)

    def test_opening_must_fit_parent_wall(self) -> None:
        room = self.make_room()
        source = room.provenance[0]
        bad = replace(
            room,
            openings=(
                Opening(
                    "door",
                    "north",
                    3.5,
                    0.9,
                    0.0,
                    2.03,
                    source,
                    source,
                ),
            ),
        )

        with self.assertRaisesRegex(ValidationError, "door.*north"):
            bad.validate()


if __name__ == "__main__":
    unittest.main()
