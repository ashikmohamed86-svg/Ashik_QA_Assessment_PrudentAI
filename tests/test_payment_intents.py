"""Tests for Stripe PaymentIntents API – create, confirm, capture, fetch."""

import uuid

import allure
import pytest

from schemas.payment_intent_schema import (
    PAYMENT_INTENT_SCHEMA,
    PAYMENT_INTENT_CONFIRM_SCHEMA,
    PAYMENT_INTENT_LIST_SCHEMA,
    CANCEL_RESPONSE_SCHEMA,
)
from schemas.customer_schema import STRIPE_ERROR_SCHEMA
from utils.validators import (
    validate_schema, is_valid_iso_currency,
    assert_response_time, assert_response_headers,
)
from utils.test_data import (
    VALID_PAYMENT_INTENT,
    VALID_CUSTOMER,
    PAYMENT_INTENT_WITH_RECEIPT,
    PAYMENT_INTENT_MANUAL_CAPTURE,
    PAYMENT_INTENT_MIN_AMOUNT,
    PAYMENT_INTENT_LARGE_AMOUNT,
    PAYMENT_INTENT_EUR,
    PAYMENT_INTENT_GBP,
    PAYMENT_INTENT_FLOAT_AMOUNT,
    PAYMENT_INTENT_JPY,
    PAYMENT_INTENT_WITH_DESCRIPTION,
    PAYMENT_INTENT_WITH_METADATA,
    CARD_VISA_SUCCESS,
    CARD_MASTERCARD_SUCCESS,
    CARD_DECLINED,
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

    @allure.description("PI-E2E-02: Create PaymentIntent with customer attached; verify customer ID echoed back.")
    def test_create_with_customer_attached(
        self, customers_api, payments_api, created_customer_ids, created_payment_intent_ids
    ):
        with allure.step("Create a customer"):
            cust = customers_api.create(**VALID_CUSTOMER).json()
            created_customer_ids.append(cust["id"])

        with allure.step("Create PaymentIntent with customer"):
            resp = payments_api.create(
                amount=1000, currency="usd", customer=cust["id"],
                **{"payment_method_types[]": "card"},
            )
            body = resp.json()

        with allure.step("Verify customer ID is in response"):
            assert resp.status_code == 200
            assert body["customer"] == cust["id"]
            assert body["status"] in ("requires_payment_method", "requires_confirmation")
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

    @allure.description("CONF-NEG-02: Confirm a non-existing PI should return 404 with error schema.")
    def test_confirm_non_existing_intent(self, payments_api):
        resp = payments_api.confirm("pi_DOES_NOT_EXIST_123", payment_method=CARD_VISA_SUCCESS)
        body = resp.json()

        assert resp.status_code == 404
        validate_schema(body, STRIPE_ERROR_SCHEMA)


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

    @allure.description(
        "FETCHPI-VAL-01: Verify created timestamp is stable across fetches "
        "and does not change after confirm."
    )
    def test_verify_timestamps(
        self, payments_api, created_payment_intent_ids
    ):
        with allure.step("Create PI and check timestamp"):
            pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
            created_payment_intent_ids.append(pi["id"])
            assert isinstance(pi["created"], int)
            assert pi["created"] > 0

        with allure.step("Fetch PI and verify created timestamp is stable"):
            fetched = payments_api.retrieve(pi["id"]).json()
            assert fetched["created"] == pi["created"]

        with allure.step("Confirm PI and verify created timestamp unchanged"):
            payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)
            confirmed = payments_api.retrieve(pi["id"]).json()
            assert confirmed["created"] == pi["created"]


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

        with allure.step("Fetch PI and verify final state"):
            fetched = payments_api.retrieve(pi["id"]).json()
            assert fetched["status"] == "succeeded"
            assert fetched["amount"] == 7500
            assert fetched["customer"] == cust["id"]

        with allure.step("Fetch Customer and ensure still accessible + fields unchanged"):
            cust_after = customers_api.retrieve(cust["id"]).json()
            assert cust_after["id"] == cust["id"]
            assert cust_after["name"] == "E2E User"
            assert cust_after["email"] == "e2e@example.com"

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


