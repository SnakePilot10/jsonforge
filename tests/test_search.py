import unittest

from jsonforge.core.paths import JsonPath
from jsonforge.core.search import format_search_display, format_search_line, search


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

    def test_search_display_scope_is_strict_to_display_path_format(self):
        data = {"settings": {"enabled": True}}

        # Consulta en formato pointer buscando en display con formato de salida dot
        # No debe coincidir porque la cadena display final es "settings.enabled: true"
        matches1 = list(
            search(
                data,
                "/settings/enabled: true",
                scope="display",
                display_path_format="dot",
            )
        )
        self.assertEqual(matches1, [])

        # Debe coincidir si especificamos display_path_format="pointer"
        matches2 = list(
            search(
                data,
                "/settings/enabled: true",
                scope="display",
                display_path_format="pointer",
            )
        )
        self.assertEqual(matches2, [(JsonPath(("settings", "enabled")), True)])

        # Consulta en formato dot buscando en display con formato de salida pointer
        # No debe coincidir porque la cadena display es "/settings/enabled: true"
        matches3 = list(
            search(
                data,
                "settings.enabled: true",
                scope="display",
                display_path_format="pointer",
            )
        )
        self.assertEqual(matches3, [])

    def test_search_exact_with_path_and_display(self):
        data = {"settings": {"enabled": True}}

        # Búsqueda exacta en path
        self.assertEqual(len(list(search(data, "settings.enabled", scope="path", exact=True))), 1)
        self.assertEqual(len(list(search(data, "settings.enable", scope="path", exact=True))), 0)

        # Búsqueda exacta en display
        self.assertEqual(
            len(
                list(
                    search(
                        data,
                        "settings.enabled: true",
                        scope="display",
                        exact=True,
                        display_path_format="dot",
                    )
                )
            ),
            1,
        )
        self.assertEqual(
            len(
                list(
                    search(
                        data,
                        "settings.enabled: tru",
                        scope="display",
                        exact=True,
                        display_path_format="dot",
                    )
                )
            ),
            0,
        )

    def test_search_pointer_with_special_characters(self):
        data = {"a/b": {"c~d": "needle"}}

        # Coincidencia con path usando escapes JSON Pointer canónicos
        matches = list(search(data, "/a~1b/c~0d", scope="path"))
        self.assertEqual(matches, [(JsonPath(("a/b", "c~d")), "needle")])

    def test_search_display_respects_preview_limit(self):
        data = {"message": "a" * 50 + " needle"}

        # Si buscamos "needle" en display con preview=10, el valor se acorta
        # a "aaaaaaa..." y "needle" no debe coincidir.
        matches = list(
            search(
                data,
                "needle",
                scope="display",
                display_path_format="dot",
                preview=10,
            )
        )
        self.assertEqual(matches, [])

        # Sin preview (o con preview suficientemente largo), sí debe coincidir.
        matches_full = list(
            search(
                data,
                "needle",
                scope="display",
                display_path_format="dot",
            )
        )
        self.assertEqual(len(matches_full), 1)

    def test_format_search_line_rejects_too_small_preview(self):
        with self.assertRaisesRegex(ValueError, "greater than or equal to 3"):
            format_search_line(
                JsonPath(("message",)),
                "value",
                path_format="dot",
                preview=2,
            )

    def test_search_rejects_too_small_preview_before_traversal(self):
        with self.assertRaisesRegex(ValueError, "greater than or equal to 3"):
            list(search({"message": "value"}, "x", preview=-10, limit=0))

    def test_search_display_path_format_validation(self):
        with self.assertRaisesRegex(ValueError, "Unsupported display path format"):
            list(search({"a": 1}, "x", scope="display", display_path_format="banana"))


if __name__ == "__main__":
    unittest.main()
