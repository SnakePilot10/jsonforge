import json
import unittest

from jsonforge.core.paths import add_path, delete_path, get_path, iter_paths, path_completions, set_path


class PathTests(unittest.TestCase):
    def test_get_path_through_objects_and_arrays(self):
        data = {"users": [{"name": "Ada"}]}
        self.assertEqual(get_path(data, "users.0.name").value, "Ada")

    def test_set_path_updates_value(self):
        data = {"settings": {"enabled": False}}
        set_path(data, "settings.enabled", True)
        self.assertIs(data["settings"]["enabled"], True)

    def test_set_path_preserves_embedded_json_string(self):
        data = {"settings": '{"enabled":false,"theme":"dark"}'}
        set_path(data, "settings.enabled", True)
        self.assertIsInstance(data["settings"], str)
        self.assertIs(json.loads(data["settings"])["enabled"], True)

    def test_add_path_to_object(self):
        data = {"settings": {}}
        add_path(data, "settings.enabled", True)
        self.assertIs(data["settings"]["enabled"], True)

    def test_add_path_to_embedded_object(self):
        data = {"settings": "{}"}
        add_path(data, "settings.enabled", True)
        self.assertIsInstance(data["settings"], str)
        self.assertIs(json.loads(data["settings"])["enabled"], True)

    def test_add_path_appends_to_array(self):
        data = {"items": ["a"]}
        add_path(data, "items.-", "b")
        self.assertEqual(data["items"], ["a", "b"])

    def test_delete_path_from_embedded_object(self):
        data = {"settings": '{"enabled":true,"theme":"dark"}'}
        delete_path(data, "settings.theme")
        self.assertNotIn("theme", json.loads(data["settings"]))

    def test_iter_paths_and_completions_include_embedded_paths(self):
        data = {"settings": '{"enabled":true}'}
        paths = [path for path, _ in iter_paths(data)]
        self.assertIn("settings.enabled", paths)
        self.assertIn("settings.enabled", path_completions(data))


if __name__ == "__main__":
    unittest.main()