# ─────────────────────────────────────────────────────────────────────
#  Additional Positive Tests
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("Additional Positive Scenarios")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.payment_intents
class TestPaymentIntentPositive:

    @allure.description("Verify Mastercard test token works alongside Visa.")
    def test_confirm_with_mastercard(
        self, payments_api, created_payment_intent_ids
    ):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.confirm(pi["id"], payment_method=CARD_MASTERCARD_SUCCESS)
        body = resp.json()

        assert resp.status_code == 200
        assert body["status"] == "succeeded"

    @allure.description("Verify PaymentIntent creation works with EUR currency.")
    def test_create_with_eur_currency(
        self, payments_api, created_payment_intent_ids
    ):
        resp = payments_api.create(**PAYMENT_INTENT_EUR)
        body = resp.json()

        assert resp.status_code == 200
        assert body["currency"] == "eur"
        assert body["amount"] == 1500
        created_payment_intent_ids.append(body["id"])

    @allure.description("Verify PaymentIntent creation works with GBP currency.")
    def test_create_with_gbp_currency(
        self, payments_api, created_payment_intent_ids
    ):
        resp = payments_api.create(**PAYMENT_INTENT_GBP)
        body = resp.json()

        assert resp.status_code == 200
        assert body["currency"] == "gbp"
        assert body["amount"] == 2500
        created_payment_intent_ids.append(body["id"])

    @allure.description("Verify partial capture: capture less than the authorized amount.")
    def test_partial_capture(
        self, payments_api, created_payment_intent_ids
    ):
        pi = payments_api.create(**PAYMENT_INTENT_MANUAL_CAPTURE).json()
        created_payment_intent_ids.append(pi["id"])
        payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)

        partial_amount = pi["amount"] - 500
        resp = payments_api.capture(pi["id"], amount_to_capture=partial_amount)
        body = resp.json()

        assert resp.status_code == 200
        assert body["status"] == "succeeded"
        assert body["amount_received"] == partial_amount

    @allure.description("Verify canceling a PaymentIntent that hasn't been confirmed yet.")
    def test_cancel_uncaptured_intent(
        self, payments_api, created_payment_intent_ids
    ):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.cancel(pi["id"])
        body = resp.json()

        assert resp.status_code == 200
        assert body["status"] == "canceled"


# ─────────────────────────────────────────────────────────────────────
#  Negative – PaymentIntent Error Scenarios
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("Negative Error Scenarios")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.negative
@pytest.mark.payment_intents
class TestPaymentIntentNegativeErrors:

    def test_cancel_already_succeeded_intent(
        self, payments_api, created_payment_intent_ids
    ):
        """Canceling a succeeded PaymentIntent should fail."""
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)
        resp = payments_api.cancel(pi["id"])

        assert resp.status_code == 400
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)

    def test_confirm_with_invalid_payment_method(
        self, payments_api, created_payment_intent_ids
    ):
        """Using a garbage payment method token should fail."""
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.confirm(pi["id"], payment_method="pm_invalid_garbage_token")
        assert resp.status_code == 400
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)

    def test_float_amount_rejected(self, payments_api):
        """Stripe amount must be integer (minor units); float should fail."""
        resp = payments_api.create(**PAYMENT_INTENT_FLOAT_AMOUNT)
        assert resp.status_code == 400
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)

    def test_fetch_invalid_payment_intent_id(self, payments_api):
        """Completely invalid ID format should return error."""
        resp = payments_api.retrieve("not_a_valid_id")
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────
#  Performance – PaymentIntent Response Times
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("Performance")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.payment_intents
class TestPaymentIntentPerformance:

    def test_create_response_time(self, payments_api, created_payment_intent_ids):
        resp = payments_api.create(**VALID_PAYMENT_INTENT)
        assert_response_time(resp, max_seconds=5.0)
        created_payment_intent_ids.append(resp.json()["id"])

    def test_fetch_response_time(self, payments_api, created_payment_intent_ids):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.retrieve(pi["id"])
        assert_response_time(resp, max_seconds=5.0)

    def test_confirm_response_time(self, payments_api, created_payment_intent_ids):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)
        assert_response_time(resp, max_seconds=5.0)

    def test_capture_response_time(self, payments_api, created_payment_intent_ids):
        pi = payments_api.create(**PAYMENT_INTENT_MANUAL_CAPTURE).json()
        created_payment_intent_ids.append(pi["id"])
        payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)

        resp = payments_api.capture(pi["id"])
        assert_response_time(resp, max_seconds=5.0)


