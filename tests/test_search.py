import unittest

from jsonforge.core.paths import JsonPath
from jsonforge.core.search import format_search_display, search


class SearchTests(unittest.TestCase):
    def test_search_does_not_decode_embedded_json_by_default(self):
        data = {"settings": '{"theme":"dark"}'}
        matches = list(search(data, "dark"))
        self.assertEqual(matches, [(JsonPath(("settings",)), '{"theme":"dark"}')])

    def test_search_finds_embedded_json_value_when_enabled(self):
        data = {"settings": '{"theme":"dark"}'}
        matches = list(search(data, "dark", decode_embedded=True))
        self.assertTrue(any(path == JsonPath(("settings", "theme")) for path, _ in matches))

    def test_search_does_not_duplicate_path_matches(self):
        data = {"theme": "theme"}
        matches = list(search(data, "theme"))
        self.assertEqual([path for path, _ in matches], [JsonPath(("theme",))])

    def test_search_escapes_dot_keys(self):
        data = {"a.b": "needle"}
        matches = list(search(data, "needle"))
        self.assertEqual(matches[0][0], JsonPath(("a.b",)))

    def test_search_matches_raw_dotted_key(self):
        data = {"a.b": 1}
        matches = list(search(data, "a.b"))
        self.assertEqual(matches, [(JsonPath(("a.b",)), 1)])

    def test_search_matches_raw_backslash_key(self):
        data = {"a\\b": 1}
        matches = list(search(data, "a\\b"))
        self.assertEqual(matches, [(JsonPath(("a\\b",)), 1)])

    def test_search_finds_json_null(self):
        data = {"value": None}
        matches = list(search(data, "null"))
        self.assertEqual(matches, [(JsonPath(("value",)), None)])

    def test_search_rejects_empty_query(self):
        with self.assertRaises(ValueError):
            list(search({"value": 1}, ""))

    def test_search_can_scope_to_key(self):
        data = {"needle": "no", "other": "needle"}
        matches = list(search(data, "needle", scope="key"))
        self.assertEqual(matches, [(JsonPath(("needle",)), "no")])

    def test_search_can_scope_to_value(self):
        data = {"needle": "no", "other": "needle"}
        matches = list(search(data, "needle", scope="value"))
        self.assertEqual(matches, [(JsonPath(("other",)), "needle")])

    def test_search_supports_limit_and_offset(self):
        data = {"a": "needle", "b": "needle", "c": "needle"}
        matches = list(search(data, "needle", scope="value", limit=1, offset=1))
        self.assertEqual(matches, [(JsonPath(("b",)), "needle")])

    def test_search_limit_zero_returns_no_matches(self):
        self.assertEqual(list(search({"a": "needle"}, "needle", limit=0)), [])

    def test_search_display_matches_printed_line(self):
        data = {"flags": {"tower_best_floor": 101}}
        matches = list(search(data, "flags.tower_best_floor: 101", scope="display"))
        self.assertEqual(matches, [(JsonPath(("flags", "tower_best_floor")), 101)])

    def test_search_display_matches_printed_string_line(self):
        data = {"name": "Ada"}
        matches = list(search(data, 'name: "Ada"', scope="display"))
        self.assertEqual(matches, [(JsonPath(("name",)), "Ada")])

    def test_search_display_matches_escaped_string_line(self):
        data = {"message": "line\nbreak"}
        matches = list(search(data, 'message: "line\\nbreak"', scope="display"))
        self.assertEqual(matches, [(JsonPath(("message",)), "line\nbreak")])

    def test_search_display_uses_compact_container_placeholders(self):
        data = {"flags": {"tower_best_floor": 101}, "items": [1, 2]}

        self.assertEqual(
            list(search(data, "flags: {...}", scope="display")),
            [(JsonPath(("flags",)), data["flags"])],
        )
        self.assertEqual(
            list(search(data, "items: [...]", scope="display")),
            [(JsonPath(("items",)), [1, 2])],
        )

    def test_format_search_display_matches_container_search_placeholders(self):
        self.assertEqual(format_search_display({"a": 1}), "{...}")
        self.assertEqual(format_search_display([1, 2]), "[...]")
        self.assertEqual(format_search_display("Ada"), '"Ada"')

    def test_search_rejects_unknown_scope(self):
        with self.assertRaisesRegex(ValueError, "Unsupported search scope"):
            list(search({"a": 1}, "a", scope="banana"))

    def test_search_all_does_not_match_descendants_by_ancestor_path(self):
        data = {"flags": {"tower_best_floor": 101}}
        matches = list(search(data, "flags"))
        self.assertEqual(matches, [(JsonPath(("flags",)), {"tower_best_floor": 101})])

    def test_search_matches_both_dot_path_and_json_pointer(self):
        data = {"settings": {"theme.color": "blue"}}
        # Buscar por dot-path escapado
        matches_dot = list(search(data, "settings.theme\\.color", scope="path"))
        self.assertEqual(matches_dot, [(JsonPath(("settings", "theme.color")), "blue")])

        # Buscar por JSON Pointer
        matches_ptr = list(search(data, "/settings/theme.color", scope="path"))
        self.assertEqual(matches_ptr, [(JsonPath(("settings", "theme.color")), "blue")])


if __name__ == "__main__":
    unittest.main()
