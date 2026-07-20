from typing import Literal

from .strict_json import loads, validate_json_number

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

    if text and text[0] in '[{"':
        try:
            return loads(text)
        except ValueError:
            pass

    try:
        if any(ch in text for ch in ".eE"):
            return validate_json_number(float(text))
        return int(text)
    except ValueError as exc:
        if "NaN or Infinity" in str(exc):
            raise
        return value


def parse_typed_value(value: str, value_type: ValueType = "auto"):
    if value_type == "auto":
        return smart_cast(value)
    if value_type == "string":
        return value
    if value_type == "int":
        return int(value)
    if value_type == "float":
        return validate_json_number(float(value))
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
        return loads(value)
    raise ValueError(f"Unsupported value type: {value_type}")


def type_for_existing_value(value) -> ValueType:
    if isinstance(value, bool):
        return "bool"
    if value is None:
        return "null"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, (dict, list)):
        return "json"
    return "string"


def parse_preserving_type(value: str, current_value):
    value_type = type_for_existing_value(current_value)
    parsed = parse_typed_value(value, value_type)

    if current_value is None and value.strip().lower() != "null":
        raise ValueError("Preserving null requires the value 'null'")
    if isinstance(current_value, dict) and not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object")
    if isinstance(current_value, list) and not isinstance(parsed, list):
        raise ValueError("Expected a JSON array")
    return parsed