# ─────────────────────────────────────────────────────────────────────
#  Boundary / Limit – PaymentIntent Amounts
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("Boundary & Limit")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.negative
@pytest.mark.payment_intents
class TestPaymentIntentBoundary:

    @allure.description("Stripe minimum for USD is 50 cents ($0.50). Verify it's accepted.")
    def test_minimum_valid_amount(self, payments_api, created_payment_intent_ids):
        resp = payments_api.create(**PAYMENT_INTENT_MIN_AMOUNT)
        body = resp.json()

        assert resp.status_code == 200
        assert body["amount"] == 50
        created_payment_intent_ids.append(body["id"])

    @allure.description("Test with a very large amount near the boundary.")
    def test_large_amount(self, payments_api, created_payment_intent_ids):
        resp = payments_api.create(**PAYMENT_INTENT_LARGE_AMOUNT)
        body = resp.json()

        assert resp.status_code == 200
        assert body["amount"] == 99999999
        created_payment_intent_ids.append(body["id"])

    @allure.description("Amount just below Stripe minimum (49 cents) should be rejected.")
    def test_below_minimum_amount(self, payments_api):
        resp = payments_api.create(
            amount=49, currency="usd", **{"payment_method_types[]": "card"}
        )
        assert resp.status_code == 400
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)

    @allure.description("PI-VAL-01: Amount=1 boundary test — assert actual Stripe behavior.")
    def test_amount_boundary_one(self, payments_api, created_payment_intent_ids):
        resp = payments_api.create(
            amount=1, currency="usd", **{"payment_method_types[]": "card"}
        )
        body = resp.json()

        if resp.status_code == 200:
            assert body["amount"] == 1
            created_payment_intent_ids.append(body["id"])
        else:
            # Stripe rejects amount=1 for USD (minimum is 50)
            assert resp.status_code == 400
            validate_schema(body, STRIPE_ERROR_SCHEMA)


# ─────────────────────────────────────────────────────────────────────
#  PaymentIntent – Missing/Empty Field Validation
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("Missing Field Validation")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.negative
@pytest.mark.payment_intents
class TestPaymentIntentMissingFields:

    @allure.description("PI-VAL-07: Create PI without payment_method_types should use Stripe default or error.")
    def test_missing_payment_method_types(self, payments_api, created_payment_intent_ids):
        resp = payments_api.create(amount=1000, currency="usd")
        body = resp.json()

        # Stripe may default to card or return error — assert actual behavior
        if resp.status_code == 200:
            assert body["id"].startswith("pi_")
            created_payment_intent_ids.append(body["id"])
        else:
            assert resp.status_code == 400
            validate_schema(body, STRIPE_ERROR_SCHEMA)

    @allure.description("PI-VAL-07b: Create PI with empty payment_method_types.")
    def test_empty_payment_method_types(self, payments_api, created_payment_intent_ids):
        resp = payments_api.create(
            amount=1000, currency="usd", **{"payment_method_types[]": ""}
        )
        body = resp.json()

        if resp.status_code == 200:
            created_payment_intent_ids.append(body["id"])
        else:
            assert resp.status_code == 400
            validate_schema(body, STRIPE_ERROR_SCHEMA)

    @allure.description("PI-VAL-08: Create PI with invalid receipt_email format.")
    def test_invalid_receipt_email(self, payments_api, created_payment_intent_ids):
        resp = payments_api.create(
            amount=1000, currency="usd",
            receipt_email="badmail",
            **{"payment_method_types[]": "card"},
        )
        body = resp.json()

        if resp.status_code == 200:
            # Stripe accepted — our validator flags it
            from utils.validators import is_valid_email
            assert not is_valid_email(body.get("receipt_email", "")), (
                "receipt_email 'badmail' should fail email format validation"
            )
            created_payment_intent_ids.append(body["id"])
        else:
            assert resp.status_code == 400
            validate_schema(body, STRIPE_ERROR_SCHEMA)


