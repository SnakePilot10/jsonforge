import unittest

from jsonforge.core.search import search


class SearchTests(unittest.TestCase):
    def test_search_does_not_decode_embedded_json_by_default(self):
        data = {"settings": '{"theme":"dark"}'}
        matches = list(search(data, "dark"))
        self.assertEqual(matches, [("settings", '{"theme":"dark"}')])

    def test_search_finds_embedded_json_value_when_enabled(self):
        data = {"settings": '{"theme":"dark"}'}
        matches = list(search(data, "dark", decode_embedded=True))
        self.assertTrue(any(path == "settings.theme" for path, _ in matches))

    def test_search_does_not_duplicate_path_matches(self):
        data = {"theme": "theme"}
        matches = list(search(data, "theme"))
        self.assertEqual([path for path, _ in matches], ["theme"])

    def test_search_escapes_dot_keys(self):
        data = {"a.b": "needle"}
        matches = list(search(data, "needle"))
        self.assertEqual(matches[0][0], "a\\.b")

    def test_search_matches_raw_dotted_key(self):
        data = {"a.b": 1}
        matches = list(search(data, "a.b"))
        self.assertEqual(matches, [("a\\.b", 1)])

    def test_search_matches_raw_backslash_key(self):
        data = {"a\\b": 1}
        matches = list(search(data, "a\\b"))
        self.assertEqual(matches, [("a\\\\b", 1)])

    def test_search_finds_json_null(self):
        data = {"value": None}
        matches = list(search(data, "null"))
        self.assertEqual(matches, [("value", None)])

    def test_search_rejects_empty_query(self):
        with self.assertRaises(ValueError):
            list(search({"value": 1}, ""))

    def test_search_can_scope_to_key(self):
        data = {"needle": "no", "other": "needle"}
        matches = list(search(data, "needle", scope="key"))
        self.assertEqual(matches, [("needle", "no")])

    def test_search_can_scope_to_value(self):
        data = {"needle": "no", "other": "needle"}
        matches = list(search(data, "needle", scope="value"))
        self.assertEqual(matches, [("other", "needle")])

    def test_search_supports_limit_and_offset(self):
        data = {"a": "needle", "b": "needle", "c": "needle"}
        matches = list(search(data, "needle", scope="value", limit=1, offset=1))
        self.assertEqual(matches, [("b", "needle")])


if __name__ == "__main__":
    unittest.main()
