from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion, WordCompleter

from jsonforge.core.paths import path_completions


class PathCompleter(Completer):
    def __init__(
        self,
        data,
        *,
        decode_embedded: bool = False,
        include_append: bool = False,
    ) -> None:
        self.data = data
        self.decode_embedded = decode_embedded
        self.include_append = include_append

    def get_completions(self, document, complete_event):
        if document.cursor_position != len(document.text):
            return
        text = document.text_before_cursor
        for candidate in path_completions(
            self.data,
            text,
            decode_embedded=self.decode_embedded,
            include_append=self.include_append,
        ):
            yield Completion(candidate, start_position=-len(text))


def choose(label: str, options: list[str]) -> str:
    while True:
        answer = prompt(label, completer=WordCompleter(options, ignore_case=True, WORD=True))
        for option in options:
            if answer.lower() == option.lower():
                return option
        print(f"Choose one of: {', '.join(options)}")


def ask(label: str) -> str:
    return prompt(label)


def ask_with_path_completions(
    label: str,
    data,
    *,
    decode_embedded: bool = False,
    include_append: bool = False,
) -> str:
    return prompt(
        label,
        completer=PathCompleter(
            data,
            decode_embedded=decode_embedded,
            include_append=include_append,
        ),
    )
