import json
import unittest

from jsonforge.core.paths import (
    JsonPath,
    add_path,
    delete_path,
    get_path,
    iter_paths,
    path_completions,
    set_path,
)


class PathTests(unittest.TestCase):
    def test_get_path_through_objects_and_arrays(self):
        data = {"users": [{"name": "Ada"}]}
        self.assertEqual(get_path(data, "users.0.name").value, "Ada")

    def test_json_path_from_dot(self):
        self.assertEqual(JsonPath.from_dot("users.0.name"), JsonPath(("users", "0", "name")))

    def test_json_pointer_round_trip(self):
        path = JsonPath.from_pointer("/users/0/name")
        self.assertEqual(path, JsonPath(("users", "0", "name")))
        self.assertEqual(path.to_pointer(), "/users/0/name")

    def test_json_pointer_escapes_slash_and_tilde(self):
        path = JsonPath.from_pointer("/a~1b/a~0b")
        self.assertEqual(path, JsonPath(("a/b", "a~b")))
        self.assertEqual(path.to_pointer(), "/a~1b/a~0b")

    def test_json_pointer_empty_key(self):
        self.assertEqual(JsonPath.from_pointer("/"), JsonPath(("",)))
        self.assertEqual(JsonPath(("",)).to_pointer(), "/")

    def test_json_path_to_dot_rejects_single_empty_key(self):
        with self.assertRaises(ValueError):
            JsonPath.from_pointer("/").to_dot()

    def test_json_path_to_dot_preserves_leading_empty_key_when_unambiguous(self):
        self.assertEqual(JsonPath.from_pointer("//name").to_dot(), ".name")

    def test_json_path_to_dot_escapes_dot_keys(self):
        self.assertEqual(JsonPath(("a.b", "c\\d")).to_dot(), "a\\.b.c\\\\d")

    def test_json_pointer_root(self):
        self.assertEqual(JsonPath.from_pointer(""), JsonPath(()))
        self.assertEqual(JsonPath(()).to_pointer(), "")

    def test_get_path_with_json_pointer(self):
        data = {"users": [{"name": "Ada"}], "a/b": 1, "a~b": 2, "": 3}
        self.assertEqual(get_path(data, "/users/0/name", path_format="pointer").value, "Ada")
        self.assertEqual(get_path(data, "/a~1b", path_format="pointer").value, 1)
        self.assertEqual(get_path(data, "/a~0b", path_format="pointer").value, 2)
        self.assertEqual(get_path(data, "/", path_format="pointer").value, 3)

    def test_json_pointer_rejects_invalid_escape(self):
        with self.assertRaises(ValueError):
            JsonPath.from_pointer("/a~2b")

    def test_json_pointer_rejects_relative_pointer(self):
        with self.assertRaises(ValueError):
            JsonPath.from_pointer("users/0")

    def test_json_pointer_array_index_rejects_leading_zero(self):
        with self.assertRaises(TypeError):
            get_path(["a", "b"], "/01", path_format="pointer")

    def test_json_pointer_array_index_rejects_unicode_digit(self):
        with self.assertRaises(TypeError):
            get_path(["a", "b"], "/١", path_format="pointer")

    def test_json_pointer_get_rejects_dash_array_index(self):
        with self.assertRaises(TypeError):
            get_path(["a", "b"], "/-", path_format="pointer")

    def test_numeric_object_keys_remain_strings(self):
        data = {"0": "zero", "items": ["first"]}
        self.assertEqual(get_path(data, "0").value, "zero")
        self.assertEqual(get_path(data, "items.0").value, "first")

    def test_escaped_dot_in_object_key(self):
        data = {"a.b": {"c\\d": 1}}
        self.assertEqual(get_path(data, "a\\.b.c\\\\d").value, 1)

    def test_set_path_updates_value(self):
        data = {"settings": {"enabled": False}}
        set_path(data, "settings.enabled", True)
        self.assertIs(data["settings"]["enabled"], True)

    def test_set_path_accepts_json_pointer(self):
        data = {"users": [{"name": "Grace"}], "a/b": 1}
        set_path(data, "/users/0/name", "Ada", path_format="pointer")
        set_path(data, "/a~1b", 2, path_format="pointer")
        self.assertEqual(data, {"users": [{"name": "Ada"}], "a/b": 2})

    def test_set_path_accepts_json_path(self):
        data = {"users": [{"name": "Grace"}]}
        set_path(data, JsonPath(("users", "0", "name")), "Ada")
        self.assertEqual(data["users"][0]["name"], "Ada")

    def test_set_path_rejects_leading_zero_array_index(self):
        data = {"items": ["a", "b"]}
        with self.assertRaises(TypeError):
            set_path(data, "items.01", "x")

    def test_set_path_does_not_traverse_embedded_json_string_by_default(self):
        data = {"settings": '{"enabled":false,"theme":"dark"}'}
        with self.assertRaises(TypeError):
            set_path(data, "settings.enabled", True)
        self.assertIsInstance(data["settings"], str)
        self.assertIs(json.loads(data["settings"])["enabled"], False)

    def test_set_path_can_traverse_embedded_json_string_when_enabled(self):
        data = {"settings": '{"enabled":false,"theme":"dark"}'}
        data = set_path(data, "settings.enabled", True, decode_embedded=True)
        self.assertIsInstance(data["settings"], str)
        self.assertIs(json.loads(data["settings"])["enabled"], True)

    def test_set_embedded_node_preserves_string_storage(self):
        data = {"settings": '{"theme":"dark"}'}

        data = set_path(data, "settings", {"theme": "light"}, decode_embedded=True)

        self.assertIsInstance(data["settings"], str)
        self.assertEqual(json.loads(data["settings"]), {"theme": "light"})

    def test_set_embedded_array_preserves_string_storage(self):
        data = {"items": "[1,2]"}

        data = set_path(data, "items", [3, 4], decode_embedded=True)

        self.assertIsInstance(data["items"], str)
        self.assertEqual(json.loads(data["items"]), [3, 4])

    def test_set_nested_embedded_strings_preserves_both_layers(self):
        data = {"outer": '{"inner":"{\\"a\\":1}"}'}

        data = set_path(data, "outer.inner.a", 2, decode_embedded=True)

        self.assertIsInstance(data["outer"], str)
        outer = json.loads(data["outer"])
        self.assertIsInstance(outer["inner"], str)
        self.assertEqual(json.loads(outer["inner"]), {"a": 2})

    def test_root_embedded_json_set_requires_decode_embedded(self):
        data = '{"enabled":false}'
        data = set_path(data, "enabled", True, decode_embedded=True)
        self.assertIsInstance(data, str)
        self.assertIs(json.loads(data)["enabled"], True)

    def test_add_path_to_object(self):
        data = {"settings": {}}
        data = add_path(data, "settings.enabled", True)
        self.assertIs(data["settings"]["enabled"], True)

    def test_add_path_rejects_existing_object_key(self):
        data = {"settings": {"enabled": False}}
        with self.assertRaises(KeyError):
            add_path(data, "settings.enabled", True)
        self.assertIs(data["settings"]["enabled"], False)

    def test_add_path_force_replaces_existing_object_key(self):
        data = {"settings": {"enabled": False}}
        add_path(data, "settings.enabled", True, force=True)
        self.assertIs(data["settings"]["enabled"], True)

    def test_add_path_to_embedded_object_requires_decode_embedded(self):
        data = {"settings": "{}"}
        data = add_path(data, "settings.enabled", True, decode_embedded=True)
        self.assertIsInstance(data["settings"], str)
        self.assertIs(json.loads(data["settings"])["enabled"], True)

    def test_root_embedded_json_add_requires_decode_embedded(self):
        data = "{}"
        data = add_path(data, "enabled", True, decode_embedded=True)
        self.assertIsInstance(data, str)
        self.assertIs(json.loads(data)["enabled"], True)

    def test_add_path_appends_to_array(self):
        data = {"items": ["a"]}
        data = add_path(data, "items.-", "b")
        self.assertEqual(data["items"], ["a", "b"])

    def test_add_path_accepts_json_pointer(self):
        data = {"users": [{"name": "Ada"}], "a/b": {}}
        add_path(data, "/users/-", {"name": "New"}, path_format="pointer")
        add_path(data, "/a~1b/new", True, path_format="pointer")
        self.assertEqual(data["users"], [{"name": "Ada"}, {"name": "New"}])
        self.assertIs(data["a/b"]["new"], True)

    def test_add_path_rejects_out_of_range_array_index(self):
        data = {"items": ["a"]}
        with self.assertRaises(IndexError):
            add_path(data, "items.999", "b")

    def test_add_path_rejects_negative_array_index(self):
        data = {"items": ["a"]}
        with self.assertRaises(TypeError):
            add_path(data, "items.-1", "b")

    def test_add_path_rejects_leading_zero_array_index(self):
        data = {"items": ["a", "b"]}
        with self.assertRaises(TypeError):
            add_path(data, "items.01", "c")

    def test_delete_path_from_embedded_object_requires_decode_embedded(self):
        data = {"settings": '{"enabled":true,"theme":"dark"}'}
        data = delete_path(data, "settings.theme", decode_embedded=True)
        self.assertNotIn("theme", json.loads(data["settings"]))

    def test_delete_path_accepts_json_pointer(self):
        data = {"users": [{"name": "Ada"}, {"name": "New"}], "obsolete": True}
        delete_path(data, "/users/1", path_format="pointer")
        delete_path(data, "/obsolete", path_format="pointer")
        self.assertEqual(data, {"users": [{"name": "Ada"}]})

    def test_root_embedded_json_delete_requires_decode_embedded(self):
        data = '{"enabled":true,"theme":"dark"}'
        data = delete_path(data, "theme", decode_embedded=True)
        self.assertIsInstance(data, str)
        self.assertNotIn("theme", json.loads(data))

    def test_delete_path_rejects_negative_array_index(self):
        data = {"items": ["a", "b"]}
        with self.assertRaises(TypeError):
            delete_path(data, "items.-1")
        self.assertEqual(data["items"], ["a", "b"])

    def test_delete_path_rejects_non_numeric_array_index(self):
        data = {"items": ["a", "b"]}
        with self.assertRaises(TypeError):
            delete_path(data, "items.one")
        self.assertEqual(data["items"], ["a", "b"])

    def test_delete_path_rejects_leading_zero_array_index(self):
        data = {"items": ["a", "b"]}
        with self.assertRaises(TypeError):
            delete_path(data, "items.01")
        self.assertEqual(data["items"], ["a", "b"])

    def test_iter_paths_and_completions_do_not_include_embedded_paths_by_default(self):
        data = {"settings": '{"enabled":true}'}
        paths = [path for path, _ in iter_paths(data)]
        self.assertEqual(paths, ["settings"])
        self.assertNotIn("settings.enabled", path_completions(data))

    def test_iter_paths_and_completions_include_embedded_paths_when_enabled(self):
        data = {"settings": '{"enabled":true}'}
        paths = [path for path, _ in iter_paths(data, decode_embedded=True)]
        self.assertIn("settings.enabled", paths)
        self.assertIn("settings.enabled", path_completions(data, decode_embedded=True))

    def test_iter_paths_escapes_dot_keys(self):
        data = {"a.b": 1}
        self.assertIn("a\\.b", path_completions(data))


if __name__ == "__main__":
    unittest.main()
