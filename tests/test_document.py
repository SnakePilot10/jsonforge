import json
import math
import os
import stat
import tempfile
import unittest
from pathlib import Path

from jsonforge.core.document import JsonDocument


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

            self.assertTrue(backup_path.exists())
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"a": 2})
            self.assertEqual(json.loads(backup_path.read_text(encoding="utf-8")), {"a": 1})

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


if __name__ == "__main__":
    unittest.main()