# ─────────────────────────────────────────────────────────────────────
#  E2E Negative Flows
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("E2E Negative Flows")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.e2e
@pytest.mark.payment_intents
class TestE2ENegativeFlows:

    @allure.description(
        "FLOW-E2E-NEG-01: Full declined payment flow — "
        "Create Customer → Create PI → Confirm with declined card → Fetch PI."
    )
    def test_payment_declined_e2e(
        self, customers_api, payments_api,
        created_customer_ids, created_payment_intent_ids,
    ):
        with allure.step("Create customer"):
            cust = customers_api.create(
                name="Decline User", email="decline@example.com"
            ).json()
            created_customer_ids.append(cust["id"])

        with allure.step("Create PI linked to customer"):
            pi = payments_api.create(
                amount=5000, currency="usd", customer=cust["id"],
                **{"payment_method_types[]": "card"},
            ).json()
            created_payment_intent_ids.append(pi["id"])

        with allure.step("Confirm with declined card"):
            resp = payments_api.confirm(pi["id"], payment_method=CARD_DECLINED)
            assert resp.status_code == 402
            assert resp.json()["error"]["code"] == "card_declined"

        with allure.step("Fetch PI and verify NOT succeeded"):
            fetched = payments_api.retrieve(pi["id"]).json()
            assert fetched["status"] != "succeeded"
            assert fetched["status"] == "requires_payment_method"

    @allure.description(
        "FLOW-E2E-NEG-02: Confirm without PM fails, then recover with valid card."
    )
    def test_confirm_without_pm_then_recover(
        self, payments_api, created_payment_intent_ids,
    ):
        with allure.step("Create PI"):
            pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
            created_payment_intent_ids.append(pi["id"])

        with allure.step("Confirm without payment method — expect error"):
            resp1 = payments_api.confirm(pi["id"])
            assert resp1.status_code == 400

        with allure.step("Recover: confirm again with valid Visa card"):
            resp2 = payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)
            body = resp2.json()
            assert resp2.status_code == 200
            assert body["status"] == "succeeded"

        with allure.step("Fetch and verify final succeeded state"):
            fetched = payments_api.retrieve(pi["id"]).json()
            assert fetched["status"] == "succeeded"


# ─────────────────────────────────────────────────────────────────────
#  Zero-Decimal Currency & Description Tests
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("Zero-Decimal Currency & Description")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.payment_intents
class TestPaymentIntentZeroCurrency:

    @allure.description("JPY is a zero-decimal currency; amount=500 means 500 yen, not 5.00.")
    def test_jpy_zero_decimal_currency(self, payments_api, created_payment_intent_ids):
        resp = payments_api.create(**PAYMENT_INTENT_JPY)
        body = resp.json()

        assert resp.status_code == 200
        assert body["currency"] == "jpy"
        assert body["amount"] == 500
        validate_schema(body, PAYMENT_INTENT_SCHEMA)
        created_payment_intent_ids.append(body["id"])

    @allure.description("Verify PI creation with description field.")
    def test_create_with_description(self, payments_api, created_payment_intent_ids):
        resp = payments_api.create(**PAYMENT_INTENT_WITH_DESCRIPTION)
        body = resp.json()

        assert resp.status_code == 200
        assert body["description"] == PAYMENT_INTENT_WITH_DESCRIPTION["description"]
        created_payment_intent_ids.append(body["id"])

    @allure.description("Cancel PI with cancellation_reason parameter.")
    def test_cancel_with_reason(self, payments_api, created_payment_intent_ids):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.cancel(pi["id"], cancellation_reason="requested_by_customer")
        body = resp.json()

        assert resp.status_code == 200
        assert body["status"] == "canceled"
        assert body.get("cancellation_reason") == "requested_by_customer"
        validate_schema(body, CANCEL_RESPONSE_SCHEMA)


