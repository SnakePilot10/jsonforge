import json
import math
from typing import Any, TextIO


def reject_json_constant(value: str) -> None:
    raise ValueError(f"JSON does not support {value}")


def validate_json_number(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("JSON does not support NaN or Infinity")
    return value


def loads(text: str) -> Any:
    return json.loads(text, parse_constant=reject_json_constant)


def load(handle: TextIO) -> Any:
    return json.load(handle, parse_constant=reject_json_constant)


def dumps(data: Any, **kwargs) -> str:
    return json.dumps(data, allow_nan=False, **kwargs)


def dump(data: Any, handle: TextIO, **kwargs) -> None:
    json.dump(data, handle, allow_nan=False, **kwargs)
