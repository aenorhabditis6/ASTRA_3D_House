import contextlib
import io
import unittest

from astra_house.cli import main


class CliSmokeTest(unittest.TestCase):
    def test_no_command_prints_help_and_returns_two(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = main([])

        self.assertEqual(result, 2)
        self.assertIn("build-logical", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
