import re

from jsonschema import validate, ValidationError


def validate_schema(instance: dict, schema: dict) -> None:
    """Raise AssertionError with a clear message when schema validation fails."""
    try:
        validate(instance=instance, schema=schema)
    except ValidationError as exc:
        raise AssertionError(f"Schema validation failed: {exc.message}") from exc


def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email))


def is_valid_phone(phone: str) -> bool:
    pattern = r"^\+?[1-9]\d{1,14}$"
    return bool(re.match(pattern, phone))


def is_valid_iso_currency(code: str) -> bool:
    return bool(re.match(r"^[a-z]{3}$", code))
