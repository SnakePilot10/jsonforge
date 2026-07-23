import json
import unittest
from types import SimpleNamespace
from unittest import mock

from jsonforge.core.paths import JsonPath
from jsonforge.tui.app import (
    contains_embedded_json,
    edit_path_guided,
    json_type_name,
    preview_value,
    run_interactive,
    same_json_value,
)


class InteractiveTests(unittest.TestCase):
    def test_helpers_detect_embedded_json_and_summarize_types(self):
        self.assertTrue(contains_embedded_json({"flags": '{"tower":101}'}))
        self.assertFalse(contains_embedded_json({"flags": "plain text"}))
        self.assertEqual(json_type_name(101), "integer")
        self.assertEqual(json_type_name(True), "boolean")
        self.assertEqual(preview_value({"tower": 101}), "{...} (1 entry)")

    def test_json_value_comparison_distinguishes_equal_python_values_by_json_type(self):
        self.assertFalse(same_json_value(True, 1))
        self.assertFalse(same_json_value(1, 1.0))
        self.assertFalse(same_json_value([True], [1]))
        self.assertTrue(same_json_value({"items": [True]}, {"items": [True]}))

    def test_json_value_comparison_handles_deep_values_iteratively(self):
        left = right = None
        for _ in range(1100):
            left = [left]
            right = [right]

        self.assertTrue(same_json_value(left, right))

    def test_preview_rejects_limit_below_ellipsis_width(self):
        with self.assertRaisesRegex(ValueError, "greater than or equal to 3"):
            preview_value("value", 2)

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

    def test_delete_container_requires_strong_confirmation(self):
        doc = SimpleNamespace(path="sample.json", data={"flags": {"enabled": True}})

        with (
            mock.patch("jsonforge.tui.app.JsonDocument.load", return_value=doc),
            mock.patch("jsonforge.tui.app.choose", side_effect=["6", "9"]),
            mock.patch("jsonforge.tui.app.ask", side_effect=["", "DELETE another.path"]),
            mock.patch("jsonforge.tui.app.ask_with_path_completions", return_value="flags"),
            mock.patch("builtins.print"),
        ):
            run_interactive("sample.json")

        self.assertEqual(doc.data, {"flags": {"enabled": True}})

    def test_container_browser_can_reach_entries_after_first_page(self):
        doc = SimpleNamespace(data={"items": {f"key{index}": index for index in range(60)}})

        with (
            mock.patch(
                "jsonforge.tui.app.ask",
                side_effect=["n", "10", "250", ""],
            ),
            mock.patch("jsonforge.tui.app.render_container_children") as children_mock,
            mock.patch("jsonforge.tui.app.render_path_summary"),
            mock.patch("jsonforge.tui.app.render_change_preview"),
            mock.patch("jsonforge.tui.app.render_status"),
        ):
            changed = edit_path_guided(doc, "items", decode_embedded=False)

        self.assertTrue(changed)
        self.assertEqual(doc.data["items"]["key59"], 250)
        self.assertEqual(children_mock.call_count, 2)
        self.assertIn("Page 2/2", children_mock.call_args_list[1].kwargs["caption"])

    def test_guided_edit_can_change_scalar_type(self):
        doc = SimpleNamespace(data={"value": 101})

        with (
            mock.patch("jsonforge.tui.app.ask", side_effect=[":type", "unknown", ""]),
            mock.patch("jsonforge.tui.app.choose", return_value="string"),
            mock.patch("jsonforge.tui.app.render_path_summary"),
            mock.patch("jsonforge.tui.app.render_change_preview"),
            mock.patch("jsonforge.tui.app.render_status"),
        ):
            changed = edit_path_guided(doc, "value", decode_embedded=False)

        self.assertTrue(changed)
        self.assertEqual(doc.data["value"], "unknown")

    def test_guided_edit_does_not_treat_boolean_to_integer_as_noop(self):
        doc = SimpleNamespace(data={"value": True})

        with (
            mock.patch("jsonforge.tui.app.ask", side_effect=[":type", "1", ""]),
            mock.patch("jsonforge.tui.app.choose", return_value="int"),
            mock.patch("jsonforge.tui.app.render_path_summary"),
            mock.patch("jsonforge.tui.app.render_change_preview"),
            mock.patch("jsonforge.tui.app.render_status"),
        ):
            changed = edit_path_guided(doc, "value", decode_embedded=False)

        self.assertTrue(changed)
        self.assertIs(type(doc.data["value"]), int)
        self.assertEqual(doc.data["value"], 1)

    def test_guided_edit_can_change_null_to_value(self):
        doc = SimpleNamespace(data={"value": None})

        with (
            mock.patch("jsonforge.tui.app.ask", side_effect=[":type", "250", ""]),
            mock.patch("jsonforge.tui.app.choose", return_value="int"),
            mock.patch("jsonforge.tui.app.render_path_summary"),
            mock.patch("jsonforge.tui.app.render_change_preview"),
            mock.patch("jsonforge.tui.app.render_status"),
        ):
            changed = edit_path_guided(doc, "value", decode_embedded=False)

        self.assertTrue(changed)
        self.assertEqual(doc.data["value"], 250)

    def test_save_without_changes_does_not_write(self):
        doc = SimpleNamespace(path="sample.json", data={"value": 1}, save=mock.Mock())

        with (
            mock.patch("jsonforge.tui.app.JsonDocument.load", return_value=doc),
            mock.patch("jsonforge.tui.app.choose", side_effect=["8", "9"]),
            mock.patch("jsonforge.tui.app.render_status") as status_mock,
            mock.patch("builtins.print"),
        ):
            run_interactive("sample.json")

        doc.save.assert_not_called()
        status_mock.assert_called_once_with("No changes to save.", kind="info")

    def test_unconfirmed_snapshot_ends_session_after_save(self):
        result = SimpleNamespace(
            backup_path=None,
            durability_confirmed=True,
            snapshot_confirmed=False,
        )
        doc = SimpleNamespace(
            path="sample.json",
            data={"value": 1},
            save=mock.Mock(return_value=result),
        )

        with (
            mock.patch("jsonforge.tui.app.JsonDocument.load", return_value=doc),
            mock.patch("jsonforge.tui.app.choose", side_effect=["3", "8"]),
            mock.patch("jsonforge.tui.app.ask", side_effect=["2", ""]),
            mock.patch("jsonforge.tui.app.ask_with_path_completions", return_value="value"),
            mock.patch("jsonforge.tui.app.render_status") as status_mock,
            mock.patch("builtins.print"),
        ):
            run_interactive("sample.json")

        doc.save.assert_called_once_with(backup=True)
        status_mock.assert_called_with(
            "The file was written, but its current state could not be re-verified. "
            "Reload the document before making additional changes.",
            kind="error",
        )


if __name__ == "__main__":
    unittest.main()
