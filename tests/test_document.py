import json
import math
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jsonforge.core.document import (
    ConcurrentModificationError,
    JsonDocument,
    ReadStabilitySignature,
    preserve_file_ownership,
)


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
            self.assertTrue(result.snapshot_confirmed)

    def test_load_rejects_non_standard_json_constants(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text('{"value": Infinity}', encoding="utf-8")

            with self.assertRaises(ValueError):
                JsonDocument.load(path)

    def test_load_reports_excessive_parser_nesting_as_value_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "deep.json"
            path.write_text("[]", encoding="utf-8")

            with mock.patch("jsonforge.core.document.loads", side_effect=RecursionError):
                with self.assertRaisesRegex(ValueError, "parser depth limit"):
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

    def test_load_rejects_file_above_configured_size_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text('{"value": 1}', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "exceeds the 5-byte limit"):
                JsonDocument.load(path, max_bytes=5)

    def test_load_accepts_file_exactly_at_configured_size_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            contents = '{"value": 1}'
            path.write_text(contents, encoding="utf-8")

            doc = JsonDocument.load(path, max_bytes=len(contents.encode("utf-8")))

            self.assertEqual(doc.data, {"value": 1})

    def test_save_rejects_output_above_loaded_size_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            original = '{"value":1}'
            path.write_text(original, encoding="utf-8")
            doc = JsonDocument.load(path, max_bytes=40)
            doc.data["value"] = "x" * 100

            with self.assertRaisesRegex(ValueError, "exceeds the 40-byte limit"):
                doc.save(backup=False)

            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_save_reports_excessive_serializer_nesting_as_value_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "deep.json"
            data = current = []
            for _ in range(2000):
                child = []
                current.append(child)
                current = child
            doc = JsonDocument(path, data)

            with self.assertRaisesRegex(ValueError, "serializer depth limit"):
                doc.save(backup=False)

            self.assertFalse(path.exists())

    def test_save_preserves_file_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            path.chmod(0o640)
            doc = JsonDocument.load(path)
            doc.data["value"] = 2

            doc.save()

            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)

    @unittest.skipUnless(hasattr(os, "fchown"), "file ownership not available")
    def test_save_preserves_file_owner_and_group(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            original = path.stat()
            doc = JsonDocument.load(path)
            doc.data["value"] = 2

            doc.save()

            saved = path.stat()
            self.assertEqual(saved.st_uid, original.st_uid)
            self.assertEqual(saved.st_gid, original.st_gid)

    @unittest.skipUnless(hasattr(os, "fchown"), "file ownership not available")
    def test_save_skips_fchown_when_ownership_already_matches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            doc = JsonDocument.load(path)
            doc.data["value"] = 2

            with mock.patch("jsonforge.core.document.os.fchown") as fchown_mock:
                doc.save(backup=False)

            fchown_mock.assert_not_called()
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"value": 2})

    @unittest.skipUnless(hasattr(os, "fchown"), "file ownership not available")
    def test_ownership_change_is_verified(self):
        snapshot = mock.Mock(st_uid=1000, st_gid=1000)
        before = mock.Mock(st_uid=2000, st_gid=2000)
        after = mock.Mock(st_uid=1000, st_gid=1000)

        with (
            mock.patch("jsonforge.core.document.os.fstat", side_effect=[before, after]),
            mock.patch("jsonforge.core.document.os.fchown") as fchown_mock,
        ):
            preserve_file_ownership(7, snapshot)

        fchown_mock.assert_called_once_with(7, 1000, 1000)

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

    def test_save_rechecks_symlink_immediately_before_replacement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            doc = JsonDocument.load(path)
            doc.data["value"] = 2

            with mock.patch(
                "jsonforge.core.document.ensure_not_symlink",
                side_effect=[None, ValueError("Refusing to replace symlink")],
            ):
                with self.assertRaisesRegex(ValueError, "Refusing to replace symlink"):
                    doc.save(backup=False)

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"value": 1})
            self.assertEqual(list(Path(tmpdir).glob(".*.tmp")), [])

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

    def test_save_rejects_file_deleted_since_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            doc = JsonDocument.load(path)
            doc.data["value"] = 2
            path.unlink()

            with self.assertRaisesRegex(ConcurrentModificationError, "deleted"):
                doc.save()

            self.assertFalse(path.exists())

    def test_save_rejects_existing_target_without_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            doc = JsonDocument(path, {"value": 2})

            with self.assertRaisesRegex(ConcurrentModificationError, "already exists"):
                doc.save()

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"value": 1})

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
            self.assertTrue(doc.snapshot.matches_stat(path.stat()))

    def test_save_reports_unconfirmed_snapshot_after_replacement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            doc = JsonDocument.load(path)
            doc.data["value"] = 2
            original_snapshot = doc.snapshot

            with mock.patch.object(
                doc,
                "_snapshot_path",
                side_effect=[original_snapshot, original_snapshot, FileNotFoundError()],
            ):
                result = doc.save(backup=False)

            self.assertTrue(result.replaced)
            self.assertFalse(result.snapshot_confirmed)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"value": 2})

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
        first = ReadStabilitySignature(1, 2, 3, 4)
        second = ReadStabilitySignature(1, 2, 4, 5)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")

            with (
                mock.patch(
                    "jsonforge.core.document.ReadStabilitySignature.from_stat",
                    side_effect=[first, second] * 3,
                ),
                mock.patch("jsonforge.core.document.time.sleep"),
            ):
                with self.assertRaises(ConcurrentModificationError):
                    JsonDocument.load(path)

    def test_load_retries_transient_snapshot_instability(self):
        first = ReadStabilitySignature(1, 2, 3, 4)
        second = ReadStabilitySignature(1, 2, 4, 5)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")

            with (
                mock.patch(
                    "jsonforge.core.document.ReadStabilitySignature.from_stat",
                    side_effect=[first, second, first, first],
                ),
                mock.patch("jsonforge.core.document.time.sleep") as sleep_mock,
            ):
                doc = JsonDocument.load(path)

            self.assertEqual(doc.data, {"value": 1})
            sleep_mock.assert_called_once_with(0.01)


if __name__ == "__main__":
    unittest.main()
