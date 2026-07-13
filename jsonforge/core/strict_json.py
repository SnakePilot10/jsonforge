import json
import math
from typing import Any, TextIO


def reject_json_constant(value: str) -> None:
    raise ValueError(f"JSON does not support {value}")


def validate_json_number(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("JSON does not support NaN or Infinity")
    return value


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate key "{key}"')
        result[key] = value
    return result


def loads(text: str, *, allow_duplicate_keys: bool = False) -> Any:
    object_pairs_hook = None if allow_duplicate_keys else reject_duplicate_keys
    return json.loads(
        text,
        parse_constant=reject_json_constant,
        object_pairs_hook=object_pairs_hook,
    )


def load(handle: TextIO, *, allow_duplicate_keys: bool = False) -> Any:
    object_pairs_hook = None if allow_duplicate_keys else reject_duplicate_keys
    return json.load(
        handle,
        parse_constant=reject_json_constant,
        object_pairs_hook=object_pairs_hook,
    )


def dumps(data: Any, **kwargs) -> str:
    return json.dumps(data, allow_nan=False, **kwargs)


def dump(data: Any, handle: TextIO, **kwargs) -> None:
    json.dump(data, handle, allow_nan=False, **kwargs)
