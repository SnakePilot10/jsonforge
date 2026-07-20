import json
import math
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jsonforge.core.document import ConcurrentModificationError, FileSnapshot, JsonDocument


class DocumentTests(unittest.TestCase):
    def test_backup_names_do_not_collide(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"a": 1}), encoding="utf-8")
            doc = JsonDocument.load(path)

            first = doc.backup()
            second = doc.backup()

            self.assertNotEqual(first, second)
            self.assertTrue(first.exists())
            self.assertTrue(second.exists())

    def test_save_writes_valid_json_atomically(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"a": 1}), encoding="utf-8")
            doc = JsonDocument.load(path)
            doc.data["a"] = 2

            backup_path = doc.save()

            self.assertTrue(backup_path.backup_path.exists())
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"a": 2})
            backup_content = backup_path.backup_path.read_text(encoding="utf-8")
            self.assertEqual(json.loads(backup_content), {"a": 1})

    def test_save_result_reports_replacement_and_durability(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"a": 1}), encoding="utf-8")
            doc = JsonDocument.load(path)
            doc.data["a"] = 2

            result = doc.save()

            self.assertTrue(result.replaced)
            self.assertIsNotNone(result.backup_path)
            self.assertIsInstance(result.durability_confirmed, bool)

    def test_load_rejects_non_standard_json_constants(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text('{"value": Infinity}', encoding="utf-8")

            with self.assertRaises(ValueError):
                JsonDocument.load(path)

    def test_load_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text('{"enabled": true, "enabled": false}', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, 'Duplicate key "enabled"'):
                JsonDocument.load(path)

    def test_load_can_allow_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text('{"enabled": true, "enabled": false}', encoding="utf-8")

            doc = JsonDocument.load(path, allow_duplicate_keys=True)

            self.assertEqual(doc.data, {"enabled": False})

    def test_save_rejects_infinity_and_keeps_original(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            doc = JsonDocument.load(path)
            doc.data["value"] = math.inf

            with self.assertRaises(ValueError):
                doc.save()

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"value": 1})

    def test_save_preserves_file_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            path.chmod(0o640)
            doc = JsonDocument.load(path)
            doc.data["value"] = 2

            doc.save()

            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)

    def test_save_does_not_preserve_old_mtime(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            old_time = 946684800
            os.utime(path, (old_time, old_time))
            doc = JsonDocument.load(path)
            doc.data["value"] = 2

            doc.save()

            self.assertGreater(path.stat().st_mtime, old_time)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink not available")
    def test_save_rejects_symlink_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "target.json"
            link = Path(tmpdir) / "link.json"
            target.write_text(json.dumps({"value": 1}), encoding="utf-8")
            os.symlink(target, link)
            doc = JsonDocument.load(link)
            doc.data["value"] = 2

            with self.assertRaises(ValueError):
                doc.save()

            self.assertTrue(link.is_symlink())
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"value": 1})

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink not available")
    def test_backup_uses_exclusive_creation_and_skips_broken_symlink(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            blocked = Path(tmpdir) / "sample.json.bak_20260717_120000"
            target = Path(tmpdir) / "target.json"
            os.symlink(target, blocked)
            doc = JsonDocument.load(path)

            with mock.patch(
                "jsonforge.core.document.time.strftime",
                return_value="20260717_120000",
            ):
                backup_path = doc.backup(doc.snapshot)

            self.assertEqual(backup_path.name, "sample.json.bak_20260717_120000_1")
            self.assertFalse(target.exists())
            self.assertTrue(blocked.is_symlink())
            self.assertEqual(json.loads(backup_path.read_text(encoding="utf-8")), {"value": 1})

    def test_backup_preserves_file_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            path.chmod(0o640)
            doc = JsonDocument.load(path)

            backup_path = doc.backup(doc.snapshot)

            self.assertEqual(stat.S_IMODE(backup_path.stat().st_mode), 0o640)

    def test_save_rejects_external_modification(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            doc = JsonDocument.load(path)
            doc.data["value"] = 3
            path.write_text(json.dumps({"value": 2}), encoding="utf-8")

            with self.assertRaises(ConcurrentModificationError):
                doc.save()

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"value": 2})

    def test_force_write_only_ignores_snapshot_conflict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            doc = JsonDocument.load(path)
            doc.data["value"] = 3
            path.write_text(json.dumps({"value": 2}), encoding="utf-8")

            result = doc.save(force_write=True)

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"value": 3})
            backup_content = result.backup_path.read_text(encoding="utf-8")
            self.assertEqual(json.loads(backup_content), {"value": 2})

    def test_save_updates_snapshot_after_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            doc = JsonDocument.load(path)
            old_snapshot = doc.snapshot
            doc.data["value"] = 2

            doc.save()

            self.assertNotEqual(doc.snapshot, old_snapshot)
            self.assertTrue(doc.snapshot.matches(path.stat()))

    def test_save_reports_unconfirmed_directory_durability(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            doc = JsonDocument.load(path)
            doc.data["value"] = 2

            with mock.patch("jsonforge.core.document.sync_parent_directory", return_value=False):
                result = doc.save()

            self.assertTrue(result.replaced)
            self.assertFalse(result.durability_confirmed)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"value": 2})

    def test_load_rejects_file_that_changes_while_reading(self):
        first = FileSnapshot(1, 2, 3, 4, 5, 0o100644)
        second = FileSnapshot(1, 2, 4, 5, 6, 0o100644)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")

            with mock.patch(
                "jsonforge.core.document.FileSnapshot.from_stat",
                side_effect=[first, second],
            ):
                with self.assertRaises(ConcurrentModificationError):
                    JsonDocument.load(path)


if __name__ == "__main__":
    unittest.main()
