import json
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


if __name__ == "__main__":
    unittest.main()
