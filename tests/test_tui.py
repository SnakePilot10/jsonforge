import json
import unittest
from types import SimpleNamespace
from unittest import mock

from jsonforge.core.paths import JsonPath
from jsonforge.tui.app import contains_embedded_json, json_type_name, preview_value, run_interactive


class InteractiveTests(unittest.TestCase):
    def test_helpers_detect_embedded_json_and_summarize_types(self):
        self.assertTrue(contains_embedded_json({"flags": '{"tower":101}'}))
        self.assertFalse(contains_embedded_json({"flags": "plain text"}))
        self.assertEqual(json_type_name(101), "integer")
        self.assertEqual(json_type_name(True), "boolean")
        self.assertEqual(preview_value({"tower": 101}), "{...} (1 entry)")

    def test_set_requires_strong_confirmation_before_replacing_embedded_object(self):
        original = '{"tower_current_floor":101,"tower_best_floor":101}'
        doc = SimpleNamespace(path="sample.json", data={"flags": original})

        with (
            mock.patch("jsonforge.tui.app.JsonDocument.load", return_value=doc),
            mock.patch("jsonforge.tui.app.choose", side_effect=["3", "auto", "9"]),
            mock.patch(
                "jsonforge.tui.app.ask",
                side_effect=["", "r", "250", "REPLACE another.path"],
            ),
            mock.patch("jsonforge.tui.app.ask_with_path_completions", return_value="flags"),
            mock.patch("jsonforge.tui.app.render_path_summary") as summary_mock,
            mock.patch("jsonforge.tui.app.render_status") as status_mock,
            mock.patch("builtins.print"),
        ):
            run_interactive("sample.json")

        self.assertEqual(doc.data["flags"], original)
        summary_mock.assert_called_once_with(
            "flags",
            "object",
            storage='embedded JSON within "flags"',
            child_count=2,
            current_value=None,
        )
        status_mock.assert_called_once_with("Update cancelled.", kind="warning")

    def test_set_previews_and_applies_only_the_selected_embedded_child(self):
        doc = SimpleNamespace(
            path="sample.json",
            data={"flags": '{"tower_current_floor":101,"tower_best_floor":101}'},
        )

        with (
            mock.patch("jsonforge.tui.app.JsonDocument.load", return_value=doc),
            mock.patch("jsonforge.tui.app.choose", side_effect=["3", "9"]),
            mock.patch(
                "jsonforge.tui.app.ask",
                side_effect=["", "250", "", "yes"],
            ),
            mock.patch(
                "jsonforge.tui.app.ask_with_path_completions",
                return_value="flags.tower_current_floor",
            ),
            mock.patch("jsonforge.tui.app.render_change_preview") as preview_mock,
            mock.patch("builtins.print"),
        ):
            run_interactive("sample.json")

        flags = json.loads(doc.data["flags"])
        self.assertEqual(flags["tower_current_floor"], 250)
        self.assertEqual(flags["tower_best_floor"], 101)
        preview_mock.assert_called_once_with(
            "flags.tower_current_floor",
            "101",
            "250",
            "integer",
            "integer",
        )

    def test_search_result_can_be_selected_and_edited_in_place(self):
        doc = SimpleNamespace(
            path="sample.json",
            data={"flags": '{"tower_current_floor":101,"tower_best_floor":101}'},
        )
        match = (JsonPath(("flags", "tower_current_floor")), 101)

        with (
            mock.patch("jsonforge.tui.app.JsonDocument.load", return_value=doc),
            mock.patch("jsonforge.tui.app.choose", side_effect=["4", "all", "9"]),
            mock.patch(
                "jsonforge.tui.app.ask",
                side_effect=["tower", "", "", "", "", "1", "250", "", "yes"],
            ),
            mock.patch("jsonforge.tui.app.search", return_value=iter([match])) as search_mock,
            mock.patch("jsonforge.tui.app.render_search_results") as results_mock,
            mock.patch("builtins.print"),
        ):
            run_interactive("sample.json")

        search_mock.assert_called_once_with(
            doc.data,
            "tower",
            scope="all",
            exact=False,
            limit=50,
            offset=0,
            decode_embedded=True,
        )
        results_mock.assert_called_once_with(
            "tower",
            [(1, "flags.tower_current_floor", "integer", "101")],
        )
        flags = json.loads(doc.data["flags"])
        self.assertEqual(flags["tower_current_floor"], 250)
        self.assertEqual(flags["tower_best_floor"], 101)

    def test_tree_can_decode_embedded_json(self):
        doc = SimpleNamespace(path="sample.json", data={"settings": '{"enabled":true}'})

        with (
            mock.patch("jsonforge.tui.app.JsonDocument.load", return_value=doc),
            mock.patch("jsonforge.tui.app.choose", side_effect=["7", "9"]),
            mock.patch("jsonforge.tui.app.ask", side_effect=["", "", "yes"]),
            mock.patch("jsonforge.tui.app.iter_paths", return_value=iter([])) as paths_mock,
            mock.patch("builtins.print"),
        ):
            run_interactive("sample.json")

        paths_mock.assert_called_once_with(doc.data, max_depth=2, decode_embedded=True)


if __name__ == "__main__":
    unittest.main()
