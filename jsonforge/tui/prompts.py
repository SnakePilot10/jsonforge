from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter


def choose(label: str, options: list[str]) -> str:
    return prompt(label, completer=WordCompleter(options, ignore_case=True, WORD=True))


def ask(label: str) -> str:
    return prompt(label)


def ask_with_completions(label: str, options: list[str]) -> str:
    return prompt(label, completer=WordCompleter(options, ignore_case=True, WORD=True))
