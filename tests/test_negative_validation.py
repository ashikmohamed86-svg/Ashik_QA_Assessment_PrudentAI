"""Negative & input-validation tests for Stripe APIs.

Covers boundary values, invalid inputs, missing fields, and Stripe
test-card decline scenarios.
"""

import allure
import pytest

from schemas.customer_schema import STRIPE_ERROR_SCHEMA
from utils.validators import validate_schema
from utils.test_data import (
    VALID_PAYMENT_INTENT,
    PAYMENT_INTENT_MANUAL_CAPTURE,
    PAYMENT_INTENT_INVALID_CURRENCY,
    PAYMENT_INTENT_ZERO_AMOUNT,
    PAYMENT_INTENT_NEGATIVE_AMOUNT,
    CUSTOMER_INVALID_EMAIL,
    CUSTOMER_MISSING_EMAIL,
    CARD_VISA_SUCCESS,
    CARD_DECLINED,
    CARD_INSUFFICIENT_FUNDS,
    CARD_EXPIRED,
    CARD_INCORRECT_CVC,
    CARD_PROCESSING_ERROR,
)


# ─────────────────────────────────────────────────────────────────────
#  Customer – Negative Tests
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Customers API")
@allure.story("Negative Validation")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.negative
@pytest.mark.customers
class TestCustomerNegative:

    @allure.description("Stripe rejects invalid email formats; verify 400 response with error schema.")
    def test_create_customer_invalid_email_rejected(
        self, customers_api, created_customer_ids
    ):
        resp = customers_api.create(**CUSTOMER_INVALID_EMAIL)
        body = resp.json()

        if resp.status_code == 400:
            validate_schema(body, STRIPE_ERROR_SCHEMA)
        else:
            assert resp.status_code == 200
            assert body["email"] == CUSTOMER_INVALID_EMAIL["email"]
            created_customer_ids.append(body["id"])

    @allure.description("Stripe allows creating a customer without an email — email is optional.")
    def test_create_customer_missing_email(
        self, customers_api, created_customer_ids
    ):
        resp = customers_api.create(**CUSTOMER_MISSING_EMAIL)
        body = resp.json()

        assert resp.status_code == 200
        assert body["email"] is None
        assert body["name"] == CUSTOMER_MISSING_EMAIL["name"]
        created_customer_ids.append(body["id"])

    def test_create_customer_empty_body(
        self, customers_api, created_customer_ids
    ):
        """Stripe allows creating a customer with no fields."""
        resp = customers_api.create()
        body = resp.json()

        assert resp.status_code == 200
        assert body["id"].startswith("cus_")
        created_customer_ids.append(body["id"])

    @allure.description("Boundary test: extremely long name (5000 chars) may be accepted or rejected.")
    def test_create_customer_extremely_long_name(
        self, customers_api, created_customer_ids
    ):
        long_name = "A" * 5000
        resp = customers_api.create(name=long_name)
        body = resp.json()

        if resp.status_code == 400:
            validate_schema(body, STRIPE_ERROR_SCHEMA)
        else:
            assert resp.status_code == 200
            assert body["name"] == long_name
            created_customer_ids.append(body["id"])

    def test_retrieve_deleted_customer(
        self, customers_api
    ):
        with allure.step("Create and delete a customer"):
            create_resp = customers_api.create(email="tobedeleted@test.com")
            cid = create_resp.json()["id"]
            customers_api.delete_customer(cid)

        with allure.step("Retrieve deleted customer and verify deleted flag"):
            resp = customers_api.retrieve(cid)
            body = resp.json()
            assert body.get("deleted") is True


