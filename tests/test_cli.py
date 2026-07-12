import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def test_module_exit_code_for_search_miss(self):
        result = subprocess.run(
            [sys.executable, "-m", "jsonforge", "search", "tests/fixtures/sample.json", "missing-value"],
            check=False,
        )

        self.assertEqual(result.returncode, 1)

    def test_shorthand_interactive_handles_strict_json_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "invalid.json"
            path.write_text('{"value": Infinity}', encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "jsonforge", str(path)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("JSON does not support Infinity", result.stderr)


if __name__ == "__main__":
    unittest.main()
