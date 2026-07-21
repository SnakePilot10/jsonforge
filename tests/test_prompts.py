import unittest

from prompt_toolkit.document import Document

from jsonforge.tui.prompts import PathCompleter


class PathCompleterTests(unittest.TestCase):
    def test_replaces_the_full_partial_path_with_contextual_candidate(self):
        completer = PathCompleter({"users": [{"name": "Ada"}]})

        completions = list(completer.get_completions(Document("users.0.n"), None))

        self.assertEqual(len(completions), 1)
        self.assertEqual(completions[0].text, "users.0.name")
        self.assertEqual(completions[0].start_position, -len("users.0.n"))

    def test_can_suggest_array_append_for_add_flow(self):
        completer = PathCompleter({"users": []}, include_append=True)

        completions = list(completer.get_completions(Document("users."), None))

        self.assertEqual([completion.text for completion in completions], ["users.-"])

    def test_container_completion_invites_deeper_navigation(self):
        completer = PathCompleter({"flags": {"tower_current_floor": 101}})

        completions = list(completer.get_completions(Document("fla"), None))

        self.assertEqual([completion.text for completion in completions], ["flags."])

    def test_does_not_complete_when_cursor_is_in_middle_of_path(self):
        completer = PathCompleter({"users": [{"name": "Ada"}]})
        document = Document("users.0.name", cursor_position=len("users.0.n"))

        completions = list(completer.get_completions(document, None))

        self.assertEqual(completions, [])


if __name__ == "__main__":
    unittest.main()
