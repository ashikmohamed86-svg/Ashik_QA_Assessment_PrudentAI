"""Tests for Stripe PaymentIntents API – create, confirm, capture, fetch."""

import allure
import pytest

from schemas.payment_intent_schema import (
    PAYMENT_INTENT_SCHEMA,
    PAYMENT_INTENT_CONFIRM_SCHEMA,
)
from utils.validators import validate_schema, is_valid_iso_currency, assert_response_time
from utils.test_data import (
    VALID_PAYMENT_INTENT,
    PAYMENT_INTENT_WITH_RECEIPT,
    PAYMENT_INTENT_MANUAL_CAPTURE,
    CARD_VISA_SUCCESS,
)


# ─────────────────────────────────────────────────────────────────────
#  Create PaymentIntent
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("Create PaymentIntent")
@pytest.mark.smoke
@pytest.mark.payment_intents
class TestCreatePaymentIntent:

    def test_create_basic_payment_intent(
        self, payments_api, created_payment_intent_ids
    ):
        resp = payments_api.create(**VALID_PAYMENT_INTENT)
        body = resp.json()

        assert resp.status_code == 200
        assert_response_time(resp)
        assert body["id"].startswith("pi_")
        assert body["amount"] == VALID_PAYMENT_INTENT["amount"]
        assert body["status"] in (
            "requires_payment_method",
            "requires_confirmation",
        )
        validate_schema(body, PAYMENT_INTENT_SCHEMA)

        created_payment_intent_ids.append(body["id"])

    def test_amount_stored_in_minor_units(
        self, payments_api, created_payment_intent_ids
    ):
        resp = payments_api.create(**VALID_PAYMENT_INTENT)
        body = resp.json()

        assert isinstance(body["amount"], int)
        assert body["amount"] == 2000  # $20.00 in cents

        created_payment_intent_ids.append(body["id"])

    def test_currency_is_iso3(
        self, payments_api, created_payment_intent_ids
    ):
        resp = payments_api.create(**VALID_PAYMENT_INTENT)
        body = resp.json()

        assert is_valid_iso_currency(body["currency"])

        created_payment_intent_ids.append(body["id"])

    def test_create_with_receipt_email(
        self, payments_api, created_payment_intent_ids
    ):
        resp = payments_api.create(**PAYMENT_INTENT_WITH_RECEIPT)
        body = resp.json()

        assert resp.status_code == 200
        assert body["receipt_email"] == "receipt@example.com"
        validate_schema(body, PAYMENT_INTENT_SCHEMA)

        created_payment_intent_ids.append(body["id"])

    def test_create_manual_capture(
        self, payments_api, created_payment_intent_ids
    ):
        resp = payments_api.create(**PAYMENT_INTENT_MANUAL_CAPTURE)
        body = resp.json()

        assert resp.status_code == 200
        assert body["capture_method"] == "manual"

        created_payment_intent_ids.append(body["id"])

    def test_response_schema(
        self, payments_api, created_payment_intent_ids
    ):
        resp = payments_api.create(**VALID_PAYMENT_INTENT)
        body = resp.json()

        validate_schema(body, PAYMENT_INTENT_SCHEMA)
        created_payment_intent_ids.append(body["id"])


# ─────────────────────────────────────────────────────────────────────
#  Confirm PaymentIntent
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("Confirm PaymentIntent")
@pytest.mark.payment_intents
class TestConfirmPaymentIntent:

    def test_confirm_with_valid_card(
        self, payments_api, created_payment_intent_ids
    ):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.confirm(
            pi["id"], payment_method=CARD_VISA_SUCCESS
        )
        body = resp.json()

        assert resp.status_code == 200
        assert body["status"] == "succeeded"
        validate_schema(body, PAYMENT_INTENT_CONFIRM_SCHEMA)

    def test_confirm_without_payment_method(
        self, payments_api, created_payment_intent_ids
    ):
        """Confirming without attaching a payment method should error."""
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.confirm(pi["id"])
        assert resp.status_code == 400

    def test_confirm_already_succeeded(
        self, payments_api, created_payment_intent_ids
    ):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)
        resp = payments_api.confirm(
            pi["id"], payment_method=CARD_VISA_SUCCESS
        )

        assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────
