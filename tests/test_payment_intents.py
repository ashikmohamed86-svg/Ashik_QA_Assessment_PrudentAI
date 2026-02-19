"""Tests for Stripe PaymentIntents API – create, confirm, capture, fetch."""

import uuid

import allure
import pytest

from schemas.payment_intent_schema import (
    PAYMENT_INTENT_SCHEMA,
    PAYMENT_INTENT_CONFIRM_SCHEMA,
)
from utils.validators import (
    validate_schema, is_valid_iso_currency,
    assert_response_time, assert_response_headers,
)
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
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.smoke
@pytest.mark.payment_intents
class TestCreatePaymentIntent:

    @allure.description("Verify basic PaymentIntent creation with amount, currency, and status validation.")
    def test_create_basic_payment_intent(
        self, payments_api, created_payment_intent_ids
    ):
        with allure.step("Send POST /payment_intents"):
            resp = payments_api.create(**VALID_PAYMENT_INTENT)
            body = resp.json()

        with allure.step("Validate status, ID prefix, amount, and initial status"):
            assert resp.status_code == 200
            assert_response_time(resp)
            assert_response_headers(resp)
            assert body["id"].startswith("pi_")
            assert body["amount"] == VALID_PAYMENT_INTENT["amount"]
            assert body["status"] in (
                "requires_payment_method",
                "requires_confirmation",
            )

        with allure.step("Validate response schema"):
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
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.payment_intents
class TestConfirmPaymentIntent:

    @allure.description("Confirm a PaymentIntent with a valid Visa test card and verify status becomes succeeded.")
    def test_confirm_with_valid_card(
        self, payments_api, created_payment_intent_ids
    ):
        with allure.step("Create PaymentIntent"):
            pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
            created_payment_intent_ids.append(pi["id"])

        with allure.step("Confirm with Visa test card"):
            resp = payments_api.confirm(
                pi["id"], payment_method=CARD_VISA_SUCCESS
            )
            body = resp.json()

        with allure.step("Verify status is succeeded"):
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
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.payment_intents
class TestCapturePaymentIntent:

    def _create_and_confirm_manual(self, payments_api, ids_list):
        pi = payments_api.create(**PAYMENT_INTENT_MANUAL_CAPTURE).json()
        ids_list.append(pi["id"])
        payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)
        return pi["id"]

    @allure.description("Verify that a manually-captured PaymentIntent succeeds and amount_received matches.")
    def test_capture_after_confirm(
        self, payments_api, created_payment_intent_ids
    ):
        with allure.step("Create and confirm manual-capture PaymentIntent"):
            pi_id = self._create_and_confirm_manual(
                payments_api, created_payment_intent_ids
            )

        with allure.step("Capture the PaymentIntent"):
            resp = payments_api.capture(pi_id)
            body = resp.json()

        with allure.step("Verify succeeded and amount_received"):
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
@allure.severity(allure.severity_level.NORMAL)
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
        assert_response_headers(resp)
        assert body["id"] == pi["id"]
        validate_schema(body, PAYMENT_INTENT_SCHEMA)

    def test_fetch_non_existing_intent(self, payments_api):
        resp = payments_api.retrieve("pi_nonexistent000000000")
        assert resp.status_code == 404

    @allure.description("Verify the full status transition: requires_payment_method -> succeeded.")
    def test_status_transitions(
        self, payments_api, created_payment_intent_ids
    ):
        with allure.step("Create PaymentIntent — status should be requires_payment_method"):
            pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
            created_payment_intent_ids.append(pi["id"])
            assert pi["status"] == "requires_payment_method"

        with allure.step("Confirm and verify status is succeeded"):
            payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)
            fetched = payments_api.retrieve(pi["id"]).json()
            assert fetched["status"] == "succeeded"

    @allure.description("Verify: requires_payment_method -> requires_capture -> succeeded for manual capture.")
    def test_manual_capture_status_transitions(
        self, payments_api, created_payment_intent_ids
    ):
        with allure.step("Create manual-capture PaymentIntent"):
            pi = payments_api.create(**PAYMENT_INTENT_MANUAL_CAPTURE).json()
            created_payment_intent_ids.append(pi["id"])
            assert pi["status"] == "requires_payment_method"

        with allure.step("Confirm — status becomes requires_capture"):
            payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)
            confirmed = payments_api.retrieve(pi["id"]).json()
            assert confirmed["status"] == "requires_capture"

        with allure.step("Capture — status becomes succeeded"):
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
@allure.severity(allure.severity_level.BLOCKER)
@pytest.mark.e2e
@pytest.mark.payment_intents
class TestEndToEndPaymentFlow:

    @allure.description("Full flow: Create Customer -> Create PaymentIntent -> Confirm -> Verify succeeded.")
    def test_full_automatic_capture_flow(
        self,
        customers_api,
        payments_api,
        created_customer_ids,
        created_payment_intent_ids,
    ):
        with allure.step("Create customer"):
            cust = customers_api.create(
                name="E2E User", email="e2e@example.com"
            ).json()
            created_customer_ids.append(cust["id"])

        with allure.step("Create PaymentIntent linked to customer"):
            pi = payments_api.create(
                amount=7500,
                currency="usd",
                customer=cust["id"],
                **{"payment_method_types[]": "card"},
            ).json()
            created_payment_intent_ids.append(pi["id"])
            assert pi["status"] == "requires_payment_method"

        with allure.step("Confirm payment"):
            confirmed = payments_api.confirm(
                pi["id"], payment_method=CARD_VISA_SUCCESS
            ).json()
            assert confirmed["status"] == "succeeded"

        with allure.step("Fetch and verify final state"):
            fetched = payments_api.retrieve(pi["id"]).json()
            assert fetched["status"] == "succeeded"
            assert fetched["amount"] == 7500
            assert fetched["customer"] == cust["id"]

    @allure.description("Full flow: Customer -> PaymentIntent(manual) -> Confirm -> Capture -> Verify.")
    def test_full_manual_capture_flow(
        self,
        customers_api,
        payments_api,
        created_customer_ids,
        created_payment_intent_ids,
    ):
        with allure.step("Create customer"):
            cust = customers_api.create(
                name="E2E Manual", email="e2e_manual@example.com"
            ).json()
            created_customer_ids.append(cust["id"])

        with allure.step("Create manual-capture PaymentIntent"):
            pi = payments_api.create(
                amount=10000,
                currency="usd",
                customer=cust["id"],
                capture_method="manual",
                **{"payment_method_types[]": "card"},
            ).json()
            created_payment_intent_ids.append(pi["id"])

        with allure.step("Confirm and verify requires_capture"):
            payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)
            confirmed = payments_api.retrieve(pi["id"]).json()
            assert confirmed["status"] == "requires_capture"

        with allure.step("Capture and verify succeeded"):
            payments_api.capture(pi["id"])
            captured = payments_api.retrieve(pi["id"]).json()
            assert captured["status"] == "succeeded"
            assert captured["amount_received"] == 10000


