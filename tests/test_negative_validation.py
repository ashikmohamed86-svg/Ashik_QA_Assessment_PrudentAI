"""Negative & input-validation tests for Stripe APIs.

Covers boundary values, invalid inputs, missing fields, and Stripe
test-card decline scenarios.
"""

import pytest

from schemas.customer_schema import STRIPE_ERROR_SCHEMA
from utils.validators import validate_schema
from utils.test_data import (
    VALID_PAYMENT_INTENT,
    PAYMENT_INTENT_MANUAL_CAPTURE,
    CARD_VISA_SUCCESS,
    CARD_DECLINED,
    CARD_INSUFFICIENT_FUNDS,
    CARD_EXPIRED,
    CARD_INCORRECT_CVC,
)


# ─────────────────────────────────────────────────────────────────────
#  Customer – Negative Tests
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.negative
@pytest.mark.customers
class TestCustomerNegative:

    def test_create_customer_invalid_email_accepted(
        self, customers_api, created_customer_ids
    ):
        """Stripe does not validate email format server-side; it stores as-is."""
        resp = customers_api.create(email="not-an-email")
        body = resp.json()

        assert resp.status_code == 200
        assert body["email"] == "not-an-email"
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

    def test_create_customer_extremely_long_name(
        self, customers_api, created_customer_ids
    ):
        long_name = "A" * 5000
        resp = customers_api.create(name=long_name)
        body = resp.json()

        assert resp.status_code == 200
        assert body["name"] == long_name
        created_customer_ids.append(body["id"])

    def test_retrieve_deleted_customer(
        self, customers_api
    ):
        create_resp = customers_api.create(email="tobedeleted@test.com")
        cid = create_resp.json()["id"]
        customers_api.delete_customer(cid)

        resp = customers_api.retrieve(cid)
        body = resp.json()
        assert body.get("deleted") is True


# ─────────────────────────────────────────────────────────────────────
#  PaymentIntent – Invalid Input Tests
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.negative
@pytest.mark.payment_intents
class TestPaymentIntentInvalidInput:

    def test_invalid_currency_code(self, payments_api):
        resp = payments_api.create(
            amount=1000, currency="zzz", **{"payment_method_types[]": "card"}
        )
        assert resp.status_code == 400
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)

    def test_missing_amount(self, payments_api):
        resp = payments_api.create(
            currency="usd", **{"payment_method_types[]": "card"}
        )
        assert resp.status_code == 400

    def test_negative_amount(self, payments_api):
        resp = payments_api.create(
            amount=-100, currency="usd", **{"payment_method_types[]": "card"}
        )
        assert resp.status_code == 400

    def test_zero_amount_rejected(self, payments_api):
        """Stripe rejects amount=0 for most currencies."""
        resp = payments_api.create(
            amount=0, currency="usd", **{"payment_method_types[]": "card"}
        )
        assert resp.status_code == 400

    def test_string_amount(self, payments_api):
        resp = payments_api.create(
            amount="not_a_number",
            currency="usd",
            **{"payment_method_types[]": "card"},
        )
        assert resp.status_code == 400

    def test_missing_currency(self, payments_api):
        resp = payments_api.create(
            amount=1000, **{"payment_method_types[]": "card"}
        )
        assert resp.status_code == 400

    @pytest.mark.parametrize(
        "currency",
        ["USD", "Us", "u", "us", "usdx", "12"],
        ids=[
            "uppercase",
            "mixed-case",
            "single-char",
            "two-chars",
            "four-chars",
            "numeric",
        ],
    )
    def test_various_invalid_currencies(self, payments_api, currency):
        resp = payments_api.create(
            amount=1000, currency=currency, **{"payment_method_types[]": "card"}
        )
        # Stripe normalises uppercase to lowercase, so "USD" may succeed.
        # We verify the response is either 200 with lowercased currency or 400.
        if resp.status_code == 200:
            assert resp.json()["currency"] == currency.lower()
        else:
            assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────
#  PaymentIntent – Capture Validation
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.negative
@pytest.mark.payment_intents
class TestCaptureValidation:

    def test_capture_before_confirm_fails(
        self, payments_api, created_payment_intent_ids
    ):
        pi = payments_api.create(**PAYMENT_INTENT_MANUAL_CAPTURE).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.capture(pi["id"])
        assert resp.status_code == 400

    def test_capture_amount_greater_than_authorized(
        self, payments_api, created_payment_intent_ids
    ):
        """Attempt to capture more than the authorized amount."""
        pi = payments_api.create(**PAYMENT_INTENT_MANUAL_CAPTURE).json()
        created_payment_intent_ids.append(pi["id"])

        payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)

        resp = payments_api.capture(
            pi["id"], amount_to_capture=pi["amount"] + 5000
        )
        assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────
#  Stripe Test Card Decline Scenarios
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.negative
@pytest.mark.payment_intents
class TestDeclineScenarios:

    def _create_and_confirm(self, payments_api, card, ids_list):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        ids_list.append(pi["id"])
        return payments_api.confirm(pi["id"], payment_method=card)

    def test_card_declined(
        self, payments_api, created_payment_intent_ids
    ):
        resp = self._create_and_confirm(
            payments_api, CARD_DECLINED, created_payment_intent_ids
        )
        body = resp.json()
        assert resp.status_code == 402
        assert body["error"]["code"] == "card_declined"

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

    def test_expired_card(
        self, payments_api, created_payment_intent_ids
    ):
        resp = self._create_and_confirm(
            payments_api, CARD_EXPIRED, created_payment_intent_ids
        )
        body = resp.json()
        assert resp.status_code == 402
        assert body["error"]["code"] == "card_declined"
        assert body["error"]["decline_code"] == "expired_card"

    def test_incorrect_cvc(
        self, payments_api, created_payment_intent_ids
    ):
        resp = self._create_and_confirm(
            payments_api, CARD_INCORRECT_CVC, created_payment_intent_ids
        )
        body = resp.json()
        assert resp.status_code == 402
        assert body["error"]["code"] == "card_declined"
        assert body["error"]["decline_code"] == "incorrect_cvc"

    def test_confirm_without_payment_method(
        self, payments_api, created_payment_intent_ids
    ):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.confirm(pi["id"])
        assert resp.status_code == 400
        body = resp.json()
        assert "error" in body
