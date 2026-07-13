import unittest
from itertools import islice
from pathlib import Path

from jsonforge.core.document import JsonDocument
from jsonforge.core.paths import iter_paths
from jsonforge.core.search import search

STRESS_FIXTURE = Path(__file__).parent / "fixtures" / "json_stress_test.json"


class StressFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = JsonDocument.load(STRESS_FIXTURE)

    def test_stress_fixture_loads_with_strict_json(self):
        self.assertIsInstance(self.doc.data, dict)

    def test_iter_paths_can_be_consumed_partially(self):
        paths = list(islice(iter_paths(self.doc.data), 1000))

        self.assertEqual(len(paths), 1000)
        self.assertEqual(paths[0][0], "01_primitivos")

    def test_search_respects_limit_on_stress_fixture(self):
        matches = list(search(self.doc.data, "unicode", limit=2))

        self.assertEqual(
            [path for path, _ in matches],
            [
                "02_strings_extremos.unicode_acentos",
                "04_claves_raras.ñ_único_ǹó_àscii",
            ],
        )


if __name__ == "__main__":
    unittest.main()
