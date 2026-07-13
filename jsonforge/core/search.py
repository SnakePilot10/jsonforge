from collections.abc import Iterator
from typing import Any, Literal

from .embedded_json import decode_if_embedded_json
from .paths import join_path

SearchScope = Literal["key", "path", "value", "all"]


def _searchable_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def search(
    data: Any,
    query: str,
    path: str = "",
    *,
    scope: SearchScope = "all",
    exact: bool = False,
    limit: int | None = None,
    offset: int = 0,
    decode_embedded: bool = False,
) -> Iterator[tuple[str, Any]]:
    if not query:
        raise ValueError("Search query must not be empty")
    if limit is not None and limit < 0:
        raise ValueError("Search limit must not be negative")
    if offset < 0:
        raise ValueError("Search offset must not be negative")

    needle = query if exact else query.lower()
    skipped = emitted = 0
    stack: list[tuple[Any, str, str | None]] = [(data, path, None)]

    while stack:
        value, current_path, key_name = stack.pop()
        decoded = decode_if_embedded_json(value, enabled=decode_embedded)
        current = decoded.value

        if _matches(current, current_path, key_name, needle, scope, exact):
            if skipped < offset:
                skipped += 1
            else:
                yield current_path, current
                emitted += 1
                if limit is not None and emitted >= limit:
                    return
        if isinstance(current, dict):
            children = list(current.items())
            for key, child in reversed(children):
                stack.append((child, join_path(current_path, str(key)), str(key)))
        elif isinstance(current, list):
            for index in range(len(current) - 1, -1, -1):
                child_path = f"{current_path}.{index}" if current_path else str(index)
                stack.append((current[index], child_path, None))


def _text_matches(text: str, needle: str, exact: bool) -> bool:
    haystack = text if exact else text.lower()
    return haystack == needle if exact else needle in haystack


def _matches(
    value: Any,
    path: str,
    key_name: str | None,
    needle: str,
    scope: SearchScope,
    exact: bool,
) -> bool:
    if scope in {"key", "all"} and key_name is not None and _text_matches(key_name, needle, exact):
        return True
    if scope in {"path", "all"} and path and _text_matches(path, needle, exact):
        return True
    if scope in {"value", "all"} and not isinstance(value, (dict, list)):
        return _text_matches(_searchable_scalar(value), needle, exact)
    return False
