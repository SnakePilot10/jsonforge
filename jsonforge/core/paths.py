import json
from dataclasses import dataclass
from typing import Any

from .embedded_json import decode_if_embedded_json, encode_if_needed


@dataclass
class PathMatch:
    value: Any
    decoded_embedded_segments: int = 0


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
        if not part.isdigit():
            raise TypeError(f"Array index must be numeric, got '{part}'")
        return int(part)
    if isinstance(container, dict):
        return part
    raise TypeError("Cannot traverse scalar value")


def _insert_index(container: list, part: str) -> int:
    if part == "-":
        return len(container)
    if not part.isdigit():
        raise TypeError(f"Array insert index must be numeric or '-', got '{part}'")
    index = int(part)
    if index > len(container):
        raise IndexError(index)
    return index


def get_path(data: Any, path: str) -> PathMatch:
    current = data
    decoded = 0
    for part in split_path(path):
        decoded_value = decode_if_embedded_json(current)
        if decoded_value.was_embedded_json:
            decoded += 1
            current = decoded_value.value

        key = _key(current, part)
        current = current[key]
    decoded_value = decode_if_embedded_json(current)
    if decoded_value.was_embedded_json:
        decoded += 1
        current = decoded_value.value
    return PathMatch(current, decoded)


def set_path(data: Any, path: str, value: Any) -> Any:
    parts = split_path(path)
    if not parts:
        raise ValueError("Cannot replace document root through set_path")

    def set_inner(container: Any, remaining: list[str]) -> Any:
        decoded = decode_if_embedded_json(container)
        working = decoded.value
        part = remaining[0]
        key = _key(working, part)

        if len(remaining) == 1:
            if isinstance(working, dict) and key not in working:
                raise KeyError(key)
            working[key] = value
        else:
            child = working[key]
            working[key] = set_inner(child, remaining[1:])

        return encode_if_needed(working, decoded.was_embedded_json)

    return set_inner(data, parts)


def add_path(data: Any, path: str, value: Any, force: bool = False) -> Any:
    parts = split_path(path)
    if not parts:
        raise ValueError("Path is required")

    def add_inner(container: Any, remaining: list[str]) -> Any:
        decoded = decode_if_embedded_json(container)
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


def delete_path(data: Any, path: str) -> Any:
    parts = split_path(path)
    if not parts:
        raise ValueError("Cannot delete document root")

    def delete_inner(container: Any, remaining: list[str]) -> Any:
        decoded = decode_if_embedded_json(container)
        working = decoded.value
        part = remaining[0]

        if len(remaining) == 1:
            if isinstance(working, list):
                del working[int(part)]
            elif isinstance(working, dict):
                del working[part]
            else:
                raise TypeError("Parent is not an object or array")
        else:
            key = _key(working, part)
            working[key] = delete_inner(working[key], remaining[1:])

        return encode_if_needed(working, decoded.was_embedded_json)

    return delete_inner(data, parts)


def iter_paths(data: Any, path: str = "", max_depth: int | None = None) -> list[tuple[str, Any]]:
    results: list[tuple[str, Any]] = []

    def walk(value: Any, current_path: str, depth: int) -> None:
        decoded = decode_if_embedded_json(value)
        current = decoded.value
        if current_path:
            results.append((current_path, current))
        if max_depth is not None and depth >= max_depth:
            return
        if isinstance(current, dict):
            for key, child in current.items():
                child_path = join_path(current_path, str(key))
                walk(child, child_path, depth + 1)
        elif isinstance(current, list):
            for index, child in enumerate(current):
                child_path = f"{current_path}.{index}" if current_path else str(index)
                walk(child, child_path, depth + 1)

    walk(data, path, 0)
    return results


def path_completions(data: Any) -> list[str]:
    return [path for path, _ in iter_paths(data)]


def format_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)
