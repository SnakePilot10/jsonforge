import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def test_module_exit_code_for_search_miss(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "jsonforge",
                "search",
                "tests/fixtures/sample.json",
                "missing-value",
            ],
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

    def test_search_limit_zero_returns_search_miss(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "jsonforge",
                "search",
                "tests/fixtures/sample.json",
                "settings",
                "--limit",
                "0",
            ],
            check=False,
        )

        self.assertEqual(result.returncode, 1)

    def test_search_rejects_too_small_preview(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "jsonforge",
                "search",
                "tests/fixtures/sample.json",
                "settings",
                "--preview",
                "2",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("greater than or equal to 3", result.stderr)

    def test_tree_rejects_negative_depth(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "jsonforge",
                "tree",
                "tests/fixtures/sample.json",
                "--depth",
                "-1",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("greater than or equal to 0", result.stderr)

    def test_get_supports_json_pointer_path_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text('{"users": [{"name": "Ada"}], "a/b": 1}', encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "jsonforge",
                    "get",
                    str(path),
                    "/a~1b",
                    "--path-format",
                    "pointer",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "1")

    def test_set_supports_json_pointer_path_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text('{"users": [{"name": "Grace"}]}', encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "jsonforge",
                    "set",
                    str(path),
                    "/users/0/name",
                    "Ada",
                    "--path-format",
                    "pointer",
                    "--type",
                    "string",
                    "--no-backup",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn('"name": "Ada"', path.read_text(encoding="utf-8"))

    def test_add_supports_json_pointer_path_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text('{"users": [{"name": "Ada"}]}', encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "jsonforge",
                    "add",
                    str(path),
                    "/users/-",
                    '{"name":"New"}',
                    "--path-format",
                    "pointer",
                    "--type",
                    "json",
                    "--no-backup",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn('"name": "New"', path.read_text(encoding="utf-8"))

    def test_delete_supports_json_pointer_path_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text('{"obsolete": true, "keep": true}', encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "jsonforge",
                    "delete",
                    str(path),
                    "/obsolete",
                    "--path-format",
                    "pointer",
                    "--no-backup",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            contents = path.read_text(encoding="utf-8")
            self.assertNotIn("obsolete", contents)
            self.assertIn('"keep": true', contents)


if __name__ == "__main__":
    unittest.main()
