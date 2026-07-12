import json


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
