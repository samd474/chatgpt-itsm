"""Validate catalog form schemas and submitted answers on the server.

React evaluates show_when only to improve the form; this module re-evaluates
everything so the API can be called directly without bypassing the rules.
"""
from datetime import date

FIELD_TYPES = {"text", "textarea", "date", "boolean", "select"}
MAX_TEXT = 4000


def validate_schema(schema):
    errors = []
    if not isinstance(schema, list):
        return ["form_schema must be a list of fields"]
    keys = set()
    for index, field in enumerate(schema):
        if not isinstance(field, dict):
            errors.append(f"field {index} must be an object")
            continue
        key = field.get("key")
        if not key or not isinstance(key, str):
            errors.append(f"field {index} needs a key")
        elif key in keys:
            errors.append(f"duplicate key '{key}'")
        keys.add(key)
        if field.get("type") not in FIELD_TYPES:
            errors.append(f"field '{key}' has an unknown type")
        if field.get("type") == "select" and not field.get("options"):
            errors.append(f"select field '{key}' needs options")
    for field in schema:
        if isinstance(field, dict) and field.get("show_when"):
            if field["show_when"].get("field") not in keys:
                errors.append(f"field '{field.get('key')}' depends on an unknown field")
    return errors


def is_visible(field, answers):
    rule = field.get("show_when")
    if not rule:
        return True
    return answers.get(rule.get("field")) == rule.get("equals")


def validate_answers(schema, answers, *, reject_unknown=True):
    """Return (cleaned_answers, errors). Hidden fields are dropped."""
    if not isinstance(answers, dict):
        return {}, {"request_payload": "Answers must be an object."}
    errors = {}
    cleaned = {}
    known = {field["key"] for field in schema}
    if reject_unknown:
        for key in answers:
            if key not in known:
                errors[key] = "Unknown field."

    for field in schema:
        key = field["key"]
        if not is_visible(field, answers):
            continue
        value = answers.get(key)
        empty = value is None or value == ""
        if empty:
            if field.get("required") and field["type"] != "boolean":
                errors[key] = "This field is required."
            continue

        kind = field["type"]
        if kind == "boolean":
            if not isinstance(value, bool):
                errors[key] = "Must be true or false."
                continue
            if field.get("required") and value is not True:
                errors[key] = "This must be checked."
                continue
        elif kind in ("text", "textarea"):
            if not isinstance(value, str):
                errors[key] = "Must be text."
                continue
            value = value.strip()
            if len(value) > MAX_TEXT:
                errors[key] = f"Must be {MAX_TEXT} characters or fewer."
                continue
        elif kind == "date":
            try:
                value = date.fromisoformat(str(value)).isoformat()
            except ValueError:
                errors[key] = "Must be a date (YYYY-MM-DD)."
                continue
        elif kind == "select":
            if value not in field.get("options", []):
                errors[key] = "Choose one of the listed options."
                continue
        cleaned[key] = value
    return cleaned, errors
