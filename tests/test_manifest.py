import json
import tempfile
import unittest
from pathlib import Path

from astra_house.errors import ValidationError
from astra_house.manifest import sha256_file, verify_manifest


class ManifestTest(unittest.TestCase):
    def test_floorplan_hash_matches_recorded_source(self) -> None:
        manifest = json.loads(
            Path("projects/dorm-right-bedroom/manifest.json").read_text()
        )
        asset = manifest["assets"][0]
        self.assertEqual(
            asset["sha256"],
            "8aae212209211a2e0f668801de6148cee8dae6c155b487a66c8797fdbcc77011",
        )
        self.assertEqual(sha256_file(Path(asset["path"])), asset["sha256"])

    def test_changed_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "plan.png"
            path.write_bytes(b"changed")
            manifest = {
                "schema_version": "1.0",
                "assets": [
                    {"path": "plan.png", "bytes": 7, "sha256": "0" * 64}
                ],
            }
            with self.assertRaisesRegex(ValidationError, "plan.png.*SHA-256"):
                verify_manifest(root, manifest)
