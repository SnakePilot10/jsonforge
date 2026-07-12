import json
from typing import Literal


ValueType = Literal["auto", "string", "int", "float", "bool", "null", "json"]


def smart_cast(value: str):
    """Convert prompt input into a JSON-like Python value when obvious."""
    text = value.strip()
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None

    if text and text[0] in "[{\"":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    try:
        if any(ch in text for ch in ".eE"):
            return float(text)
        return int(text)
    except ValueError:
        return value


def parse_typed_value(value: str, value_type: ValueType = "auto"):
    if value_type == "auto":
        return smart_cast(value)
    if value_type == "string":
        return value
    if value_type == "int":
        return int(value)
    if value_type == "float":
        return float(value)
    if value_type == "bool":
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
        raise ValueError("Boolean values must be true/false, yes/no, or 1/0")
    if value_type == "null":
        return None
    if value_type == "json":
        return json.loads(value)
    raise ValueError(f"Unsupported value type: {value_type}")