# ─────────────────────────────────────────────────────────────────────
#  PaymentIntent List & Search
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("List & Search")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.payment_intents
class TestPaymentIntentListAndSearch:

    @allure.description("List payment intents with limit parameter.")
    def test_list_with_limit(self, payments_api):
        resp = payments_api.list_intents(limit=3)
        body = resp.json()

        assert resp.status_code == 200
        assert len(body["data"]) <= 3
        validate_schema(body, PAYMENT_INTENT_LIST_SCHEMA)

    @allure.description("Paginate through payment intents using starting_after cursor.")
    def test_paginate_payment_intents(self, payments_api):
        page1_resp = payments_api.list_intents(limit=2)
        page1 = page1_resp.json()
        assert page1_resp.status_code == 200
        assert len(page1["data"]) > 0

        if page1["has_more"]:
            cursor = page1["data"][-1]["id"]
            page2 = payments_api.list_intents(limit=2, starting_after=cursor).json()
            assert page2["data"][0]["id"] != cursor

    @allure.description("Verify listing returns only payment_intent objects.")
    def test_list_object_types(self, payments_api):
        resp = payments_api.list_intents(limit=5)
        body = resp.json()

        assert resp.status_code == 200
        for pi in body["data"]:
            assert pi["object"] == "payment_intent"
            assert pi["id"].startswith("pi_")


# ─────────────────────────────────────────────────────────────────────
#  PaymentIntent Metadata
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("Metadata")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.payment_intents
class TestPaymentIntentMetadata:

    @allure.description("Create PI with metadata and verify it persists.")
    def test_create_with_metadata(self, payments_api, created_payment_intent_ids):
        resp = payments_api.create(**PAYMENT_INTENT_WITH_METADATA)
        body = resp.json()

        assert resp.status_code == 200
        assert body["metadata"]["order_id"] == "ord_12345"
        assert body["metadata"]["source"] == "automation"
        created_payment_intent_ids.append(body["id"])

    @allure.description("Update PI metadata after creation.")
    def test_update_metadata(self, payments_api, created_payment_intent_ids):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.update(
            pi["id"],
            **{"metadata[tracking]": "updated_value", "metadata[new_key]": "new_value"},
        )
        body = resp.json()

        assert resp.status_code == 200
        assert body["metadata"]["tracking"] == "updated_value"
        assert body["metadata"]["new_key"] == "new_value"


# ─────────────────────────────────────────────────────────────────────
#  PaymentIntent – Update Before Confirmation
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("Update PaymentIntent")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.payment_intents
class TestPaymentIntentUpdate:

    @allure.description("Update PI amount before confirmation — should succeed.")
    def test_update_amount_before_confirm(self, payments_api, created_payment_intent_ids):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.update(pi["id"], amount=5000)
        body = resp.json()

        assert resp.status_code == 200
        assert body["amount"] == 5000

    @allure.description("Update PI description after creation.")
    def test_update_description(self, payments_api, created_payment_intent_ids):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.update(pi["id"], description="Updated order description")
        body = resp.json()

        assert resp.status_code == 200
        assert body["description"] == "Updated order description"

    @allure.description("Updating currency on unconfirmed PI is allowed by Stripe.")
    def test_update_currency_allowed_before_confirm(self, payments_api, created_payment_intent_ids):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.update(pi["id"], currency="eur")
        body = resp.json()
        # Stripe allows currency changes on unconfirmed PIs
        assert resp.status_code == 200
        assert body["currency"] == "eur"

    @allure.description("Retrieve a canceled PI and validate full canceled state schema.")
    def test_retrieve_canceled_pi(self, payments_api, created_payment_intent_ids):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])
        payments_api.cancel(pi["id"])

        fetched = payments_api.retrieve(pi["id"]).json()
        assert fetched["status"] == "canceled"
        assert fetched["id"] == pi["id"]
        validate_schema(fetched, PAYMENT_INTENT_SCHEMA)