# ─────────────────────────────────────────────────────────────────────
#  Idempotency Key Tests
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("Idempotency")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.payment_intents
class TestIdempotency:

    @allure.description("Stripe Idempotency-Key header ensures the same request is not processed twice.")
    def test_same_key_returns_same_intent(
        self, payments_api, created_payment_intent_ids
    ):
        key = f"test-idem-{uuid.uuid4()}"

        with allure.step("Send same request twice with identical idempotency key"):
            resp1 = payments_api.create(idempotency_key=key, **VALID_PAYMENT_INTENT)
            resp2 = payments_api.create(idempotency_key=key, **VALID_PAYMENT_INTENT)

        with allure.step("Verify both return the same PaymentIntent ID"):
            body1 = resp1.json()
            body2 = resp2.json()
            assert resp1.status_code == 200
            assert resp2.status_code == 200
            assert body1["id"] == body2["id"]

        created_payment_intent_ids.append(body1["id"])

    def test_different_keys_create_different_intents(
        self, payments_api, created_payment_intent_ids
    ):
        """Different idempotency keys should create distinct PaymentIntents."""
        key1 = f"test-idem-{uuid.uuid4()}"
        key2 = f"test-idem-{uuid.uuid4()}"

        body1 = payments_api.create(idempotency_key=key1, **VALID_PAYMENT_INTENT).json()
        body2 = payments_api.create(idempotency_key=key2, **VALID_PAYMENT_INTENT).json()

        assert body1["id"] != body2["id"]

        created_payment_intent_ids.append(body1["id"])
        created_payment_intent_ids.append(body2["id"])
