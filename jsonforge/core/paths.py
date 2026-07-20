import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

from .embedded_json import decode_if_embedded_json, encode_if_needed

ARRAY_INDEX_PATTERN = re.compile(r"0|[1-9][0-9]*")
PathFormat = Literal["dot", "pointer"]


@dataclass
class PathMatch:
    value: Any
    decoded_embedded_segments: int = 0


@dataclass(frozen=True)
class JsonPath:
    parts: tuple[str, ...] = ()

    @classmethod
    def from_dot(cls, path: str) -> "JsonPath":
        return cls(tuple(split_path(path)))

    @classmethod
    def from_pointer(cls, pointer: str) -> "JsonPath":
        return parse_json_pointer(pointer)

    def to_dot(self) -> str:
        if self.parts == ("",):
            raise ValueError("This path cannot be represented unambiguously as a dot path")
        return ".".join(escape_path_part(part) for part in self.parts)

    def to_pointer(self) -> str:
        return to_json_pointer(self)


def parse_json_pointer(pointer: str) -> JsonPath:
    if pointer == "":
        return JsonPath(())
    if not pointer.startswith("/"):
        raise ValueError("JSON Pointer must be empty or start with '/'")
    return JsonPath(tuple(_unescape_pointer_part(part) for part in pointer.split("/")[1:]))


def to_json_pointer(path: JsonPath) -> str:
    if not path.parts:
        return ""
    return "/" + "/".join(_escape_pointer_part(part) for part in path.parts)


def _escape_pointer_part(part: str) -> str:
    return part.replace("~", "~0").replace("/", "~1")


def _unescape_pointer_part(part: str) -> str:
    result: list[str] = []
    index = 0
    while index < len(part):
        char = part[index]
        if char != "~":
            result.append(char)
            index += 1
            continue
        if index + 1 >= len(part):
            raise ValueError("Invalid JSON Pointer escape")
        escape = part[index + 1]
        if escape == "0":
            result.append("~")
        elif escape == "1":
            result.append("/")
        else:
            raise ValueError("Invalid JSON Pointer escape")
        index += 2
    return "".join(result)


def split_path(path: str) -> list[str]:
    if not path:
        return []
    parts: list[str] = []
    current: list[str] = []
    escaping = False
    for char in path:
        if escaping:
            current.append(char)
            escaping = False
        elif char == "\\":
            escaping = True
        elif char == ".":
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    if escaping:
        current.append("\\")
    parts.append("".join(current))
    return parts


def escape_path_part(part: str) -> str:
    return part.replace("\\", "\\\\").replace(".", "\\.")


def join_path(parent: str, part: str) -> str:
    escaped = escape_path_part(part)
    return f"{parent}.{escaped}" if parent else escaped


def _key(container: Any, part: str):
    if isinstance(container, list):
        return _array_index(container, part)
    if isinstance(container, dict):
        return part
    raise TypeError("Cannot traverse scalar value")


def _array_index(container: list, part: str) -> int:
    if not ARRAY_INDEX_PATTERN.fullmatch(part):
        raise TypeError(f"Invalid array index: {part!r}")
    index = int(part)
    if index >= len(container):
        raise IndexError(index)
    return index


def _insert_index(container: list, part: str) -> int:
    if part == "-":
        return len(container)
    if not ARRAY_INDEX_PATTERN.fullmatch(part):
        raise TypeError(f"Invalid array insert index: {part!r}")
    index = int(part)
    if index > len(container):
        raise IndexError(index)
    return index


def coerce_path(path: str | JsonPath, *, path_format: str = "dot") -> JsonPath:
    if isinstance(path, JsonPath):
        return path
    if path_format == "dot":
        return JsonPath.from_dot(path)
    if path_format == "pointer":
        return JsonPath.from_pointer(path)
    raise ValueError(f"Unsupported path format: {path_format}")


def get_path(
    data: Any,
    path: str | JsonPath,
    *,
    decode_embedded: bool = False,
    path_format: str = "dot",
) -> PathMatch:
    current = data
    decoded = 0
    for part in coerce_path(path, path_format=path_format).parts:
        decoded_value = decode_if_embedded_json(current, enabled=decode_embedded)
        if decoded_value.was_embedded_json:
            decoded += 1
            current = decoded_value.value

        key = _key(current, part)
        current = current[key]
    decoded_value = decode_if_embedded_json(current, enabled=decode_embedded)
    if decoded_value.was_embedded_json:
        decoded += 1
        current = decoded_value.value
    return PathMatch(current, decoded)