# ─────────────────────────────────────────────────────────────────────
#  PaymentIntent – All Cancellation Reasons
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("Cancellation Reasons")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.payment_intents
class TestCancellationReasons:

    @pytest.mark.parametrize(
        "reason",
        ["duplicate", "fraudulent", "requested_by_customer", "abandoned"],
        ids=["duplicate", "fraudulent", "requested_by_customer", "abandoned"],
    )
    @allure.description("Cancel PI with each valid cancellation_reason value.")
    def test_cancel_with_all_reasons(self, payments_api, created_payment_intent_ids, reason):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.cancel(pi["id"], cancellation_reason=reason)
        body = resp.json()

        assert resp.status_code == 200
        assert body["status"] == "canceled"
        assert body.get("cancellation_reason") == reason


# ─────────────────────────────────────────────────────────────────────
#  PaymentIntent – List Edge Cases
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("List Edge Cases")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.payment_intents
class TestPaymentIntentListEdgeCases:

    @allure.description("List PIs filtered by customer ID.")
    def test_list_by_customer(self, customers_api, payments_api,
                               created_customer_ids, created_payment_intent_ids):
        cust = customers_api.create(email="listfilter@example.com").json()
        created_customer_ids.append(cust["id"])

        pi = payments_api.create(
            amount=1000, currency="usd", customer=cust["id"],
            **{"payment_method_types[]": "card"},
        ).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.list_intents(limit=5, customer=cust["id"])
        body = resp.json()

        assert resp.status_code == 200
        for item in body["data"]:
            assert item["customer"] == cust["id"]

    @allure.description("List PI response time should be under 5 seconds.")
    def test_list_pi_response_time(self, payments_api):
        resp = payments_api.list_intents(limit=10)
        assert_response_time(resp, max_seconds=5.0)

    @allure.description("Cancel PI response time should be under 5 seconds.")
    def test_cancel_pi_response_time(self, payments_api, created_payment_intent_ids):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])
        resp = payments_api.cancel(pi["id"])
        assert_response_time(resp, max_seconds=5.0)