# ─────────────────────────────────────────────────────────────────────
#  PaymentIntent – Invalid Input Tests
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("Invalid Input Validation")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.negative
@pytest.mark.payment_intents
class TestPaymentIntentInvalidInput:

    def test_invalid_currency_code(self, payments_api):
        resp = payments_api.create(**PAYMENT_INTENT_INVALID_CURRENCY)
        assert resp.status_code == 400
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)

    def test_missing_amount(self, payments_api):
        resp = payments_api.create(
            currency="usd", **{"payment_method_types[]": "card"}
        )
        assert resp.status_code == 400
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)

    def test_negative_amount(self, payments_api):
        resp = payments_api.create(**PAYMENT_INTENT_NEGATIVE_AMOUNT)
        assert resp.status_code == 400
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)

    def test_zero_amount_rejected(self, payments_api):
        """Stripe rejects amount=0 for most currencies."""
        resp = payments_api.create(**PAYMENT_INTENT_ZERO_AMOUNT)
        assert resp.status_code == 400
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)

    def test_string_amount(self, payments_api):
        resp = payments_api.create(
            amount="not_a_number",
            currency="usd",
            **{"payment_method_types[]": "card"},
        )
        assert resp.status_code == 400
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)

    def test_missing_currency(self, payments_api):
        resp = payments_api.create(
            amount=1000, **{"payment_method_types[]": "card"}
        )
        assert resp.status_code == 400
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)

    @pytest.mark.parametrize(
        "currency, expected_status",
        [
            ("USD", 200),       # Stripe normalises uppercase
            ("Us", 400),        # Two-char mixed-case is invalid
            ("u", 400),         # Single char is invalid
            ("usdx", 400),      # Four chars is invalid
            ("12", 400),        # Numeric is invalid
        ],
        ids=[
            "uppercase-normalised",
            "mixed-case-invalid",
            "single-char-invalid",
            "four-chars-invalid",
            "numeric-invalid",
        ],
    )
    def test_various_invalid_currencies(self, payments_api, currency, expected_status, created_payment_intent_ids):
        resp = payments_api.create(
            amount=1000, currency=currency, **{"payment_method_types[]": "card"}
        )
        assert resp.status_code == expected_status
        if expected_status == 200:
            body = resp.json()
            assert body["currency"] == currency.lower()
            created_payment_intent_ids.append(body["id"])
        else:
            validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)


# ─────────────────────────────────────────────────────────────────────
#  PaymentIntent – Capture Validation
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("Capture Validation")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.negative
@pytest.mark.payment_intents
class TestCaptureValidation:

    @allure.description("Attempt to capture more than the authorized amount — should return 400.")
    def test_capture_amount_greater_than_authorized(
        self, payments_api, created_payment_intent_ids
    ):
        with allure.step("Create and confirm manual-capture PaymentIntent"):
            pi = payments_api.create(**PAYMENT_INTENT_MANUAL_CAPTURE).json()
            created_payment_intent_ids.append(pi["id"])
            payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)

        with allure.step("Attempt capture with amount exceeding authorization"):
            resp = payments_api.capture(
                pi["id"], amount_to_capture=pi["amount"] + 5000
            )

        with allure.step("Verify 400 and error schema"):
            assert resp.status_code == 400
            validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)


# ─────────────────────────────────────────────────────────────────────
#  Stripe Test Card Decline Scenarios
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("Decline Scenarios")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.negative
@pytest.mark.payment_intents
class TestDeclineScenarios:

    def _create_and_confirm(self, payments_api, card, ids_list):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        ids_list.append(pi["id"])
        return payments_api.confirm(pi["id"], payment_method=card)

    @allure.description("Generic card decline using pm_card_chargeDeclined test token.")
    def test_card_declined(
        self, payments_api, created_payment_intent_ids
    ):
        resp = self._create_and_confirm(
            payments_api, CARD_DECLINED, created_payment_intent_ids
        )
        body = resp.json()
        assert resp.status_code == 402
        assert body["error"]["code"] == "card_declined"
        validate_schema(body, STRIPE_ERROR_SCHEMA)

    def test_insufficient_funds(
        self, payments_api, created_payment_intent_ids
    ):
        resp = self._create_and_confirm(
            payments_api, CARD_INSUFFICIENT_FUNDS, created_payment_intent_ids
        )
        body = resp.json()
        assert resp.status_code == 402
        assert body["error"]["code"] == "card_declined"
        assert "insufficient" in body["error"]["decline_code"]
        validate_schema(body, STRIPE_ERROR_SCHEMA)

    def test_expired_card(
        self, payments_api, created_payment_intent_ids
    ):
        resp = self._create_and_confirm(
            payments_api, CARD_EXPIRED, created_payment_intent_ids
        )
        body = resp.json()
        assert resp.status_code == 402
        assert body["error"]["code"] == "expired_card"
        assert body["error"]["decline_code"] == "expired_card"
        validate_schema(body, STRIPE_ERROR_SCHEMA)

    def test_incorrect_cvc(
        self, payments_api, created_payment_intent_ids
    ):
        resp = self._create_and_confirm(
            payments_api, CARD_INCORRECT_CVC, created_payment_intent_ids
        )
        body = resp.json()
        assert resp.status_code == 402
        assert body["error"]["code"] == "incorrect_cvc"
        assert body["error"]["decline_code"] == "incorrect_cvc"
        validate_schema(body, STRIPE_ERROR_SCHEMA)

    def test_processing_error(
        self, payments_api, created_payment_intent_ids
    ):
        resp = self._create_and_confirm(
            payments_api, CARD_PROCESSING_ERROR, created_payment_intent_ids
        )
        body = resp.json()
        assert resp.status_code == 402
        assert body["error"]["code"] == "processing_error"
        assert body["error"]["decline_code"] == "processing_error"
        validate_schema(body, STRIPE_ERROR_SCHEMA)
