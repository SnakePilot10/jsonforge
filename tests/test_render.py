import io
import unittest
from unittest import mock

from rich.console import Console

from jsonforge.tui import render


class RenderTests(unittest.TestCase):
    def test_search_results_render_as_a_readable_table_without_color(self):
        output = io.StringIO()
        console = Console(file=output, force_terminal=False, width=80)

        with mock.patch.object(render, "console", console):
            render.render_search_results(
                "tower",
                [(1, "flags.tower_current_floor", "integer", "101")],
            )

        rendered = output.getvalue()
        self.assertIn('Results for "tower"', rendered)
        self.assertIn("flags.tower_current_floor", rendered)
        self.assertIn("integer", rendered)
        self.assertIn("101", rendered)

    def test_change_preview_includes_path_values_and_types(self):
        output = io.StringIO()
        console = Console(file=output, force_terminal=False, width=60)

        with mock.patch.object(render, "console", console):
            render.render_change_preview(
                "flags.tower_current_floor",
                "101",
                "250",
                "integer",
                "integer",
            )

        rendered = output.getvalue()
        self.assertIn("Pending change", rendered)
        self.assertIn("flags.tower_current_floor", rendered)
        self.assertIn("101", rendered)
        self.assertIn("250", rendered)
        self.assertIn("integer -> integer", rendered)


if __name__ == "__main__":
    unittest.main()
