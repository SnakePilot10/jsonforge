import json
import unittest

from jsonforge.core.paths import (
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

    def test_add_path_rejects_out_of_range_array_index(self):
        data = {"items": ["a"]}
        with self.assertRaises(IndexError):
            add_path(data, "items.999", "b")

    def test_add_path_rejects_negative_array_index(self):
        data = {"items": ["a"]}
        with self.assertRaises(TypeError):
            add_path(data, "items.-1", "b")

    def test_delete_path_from_embedded_object_requires_decode_embedded(self):
        data = {"settings": '{"enabled":true,"theme":"dark"}'}
        data = delete_path(data, "settings.theme", decode_embedded=True)
        self.assertNotIn("theme", json.loads(data["settings"]))

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
