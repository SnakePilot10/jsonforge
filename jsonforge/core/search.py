from collections.abc import Iterator
from typing import Any, Literal

from .embedded_json import decode_if_embedded_json
from .paths import JsonPath, format_value, render_path

SearchScope = Literal["key", "path", "value", "display", "all"]
SEARCH_SCOPES = {"key", "path", "value", "display", "all"}
PATH_FORMATS = {"dot", "pointer"}


def _searchable_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def format_search_display(value: Any) -> str:
    if isinstance(value, dict):
        return "{...}"
    if isinstance(value, list):
        return "[...]"
    return format_value(value)


def format_search_line(
    path: JsonPath,
    value: Any,
    *,
    path_format: Literal["dot", "pointer"],
    preview: int | None = None,
) -> str:
    if preview is not None and preview < 3:
        raise ValueError("Preview must be greater than or equal to 3")

    rendered_path = render_path(path, path_format)
    rendered_value = format_search_display(value).replace("\n", " ")

    if preview is not None and len(rendered_value) > preview:
        rendered_value = rendered_value[: preview - 3] + "..."

    return f"{rendered_path}: {rendered_value}"


def search(
    data: Any,
    query: str,
    path: str | JsonPath | None = None,
    *,
    scope: SearchScope = "all",
    exact: bool = False,
    limit: int | None = None,
    offset: int = 0,
    decode_embedded: bool = False,
    display_path_format: Literal["dot", "pointer"] = "dot",
    preview: int | None = None,
) -> Iterator[tuple[JsonPath, Any]]:
    if not query:
        raise ValueError("Search query must not be empty")
    if limit is not None and limit < 0:
        raise ValueError("Search limit must not be negative")
    if offset < 0:
        raise ValueError("Search offset must not be negative")
    if scope not in SEARCH_SCOPES:
        raise ValueError(f"Unsupported search scope: {scope}")
    if display_path_format not in PATH_FORMATS:
        raise ValueError(f"Unsupported display path format: {display_path_format}")
    if preview is not None and preview < 3:
        raise ValueError("Preview must be greater than or equal to 3")
    if limit == 0:
        return

    if path is None:
        path = JsonPath(())
    elif isinstance(path, str):
        path = JsonPath.from_dot(path) if path else JsonPath(())

    needle = query if exact else query.lower()
    skipped = emitted = 0
    stack: list[tuple[Any, JsonPath, str | None]] = [(data, path, None)]

    while stack:
        value, current_path, key_name = stack.pop()
        decoded = decode_if_embedded_json(value, enabled=decode_embedded)
        current = decoded.value

        if _matches(
            current,
            current_path,
            key_name,
            needle,
            scope,
            exact,
            display_path_format,
            preview,
        ):
            if skipped < offset:
                skipped += 1
            else:
                yield current_path, current
                emitted += 1
                if limit is not None and emitted >= limit:
                    return
        if isinstance(current, dict):
            for key in reversed(current):
                child_path = JsonPath(current_path.parts + (str(key),))
                stack.append((current[key], child_path, str(key)))
        elif isinstance(current, list):
            for index in range(len(current) - 1, -1, -1):
                child_path = JsonPath(current_path.parts + (str(index),))
                stack.append((current[index], child_path, None))


def _text_matches(text: str, needle: str, exact: bool) -> bool:
    haystack = text if exact else text.lower()
    return haystack == needle if exact else needle in haystack


def _matches(
    value: Any,
    path: JsonPath,
    key_name: str | None,
    needle: str,
    scope: SearchScope,
    exact: bool,
    display_path_format: Literal["dot", "pointer"] = "dot",
    preview: int | None = None,
) -> bool:
    if scope in {"key", "all"} and key_name is not None and _text_matches(key_name, needle, exact):
        return True
    if scope == "path" and path.parts:
        try:
            dot_path = path.to_dot()
            if _text_matches(dot_path, needle, exact):
                return True
        except ValueError:
            pass
        if _text_matches(path.to_pointer(), needle, exact):
            return True
    if scope in {"value", "all"} and not isinstance(value, (dict, list)):
        if _text_matches(_searchable_scalar(value), needle, exact):
            return True
    if scope == "display" and path.parts:
        try:
            display = format_search_line(
                path,
                value,
                path_format=display_path_format,
                preview=preview,
            )
            return _text_matches(display, needle, exact)
        except ValueError:
            return False
    return False
