import unittest

from jsonforge.core.search import search


class SearchTests(unittest.TestCase):
    def test_search_finds_embedded_json_value(self):
        data = {"settings": '{"theme":"dark"}'}
        matches = list(search(data, "dark"))
        self.assertTrue(any(path == "settings.theme" for path, _ in matches))

    def test_search_does_not_duplicate_path_matches(self):
        data = {"theme": "theme"}
        matches = list(search(data, "theme"))
        self.assertEqual([path for path, _ in matches], ["theme"])

    def test_search_escapes_dot_keys(self):
        data = {"a.b": "needle"}
        matches = list(search(data, "needle"))
        self.assertEqual(matches[0][0], "a\\.b")


if __name__ == "__main__":
    unittest.main()
