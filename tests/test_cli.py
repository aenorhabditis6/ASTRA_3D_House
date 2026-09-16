import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from astra_house.cli import build_logical_project, main


class CliSmokeTest(unittest.TestCase):
    def test_no_command_prints_help_and_returns_two(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = main([])

        self.assertEqual(result, 2)
        self.assertIn("build-logical", stderr.getvalue())

    def test_build_logical_writes_non_blender_artifacts_and_invokes_blender(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "build"
            calls: list[list[str]] = []

            def fake_runner(command: list[str]) -> None:
                calls.append(command)
                (output / "house_master.blend").touch()
                (output / "house.glb").touch()

            result = build_logical_project(
                project_dir=Path("projects/dorm-right-bedroom"),
                output_dir=output,
                blender=Path("/Applications/Blender.app/Contents/MacOS/Blender"),
                runner=fake_runner,
            )
            self.assertEqual(result, output / "house_master.blend")
            self.assertTrue((output / "plan-review.svg").exists())
            self.assertTrue((output / "quality-report.json").exists())
            self.assertEqual(
                calls[0][0], "/Applications/Blender.app/Contents/MacOS/Blender"
            )
            self.assertTrue(
                any(
                    str(item).endswith("blender/build_scene.py")
                    for item in calls[0]
                )
            )

    def test_missing_blender_returns_external_failure_code(self) -> None:
        with mock.patch(
            "astra_house.cli.build_logical_project",
            side_effect=OSError("executable not found"),
        ):
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "build-logical",
                        "--project",
                        "projects/dorm-right-bedroom",
                        "--blender",
                        "/missing/blender",
                    ]
                )
        self.assertEqual(result, 3)
        self.assertIn("could not start Blender", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