#  Capture PaymentIntent (manual capture flow)
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("Capture PaymentIntent")
@pytest.mark.payment_intents
class TestCapturePaymentIntent:

    def _create_and_confirm_manual(self, payments_api, ids_list):
        pi = payments_api.create(**PAYMENT_INTENT_MANUAL_CAPTURE).json()
        ids_list.append(pi["id"])
        payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)
        return pi["id"]

    def test_capture_after_confirm(
        self, payments_api, created_payment_intent_ids
    ):
        pi_id = self._create_and_confirm_manual(
            payments_api, created_payment_intent_ids
        )
        resp = payments_api.capture(pi_id)
        body = resp.json()

        assert resp.status_code == 200
        assert body["status"] == "succeeded"
        assert body["amount_received"] == PAYMENT_INTENT_MANUAL_CAPTURE["amount"]

    def test_capture_before_confirm_fails(
        self, payments_api, created_payment_intent_ids
    ):
        pi = payments_api.create(**PAYMENT_INTENT_MANUAL_CAPTURE).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.capture(pi["id"])
        assert resp.status_code == 400

    def test_double_capture_fails(
        self, payments_api, created_payment_intent_ids
    ):
        pi_id = self._create_and_confirm_manual(
            payments_api, created_payment_intent_ids
        )
        payments_api.capture(pi_id)

        resp = payments_api.capture(pi_id)
        assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────
#  Fetch PaymentIntent Details
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("Fetch PaymentIntent")
@pytest.mark.payment_intents
class TestFetchPaymentIntent:

    def test_fetch_existing_intent(
        self, payments_api, created_payment_intent_ids
    ):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.retrieve(pi["id"])
        body = resp.json()

        assert resp.status_code == 200
        assert body["id"] == pi["id"]
        validate_schema(body, PAYMENT_INTENT_SCHEMA)

    def test_fetch_non_existing_intent(self, payments_api):
        resp = payments_api.retrieve("pi_nonexistent000000000")
        assert resp.status_code == 404

    def test_status_transitions(
        self, payments_api, created_payment_intent_ids
    ):
        """Verify status flow: requires_payment_method -> succeeded."""
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])
        assert pi["status"] == "requires_payment_method"

        payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)
        fetched = payments_api.retrieve(pi["id"]).json()
        assert fetched["status"] == "succeeded"

    def test_manual_capture_status_transitions(
        self, payments_api, created_payment_intent_ids
    ):
        """Verify: requires_payment_method -> requires_capture -> succeeded."""
        pi = payments_api.create(**PAYMENT_INTENT_MANUAL_CAPTURE).json()
        created_payment_intent_ids.append(pi["id"])
        assert pi["status"] == "requires_payment_method"

        payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)
        confirmed = payments_api.retrieve(pi["id"]).json()
        assert confirmed["status"] == "requires_capture"

        payments_api.capture(pi["id"])
        captured = payments_api.retrieve(pi["id"]).json()
        assert captured["status"] == "succeeded"
        assert captured["amount_received"] == PAYMENT_INTENT_MANUAL_CAPTURE["amount"]

    def test_verify_timestamps(
        self, payments_api, created_payment_intent_ids
    ):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        assert isinstance(pi["created"], int)
        assert pi["created"] > 0


# ─────────────────────────────────────────────────────────────────────
#  End-to-End Payment Flow
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("End-to-End Payment Flow")
@pytest.mark.e2e
@pytest.mark.payment_intents
class TestEndToEndPaymentFlow:

    def test_full_automatic_capture_flow(
        self,
        customers_api,
        payments_api,
        created_customer_ids,
        created_payment_intent_ids,
    ):
        """Customer creation -> PaymentIntent -> Confirm -> Verify."""
        cust = customers_api.create(
            name="E2E User", email="e2e@example.com"
        ).json()
        created_customer_ids.append(cust["id"])

        pi = payments_api.create(
            amount=7500,
            currency="usd",
            customer=cust["id"],
            **{"payment_method_types[]": "card"},
        ).json()
        created_payment_intent_ids.append(pi["id"])
        assert pi["status"] == "requires_payment_method"

        confirmed = payments_api.confirm(
            pi["id"], payment_method=CARD_VISA_SUCCESS
        ).json()
        assert confirmed["status"] == "succeeded"

        fetched = payments_api.retrieve(pi["id"]).json()
        assert fetched["status"] == "succeeded"
        assert fetched["amount"] == 7500
        assert fetched["customer"] == cust["id"]

    def test_full_manual_capture_flow(
        self,
        customers_api,
        payments_api,
        created_customer_ids,
        created_payment_intent_ids,
    ):
        """Customer -> PaymentIntent(manual) -> Confirm -> Capture -> Verify."""
        cust = customers_api.create(
            name="E2E Manual", email="e2e_manual@example.com"
        ).json()
        created_customer_ids.append(cust["id"])

        pi = payments_api.create(
            amount=10000,
            currency="usd",
            customer=cust["id"],
            capture_method="manual",
            **{"payment_method_types[]": "card"},
        ).json()
        created_payment_intent_ids.append(pi["id"])

        payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)

        confirmed = payments_api.retrieve(pi["id"]).json()
        assert confirmed["status"] == "requires_capture"

        payments_api.capture(pi["id"])
        captured = payments_api.retrieve(pi["id"]).json()
        assert captured["status"] == "succeeded"
        assert captured["amount_received"] == 10000
