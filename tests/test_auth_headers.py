"""Cross-cutting tests: Auth, Headers, and Encoding validation.

These tests verify authentication enforcement, header handling,
and content-type behavior for the Stripe API.
"""

import allure
import pytest
import requests

from config.settings import Settings
from schemas.customer_schema import STRIPE_ERROR_SCHEMA
from utils.validators import validate_schema


@allure.feature("Cross-Cutting")
@allure.story("Authentication")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.negative
class TestAuthentication:

    @allure.description(
        "AUTH-NEG-01: Calling the API without an Authorization header should return 401."
    )
    def test_missing_authorization_header(self):
        resp = requests.get(
            f"{Settings.BASE_URL}/customers",
            timeout=Settings.REQUEST_TIMEOUT,
        )
        body = resp.json()

        assert resp.status_code == 401
        validate_schema(body, STRIPE_ERROR_SCHEMA)
        assert body["error"]["type"] == "invalid_request_error"

    @allure.description(
        "AUTH-NEG-02: Using an invalid API key should return 401."
    )
    def test_invalid_api_key(self):
        resp = requests.get(
            f"{Settings.BASE_URL}/customers",
            headers={"Authorization": "Bearer sk_test_INVALID_KEY_000"},
            timeout=Settings.REQUEST_TIMEOUT,
        )
        body = resp.json()

        assert resp.status_code == 401
        validate_schema(body, STRIPE_ERROR_SCHEMA)
        assert body["error"]["type"] == "invalid_request_error"


@allure.feature("Cross-Cutting")
@allure.story("Headers & Encoding")
@allure.severity(allure.severity_level.NORMAL)
class TestHeadersEncoding:

    @allure.description(
        "HDR-VAL-01: Stripe expects form-encoded requests. "
        "Sending JSON body should fail or behave differently."
    )
    def test_json_body_instead_of_form_encoded(self):
        """Stripe API expects x-www-form-urlencoded; sending JSON body should fail."""
        resp = requests.post(
            f"{Settings.BASE_URL}/payment_intents",
            headers={
                "Authorization": f"Bearer {Settings.API_KEY}",
                "Content-Type": "application/json",
            },
            json={"amount": 1000, "currency": "usd"},
            timeout=Settings.REQUEST_TIMEOUT,
        )

        # Stripe should reject or misinterpret JSON-encoded body
        # (missing required params since it can't parse the JSON as form data)
        assert resp.status_code == 400
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)
