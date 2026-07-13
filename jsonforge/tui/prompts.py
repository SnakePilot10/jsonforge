from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter


def choose(label: str, options: list[str]) -> str:
    while True:
        answer = prompt(label, completer=WordCompleter(options, ignore_case=True, WORD=True))
        for option in options:
            if answer.lower() == option.lower():
                return option
        print(f"Choose one of: {', '.join(options)}")


def ask(label: str) -> str:
    return prompt(label)


def ask_with_completions(label: str, options: list[str]) -> str:
    return prompt(label, completer=WordCompleter(options, ignore_case=True, WORD=True))
