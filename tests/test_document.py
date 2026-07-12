import json
import math
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

    def test_save_rejects_infinity_and_keeps_original(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            doc = JsonDocument.load(path)
            doc.data["value"] = math.inf

            with self.assertRaises(ValueError):
                doc.save()

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"value": 1})


if __name__ == "__main__":
    unittest.main()
