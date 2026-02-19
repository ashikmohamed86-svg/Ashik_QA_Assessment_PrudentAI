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


def assert_response_time(response, max_seconds: float = 5.0) -> None:
    """Assert that the response was received within the given time limit."""
    elapsed = response.elapsed.total_seconds()
    assert elapsed <= max_seconds, (
        f"Response took {elapsed:.2f}s, exceeding {max_seconds}s limit"
    )


def assert_response_headers(response) -> None:
    """Validate standard Stripe response headers for security and traceability."""
    assert "application/json" in response.headers.get("Content-Type", ""), (
        f"Expected JSON Content-Type, got: {response.headers.get('Content-Type')}"
    )
    assert response.headers.get("Request-Id"), (
        "Missing Request-Id header — required for Stripe request traceability"
    )
