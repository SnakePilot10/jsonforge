from typing import Any, Iterator

from .embedded_json import decode_if_embedded_json


def search(data: Any, query: str, path: str = "") -> Iterator[tuple[str, Any]]:
    needle = query.lower()
    decoded = decode_if_embedded_json(data)
    current = decoded.value

    if path and needle in path.lower():
        yield path, current

    if isinstance(current, dict):
        for key, value in current.items():
            child_path = f"{path}.{key}" if path else str(key)
            if needle in str(key).lower():
                yield child_path, value
            yield from search(value, query, child_path)
    elif isinstance(current, list):
        for index, value in enumerate(current):
            child_path = f"{path}.{index}" if path else str(index)
            yield from search(value, query, child_path)
    else:
        if needle in str(current).lower():
            yield path, current
