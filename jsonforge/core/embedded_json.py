import json
from dataclasses import dataclass
from typing import Any


@dataclass
class DecodedValue:
    value: Any
    was_embedded_json: bool = False


def decode_if_embedded_json(value: Any) -> DecodedValue:
    """Decode strings that contain JSON arrays or objects."""
    if not isinstance(value, str):
        return DecodedValue(value, False)

    stripped = value.strip()
    if not stripped or stripped[0] not in "[{":
        return DecodedValue(value, False)

    try:
        decoded = json.loads(stripped)
    except json.JSONDecodeError:
        return DecodedValue(value, False)
    return DecodedValue(decoded, True)


def encode_if_needed(value: Any, was_embedded_json: bool) -> Any:
    if was_embedded_json:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value
