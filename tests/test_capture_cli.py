from __future__ import annotations

import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from astra_house.cli import main


PROJECT = Path("projects/dorm-right-bedroom")
SOURCE = Path("assets/reference/floorplans/dorm-suite-floorplan.png")


class CaptureCliTest(unittest.TestCase):
    def test_build_capture_pack_does_not_require_blender(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = main(
                    [
                        "build-capture-pack",
                        "--project",
                        str(PROJECT),
                        "--output",
                        str(output),
                    ]
                )

            self.assertEqual(result, 0)
            self.assertTrue((output / "index.html").is_file())
            self.assertIn(str(output / "index.html"), stdout.getvalue())

    def test_changed_source_hash_fails_before_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "projects" / "dorm-right-bedroom"
            source = root / SOURCE
            output = root / "build" / "capture-pack"
            shutil.copytree(PROJECT, project)
            source.parent.mkdir(parents=True)
            shutil.copy2(SOURCE, source)
            changed = bytearray(source.read_bytes())
            changed[-1] ^= 1
            source.write_bytes(changed)
            output.mkdir(parents=True)
            sentinel = output / "index.html"
            sentinel.write_text("old guide", encoding="utf-8")

            stderr = io.StringIO()
            with (
                mock.patch("astra_house.cli.REPOSITORY_ROOT", root),
                contextlib.redirect_stderr(stderr),
            ):
                result = main(
                    [
                        "build-capture-pack",
                        "--project",
                        str(project),
                        "--output",
                        str(output),
                    ]
                )

            self.assertEqual(result, 2)
            self.assertIn("SHA-256 mismatch", stderr.getvalue())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "old guide")
            self.assertFalse((output / "capture-intake.json").exists())
            self.assertFalse((output / "capture-pack-report.json").exists())


if __name__ == "__main__":
    unittest.main()