def set_path(
    data: Any,
    path: str | JsonPath,
    value: Any,
    *,
    decode_embedded: bool = False,
    path_format: str = "dot",
) -> Any:
    parts = coerce_path(path, path_format=path_format).parts
    if not parts:
        raise ValueError("Cannot replace document root through set_path")

    def set_inner(container: Any, remaining: list[str]) -> Any:
        decoded = decode_if_embedded_json(container, enabled=decode_embedded)
        working = decoded.value
        part = remaining[0]
        key = _key(working, part)

        if len(remaining) == 1:
            if isinstance(working, dict) and key not in working:
                raise KeyError(key)
            existing = working[key]
            decoded_existing = decode_if_embedded_json(existing, enabled=decode_embedded)
            working[key] = encode_if_needed(value, decoded_existing.was_embedded_json)
        else:
            child = working[key]
            working[key] = set_inner(child, remaining[1:])

        return encode_if_needed(working, decoded.was_embedded_json)

    return set_inner(data, parts)


def add_path(
    data: Any,
    path: str | JsonPath,
    value: Any,
    force: bool = False,
    *,
    decode_embedded: bool = False,
    path_format: str = "dot",
) -> Any:
    parts = coerce_path(path, path_format=path_format).parts
    if not parts:
        raise ValueError("Path is required")

    def add_inner(container: Any, remaining: list[str]) -> Any:
        decoded = decode_if_embedded_json(container, enabled=decode_embedded)
        working = decoded.value
        part = remaining[0]

        if len(remaining) == 1:
            if isinstance(working, list):
                working.insert(_insert_index(working, part), value)
            elif isinstance(working, dict):
                if part in working and not force:
                    raise KeyError(f"Path already exists: {part}")
                working[part] = value
            else:
                raise TypeError("Parent is not an object or array")
        else:
            key = _key(working, part)
            working[key] = add_inner(working[key], remaining[1:])

        return encode_if_needed(working, decoded.was_embedded_json)

    return add_inner(data, parts)


def delete_path(
    data: Any,
    path: str | JsonPath,
    *,
    decode_embedded: bool = False,
    path_format: str = "dot",
) -> Any:
    parts = coerce_path(path, path_format=path_format).parts
    if not parts:
        raise ValueError("Cannot delete document root")

    def delete_inner(container: Any, remaining: list[str]) -> Any:
        decoded = decode_if_embedded_json(container, enabled=decode_embedded)
        working = decoded.value
        part = remaining[0]

        if len(remaining) == 1:
            if isinstance(working, list):
                del working[_array_index(working, part)]
            elif isinstance(working, dict):
                del working[part]
            else:
                raise TypeError("Parent is not an object or array")
        else:
            key = _key(working, part)
            working[key] = delete_inner(working[key], remaining[1:])

        return encode_if_needed(working, decoded.was_embedded_json)

    return delete_inner(data, parts)


def iter_paths(
    data: Any,
    path: str | JsonPath | None = None,
    max_depth: int | None = None,
    *,
    decode_embedded: bool = False,
) -> Iterator[tuple[JsonPath, Any]]:
    if path is None:
        path = JsonPath(())
    elif isinstance(path, str):
        path = JsonPath.from_dot(path) if path else JsonPath(())

    stack: list[tuple[Any, JsonPath, int]] = [(data, path, 0)]

    while stack:
        value, current_path, depth = stack.pop()
        decoded = decode_if_embedded_json(value, enabled=decode_embedded)
        current = decoded.value
        if current_path.parts:
            yield current_path, current
        if max_depth is not None and depth >= max_depth:
            continue
        if isinstance(current, dict):
            for key in reversed(current):
                child_path = JsonPath(current_path.parts + (str(key),))
                stack.append((current[key], child_path, depth + 1))
        elif isinstance(current, list):
            for index in range(len(current) - 1, -1, -1):
                child_path = JsonPath(current_path.parts + (str(index),))
                stack.append((current[index], child_path, depth + 1))


def path_completions(
    data: Any,
    path: str = "",
    *,
    limit: int = 1000,
    decode_embedded: bool = False,
    include_append: bool = False,
) -> list[str]:
    if limit < 0:
        raise ValueError("Completion limit must not be negative")
    if limit == 0:
        return []

    parts = split_path(path)
    parent = JsonPath(tuple(parts[:-1])) if parts else JsonPath(())
    fragment = parts[-1] if parts else ""

    try:
        container = get_path(data, parent, decode_embedded=decode_embedded).value
    except (KeyError, IndexError, TypeError, ValueError):
        return []

    if isinstance(container, dict):
        children = (str(key) for key in container)
    elif isinstance(container, list):
        indexes = [str(index) for index in range(len(container))]
        if include_append:
            indexes.append("-")
        children = iter(indexes)
    else:
        return []

    completions: list[str] = []
    for child in children:
        if not child.lower().startswith(fragment.lower()):
            continue
        candidate = JsonPath(parent.parts + (child,))
        try:
            completions.append(candidate.to_dot())
        except ValueError:
            continue
        if len(completions) >= limit:
            break
    return completions


def render_path(path: JsonPath, path_format: PathFormat) -> str:
    if path_format == "pointer":
        return path.to_pointer()
    if path_format != "dot":
        raise ValueError(f"Unsupported path format: {path_format}")
    try:
        return path.to_dot()
    except ValueError as exc:
        raise ValueError(
            "Path cannot be represented as a dot path; use --path-format pointer"
        ) from exc


def format_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)
