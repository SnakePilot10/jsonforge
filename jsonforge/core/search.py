from typing import Any, Iterator

from .embedded_json import decode_if_embedded_json
from .paths import join_path


def _searchable_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def search(data: Any, query: str, path: str = "") -> Iterator[tuple[str, Any]]:
    needle = query.lower()

    yielded: set[str] = set()

    def emit(result_path: str, value: Any):
        if result_path not in yielded:
            yielded.add(result_path)
            yield result_path, value

    yield from _search(data, needle, path, emit)


def _search(data: Any, needle: str, path: str, emit) -> Iterator[tuple[str, Any]]:
    decoded = decode_if_embedded_json(data)
    current = decoded.value

    path_matches = bool(path and needle in path.lower())
    value_matches = not isinstance(current, (dict, list)) and needle in _searchable_scalar(current).lower()
    if path_matches or value_matches:
        yield from emit(path, current)

    if isinstance(current, dict):
        for key, value in current.items():
            child_path = join_path(path, str(key))
            yield from _search(value, needle, child_path, emit)
    elif isinstance(current, list):
        for index, value in enumerate(current):
            child_path = f"{path}.{index}" if path else str(index)
            yield from _search(value, needle, child_path, emit)