# ─────────────────────────────────────────────────────────────────────
#  PaymentIntent – Charge & Receipt Verification
# ─────────────────────────────────────────────────────────────────────
@allure.feature("PaymentIntents API")
@allure.story("Charge & Receipt Verification")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.payment_intents
class TestChargeReceiptVerification:

    @allure.description(
        "After a successful payment, latest_charge should be populated "
        "and point to a valid charge object."
    )
    def test_latest_charge_populated_after_payment(
        self, payments_api, created_payment_intent_ids
    ):
        with allure.step("Create and confirm PI"):
            pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
            created_payment_intent_ids.append(pi["id"])
            payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)

        with allure.step("Fetch PI and verify latest_charge"):
            fetched = payments_api.retrieve(pi["id"]).json()
            assert fetched["status"] == "succeeded"
            assert fetched.get("latest_charge") is not None
            assert fetched["latest_charge"].startswith("ch_")

    @allure.description(
        "Expand charges on a succeeded PI to verify charge details — "
        "amount, currency, paid status, and payment method."
    )
    def test_expand_charges_after_payment(
        self, payments_api, created_payment_intent_ids
    ):
        with allure.step("Create and confirm PI"):
            pi = payments_api.create(
                amount=3000, currency="usd",
                **{"payment_method_types[]": "card"},
            ).json()
            created_payment_intent_ids.append(pi["id"])
            payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)

        with allure.step("Fetch with expand[]=latest_charge"):
            url = f"{payments_api.base_url}/payment_intents/{pi['id']}"
            resp = payments_api.session.get(
                url,
                params={"expand[]": "latest_charge"},
                timeout=payments_api.timeout,
            )
            body = resp.json()

        with allure.step("Verify expanded charge details"):
            assert resp.status_code == 200
            charge = body["latest_charge"]
            # When expanded, latest_charge is an object not a string
            assert isinstance(charge, dict)
            assert charge["object"] == "charge"
            assert charge["amount"] == 3000
            assert charge["currency"] == "usd"
            assert charge["paid"] is True
            assert charge["status"] == "succeeded"

    @allure.description(
        "After a successful payment, the expanded charge should contain "
        "a receipt_url for the customer."
    )
    def test_receipt_url_generated_after_payment(
        self, payments_api, created_payment_intent_ids
    ):
        with allure.step("Create and confirm PI with receipt_email"):
            pi = payments_api.create(
                amount=2500, currency="usd",
                receipt_email="receipt_test@example.com",
                **{"payment_method_types[]": "card"},
            ).json()
            created_payment_intent_ids.append(pi["id"])
            payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)

        with allure.step("Fetch with expanded charge and check receipt_url"):
            url = f"{payments_api.base_url}/payment_intents/{pi['id']}"
            resp = payments_api.session.get(
                url,
                params={"expand[]": "latest_charge"},
                timeout=payments_api.timeout,
            )
            body = resp.json()
            charge = body["latest_charge"]

            assert isinstance(charge, dict)
            assert charge.get("receipt_url") is not None
            assert charge["receipt_url"].startswith("https://")
            assert charge["receipt_email"] == "receipt_test@example.com"

    @allure.description(
        "After a successful payment, the expanded charge should contain "
        "payment_method_details with card brand and last4."
    )
    def test_charge_payment_method_details(
        self, payments_api, created_payment_intent_ids
    ):
        with allure.step("Create and confirm PI"):
            pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
            created_payment_intent_ids.append(pi["id"])
            payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)

        with allure.step("Fetch with expanded charge"):
            url = f"{payments_api.base_url}/payment_intents/{pi['id']}"
            resp = payments_api.session.get(
                url,
                params={"expand[]": "latest_charge"},
                timeout=payments_api.timeout,
            )
            charge = resp.json()["latest_charge"]

        with allure.step("Verify payment method details"):
            assert isinstance(charge, dict)
            pm_details = charge.get("payment_method_details")
            assert pm_details is not None
            assert pm_details["type"] == "card"
            card = pm_details["card"]
            assert card["brand"] == "visa"
            assert len(card["last4"]) == 4
            assert card["exp_month"] is not None
            assert card["exp_year"] is not None

    @allure.description(
        "Verify that an uncaptured (manual capture) PI does NOT generate "
        "a succeeded charge — charge should be status=pending or amount_captured=0."
    )
    def test_charge_not_captured_until_capture(
        self, payments_api, created_payment_intent_ids
    ):
        with allure.step("Create manual-capture PI and confirm"):
            pi = payments_api.create(**PAYMENT_INTENT_MANUAL_CAPTURE).json()
            created_payment_intent_ids.append(pi["id"])
            payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)

        with allure.step("Fetch with expanded charge before capture"):
            url = f"{payments_api.base_url}/payment_intents/{pi['id']}"
            resp = payments_api.session.get(
                url,
                params={"expand[]": "latest_charge"},
                timeout=payments_api.timeout,
            )
            body = resp.json()
            assert body["status"] == "requires_capture"
            charge = body["latest_charge"]
            assert isinstance(charge, dict)
            assert charge["captured"] is False

        with allure.step("Capture and verify charge is now captured"):
            payments_api.capture(pi["id"])
            resp2 = payments_api.session.get(
                url,
                params={"expand[]": "latest_charge"},
                timeout=payments_api.timeout,
            )
            body2 = resp2.json()
            assert body2["status"] == "succeeded"
            assert body2["latest_charge"]["captured"] is True

    @allure.description(
        "A declined payment should NOT produce a succeeded charge — "
        "latest_charge should reflect the failure."
    )
    def test_declined_payment_no_succeeded_charge(
        self, payments_api, created_payment_intent_ids
    ):
        with allure.step("Create PI and attempt confirm with declined card"):
            pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
            created_payment_intent_ids.append(pi["id"])
            resp = payments_api.confirm(pi["id"], payment_method=CARD_DECLINED)
            assert resp.status_code == 402

        with allure.step("Fetch PI and verify status is not succeeded"):
            fetched = payments_api.retrieve(pi["id"]).json()
            assert fetched["status"] != "succeeded"
            # latest_charge may or may not be present depending on Stripe version
            if fetched.get("latest_charge"):
                url = f"{payments_api.base_url}/payment_intents/{pi['id']}"
                expanded = payments_api.session.get(
                    url,
                    params={"expand[]": "latest_charge"},
                    timeout=payments_api.timeout,
                ).json()
                charge = expanded["latest_charge"]
                if isinstance(charge, dict):
                    assert charge["status"] == "failed"
