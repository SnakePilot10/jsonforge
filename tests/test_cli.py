import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jsonforge.cli import file_size, main, print_save_result, save_exit_code
from jsonforge.core.document import ConcurrentModificationError, SaveResult


class CliTests(unittest.TestCase):
    def test_file_size_accepts_units_and_unlimited(self):
        self.assertEqual(file_size("2K"), 2 * 1024)
        self.assertEqual(file_size("3MiB"), 3 * 1024 * 1024)
        self.assertIsNone(file_size("unlimited"))

    def test_file_size_rejects_negative_or_unknown_values(self):
        with self.assertRaisesRegex(ValueError, "file size"):
            file_size("-1")
        with self.assertRaisesRegex(ValueError, "file size"):
            file_size("10TB")

    def test_interactive_keyboard_interrupt_returns_130(self):
        with mock.patch("jsonforge.cli.run_interactive", side_effect=KeyboardInterrupt):
            self.assertEqual(main(["sample.json"]), 130)

    def test_interactive_eof_returns_success(self):
        with mock.patch("jsonforge.cli.run_interactive", side_effect=EOFError):
            self.assertEqual(main(["sample.json"]), 0)

    def test_shorthand_interactive_handles_concurrent_modification(self):
        with mock.patch(
            "jsonforge.cli.run_interactive",
            side_effect=ConcurrentModificationError("File changed while loading"),
        ):
            self.assertEqual(main(["sample.json"]), 2)

    def test_unconfirmed_post_save_snapshot_warns_and_returns_partial_success(self):
        result = SaveResult(
            backup_path=None,
            replaced=True,
            durability_confirmed=True,
            snapshot_confirmed=False,
        )

        with mock.patch("builtins.print") as print_mock:
            print_save_result(result)

        print_mock.assert_called_once_with(
            "warning: the file was replaced successfully, "
            "but its post-save snapshot could not be confirmed",
            file=sys.stderr,
        )
        self.assertEqual(save_exit_code(result), 3)

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

    def test_validate_rejects_file_above_cli_size_limit(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "jsonforge",
                "validate",
                "tests/fixtures/sample.json",
                "--max-file-size",
                "5",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("exceeds the 5-byte limit", result.stderr)

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

    def test_search_supports_path_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text('{"settings": {"enabled": true}}', encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "jsonforge",
                    "search",
                    str(path),
                    "true",
                    "--path-format",
                    "pointer",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn("/settings/enabled: true", result.stdout)

    def test_tree_supports_path_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text('{"settings": {"enabled": true}}', encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "jsonforge",
                    "tree",
                    str(path),
                    "--path-format",
                    "pointer",
                    "--depth",
                    "2",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            lines = result.stdout.strip().split("\n")
            self.assertIn("/settings\tdict", lines)
            self.assertIn("/settings/enabled\tbool", lines)

    def test_tree_fails_on_empty_root_key_with_dot_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty_root.json"
            path.write_text('{"": 123}', encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "jsonforge",
                    "tree",
                    str(path),
                    "--path-format",
                    "dot",
                    "--depth",
                    "2",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn(
                "Path cannot be represented as a dot path; use --path-format pointer",
                result.stderr,
            )

    def test_search_fails_on_empty_root_key_with_dot_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty_root.json"
            path.write_text('{"": 123}', encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "jsonforge",
                    "search",
                    str(path),
                    "123",
                    "--path-format",
                    "dot",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn(
                "Path cannot be represented as a dot path; use --path-format pointer",
                result.stderr,
            )


if __name__ == "__main__":
    unittest.main()
