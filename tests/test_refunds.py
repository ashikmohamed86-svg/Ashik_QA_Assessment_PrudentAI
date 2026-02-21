"""Tests for Stripe Refunds API — full refund, partial refund, double refund,
refund lifecycle, list, reason, metadata, idempotency, and error handling."""

import uuid

import allure
import pytest

from schemas.refund_schema import REFUND_SCHEMA
from schemas.customer_schema import STRIPE_ERROR_SCHEMA
from utils.validators import validate_schema, assert_response_time, assert_response_headers
from utils.test_data import VALID_PAYMENT_INTENT, CARD_VISA_SUCCESS


def _succeed_payment(payments_api, ids_list, amount=2000):
    """Helper: create and confirm a PI so it can be refunded."""
    pi = payments_api.create(
        amount=amount, currency="usd", **{"payment_method_types[]": "card"}
    ).json()
    ids_list.append(pi["id"])
    payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)
    return pi["id"]


# ─────────────────────────────────────────────────────────────────────
#  Refund – Positive Flows
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Refunds API")
@allure.story("Create Refund")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.refunds
class TestRefundPositive:

    @allure.description("Full refund of a succeeded PaymentIntent — amount_refunded should match original.")
    def test_full_refund(self, payments_api, refunds_api, created_payment_intent_ids):
        pi_id = _succeed_payment(payments_api, created_payment_intent_ids, amount=2000)

        with allure.step("Create full refund"):
            resp = refunds_api.create(payment_intent=pi_id)
            body = resp.json()

        with allure.step("Validate refund response"):
            assert resp.status_code == 200
            assert body["id"].startswith("re_")
            assert body["amount"] == 2000
            assert body["status"] == "succeeded"
            assert body["payment_intent"] == pi_id
            validate_schema(body, REFUND_SCHEMA)

    @allure.description("Partial refund — refund less than the captured amount.")
    def test_partial_refund(self, payments_api, refunds_api, created_payment_intent_ids):
        pi_id = _succeed_payment(payments_api, created_payment_intent_ids, amount=5000)

        with allure.step("Create partial refund of 1500"):
            resp = refunds_api.create(payment_intent=pi_id, amount=1500)
            body = resp.json()

        with allure.step("Validate partial refund"):
            assert resp.status_code == 200
            assert body["amount"] == 1500
            assert body["status"] == "succeeded"
            validate_schema(body, REFUND_SCHEMA)

    @allure.description("Multiple partial refunds on the same PI should work until fully refunded.")
    def test_multiple_partial_refunds(self, payments_api, refunds_api, created_payment_intent_ids):
        pi_id = _succeed_payment(payments_api, created_payment_intent_ids, amount=3000)

        with allure.step("First partial refund of 1000"):
            r1 = refunds_api.create(payment_intent=pi_id, amount=1000).json()
            assert r1["amount"] == 1000

        with allure.step("Second partial refund of 1000"):
            r2 = refunds_api.create(payment_intent=pi_id, amount=1000).json()
            assert r2["amount"] == 1000
            assert r2["id"] != r1["id"]

        with allure.step("Third partial refund of remaining 1000"):
            r3 = refunds_api.create(payment_intent=pi_id, amount=1000).json()
            assert r3["amount"] == 1000

    @allure.description("Retrieve a refund by ID and verify details match.")
    def test_retrieve_refund(self, payments_api, refunds_api, created_payment_intent_ids):
        pi_id = _succeed_payment(payments_api, created_payment_intent_ids)

        refund = refunds_api.create(payment_intent=pi_id).json()
        resp = refunds_api.retrieve(refund["id"])
        body = resp.json()

        assert resp.status_code == 200
        assert body["id"] == refund["id"]
        assert body["amount"] == refund["amount"]
        validate_schema(body, REFUND_SCHEMA)

    @allure.description("Refund response time should be within 5 seconds.")
    def test_refund_response_time(self, payments_api, refunds_api, created_payment_intent_ids):
        pi_id = _succeed_payment(payments_api, created_payment_intent_ids)
        resp = refunds_api.create(payment_intent=pi_id)
        assert_response_time(resp, max_seconds=5.0)

    @allure.description("Verify refund response has proper headers.")
    def test_refund_response_headers(self, payments_api, refunds_api, created_payment_intent_ids):
        pi_id = _succeed_payment(payments_api, created_payment_intent_ids)
        resp = refunds_api.create(payment_intent=pi_id)
        assert_response_headers(resp)


# ─────────────────────────────────────────────────────────────────────
#  Refund – Negative Flows
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Refunds API")
@allure.story("Refund Error Scenarios")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.refunds
@pytest.mark.negative
class TestRefundNegative:

    @allure.description("Refunding more than the captured amount should fail.")
    def test_refund_exceeds_amount(self, payments_api, refunds_api, created_payment_intent_ids):
        pi_id = _succeed_payment(payments_api, created_payment_intent_ids, amount=2000)

        resp = refunds_api.create(payment_intent=pi_id, amount=9999)
        assert resp.status_code == 400
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)

    @allure.description("Refunding an uncaptured (not succeeded) PI should fail.")
    def test_refund_uncaptured_pi(self, payments_api, refunds_api, created_payment_intent_ids):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        resp = refunds_api.create(payment_intent=pi["id"])
        assert resp.status_code == 400
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)

    @allure.description("Double full refund — second refund after full refund should fail.")
    def test_double_full_refund(self, payments_api, refunds_api, created_payment_intent_ids):
        pi_id = _succeed_payment(payments_api, created_payment_intent_ids, amount=2000)

        with allure.step("First refund succeeds"):
            r1 = refunds_api.create(payment_intent=pi_id)
            assert r1.status_code == 200

        with allure.step("Second refund should fail — already fully refunded"):
            r2 = refunds_api.create(payment_intent=pi_id)
            assert r2.status_code == 400
            validate_schema(r2.json(), STRIPE_ERROR_SCHEMA)

    @allure.description("Refunding a non-existent PaymentIntent should fail.")
    def test_refund_nonexistent_pi(self, refunds_api):
        resp = refunds_api.create(payment_intent="pi_nonexistent_xyz_000")
        assert resp.status_code in (400, 404)
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)

    @allure.description("Refunding a canceled PI should fail.")
    def test_refund_canceled_pi(self, payments_api, refunds_api, created_payment_intent_ids):
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])
        payments_api.cancel(pi["id"])

        resp = refunds_api.create(payment_intent=pi["id"])
        assert resp.status_code == 400
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)


# ─────────────────────────────────────────────────────────────────────
#  Refund – Lifecycle Verification
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Refunds API")
@allure.story("Refund Lifecycle")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.refunds
@pytest.mark.e2e
class TestRefundLifecycle:

    @allure.description(
        "Full refund lifecycle: Create PI -> Confirm -> Refund -> Verify PI status changes."
    )
    def test_full_refund_lifecycle(self, payments_api, refunds_api, created_payment_intent_ids):
        with allure.step("Create and confirm PI"):
            pi_id = _succeed_payment(payments_api, created_payment_intent_ids, amount=4000)

        with allure.step("Verify PI is succeeded"):
            pi = payments_api.retrieve(pi_id).json()
            assert pi["status"] == "succeeded"

        with allure.step("Refund the PI"):
            refund = refunds_api.create(payment_intent=pi_id).json()
            assert refund["status"] == "succeeded"
            assert refund["amount"] == 4000

        with allure.step("Verify PI reflects refund"):
            pi_after = payments_api.retrieve(pi_id).json()
            assert pi_after["amount_received"] == 4000

    @allure.description(
        "Partial refund then remaining refund — verify cumulative refund behavior."
    )
    def test_partial_then_remaining_refund(self, payments_api, refunds_api, created_payment_intent_ids):
        pi_id = _succeed_payment(payments_api, created_payment_intent_ids, amount=6000)

        with allure.step("Partial refund of 2000"):
            r1 = refunds_api.create(payment_intent=pi_id, amount=2000).json()
            assert r1["amount"] == 2000

        with allure.step("Refund remaining 4000"):
            r2 = refunds_api.create(payment_intent=pi_id, amount=4000).json()
            assert r2["amount"] == 4000

        with allure.step("Further refund should fail — fully refunded"):
            r3 = refunds_api.create(payment_intent=pi_id, amount=1)
            assert r3.status_code == 400


# ─────────────────────────────────────────────────────────────────────
#  Refund – List & Filter
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Refunds API")
@allure.story("List & Filter")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.refunds
class TestRefundList:

    @allure.description("List refunds with limit parameter.")
    def test_list_refunds(self, refunds_api):
        resp = refunds_api.list_refunds(limit=5)
        body = resp.json()

        assert resp.status_code == 200
        assert body["object"] == "list"
        assert len(body["data"]) <= 5
        for refund in body["data"]:
            assert refund["object"] == "refund"
            assert refund["id"].startswith("re_")

    @allure.description("List refunds filtered by payment_intent.")
    def test_list_refunds_by_pi(self, payments_api, refunds_api, created_payment_intent_ids):
        pi_id = _succeed_payment(payments_api, created_payment_intent_ids, amount=2000)
        refunds_api.create(payment_intent=pi_id)

        resp = refunds_api.list_refunds(limit=10, payment_intent=pi_id)
        body = resp.json()

        assert resp.status_code == 200
        assert len(body["data"]) >= 1
        for refund in body["data"]:
            assert refund["payment_intent"] == pi_id


# ─────────────────────────────────────────────────────────────────────
#  Refund – Reason & Metadata
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Refunds API")
@allure.story("Reason & Metadata")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.refunds
class TestRefundReasonMetadata:

    @pytest.mark.parametrize(
        "reason",
        ["duplicate", "fraudulent", "requested_by_customer"],
        ids=["duplicate", "fraudulent", "requested_by_customer"],
    )
    @allure.description("Create refund with reason parameter — verify it's stored.")
    def test_refund_with_reason(self, payments_api, refunds_api, created_payment_intent_ids, reason):
        pi_id = _succeed_payment(payments_api, created_payment_intent_ids, amount=2000)

        resp = refunds_api.create(payment_intent=pi_id, reason=reason)
        body = resp.json()

        assert resp.status_code == 200
        assert body["reason"] == reason

    @allure.description("Create refund with metadata and verify it persists.")
    def test_refund_with_metadata(self, payments_api, refunds_api, created_payment_intent_ids):
        pi_id = _succeed_payment(payments_api, created_payment_intent_ids, amount=3000)

        resp = refunds_api.create(
            payment_intent=pi_id,
            **{"metadata[reason_detail]": "customer_complaint", "metadata[ticket]": "T-001"},
        )
        body = resp.json()

        assert resp.status_code == 200
        assert body["metadata"]["reason_detail"] == "customer_complaint"
        assert body["metadata"]["ticket"] == "T-001"

    @allure.description("Refund with amount=0 should be rejected.")
    def test_refund_zero_amount(self, payments_api, refunds_api, created_payment_intent_ids):
        pi_id = _succeed_payment(payments_api, created_payment_intent_ids, amount=2000)

        resp = refunds_api.create(payment_intent=pi_id, amount=0)
        assert resp.status_code == 400

    @allure.description("Refund idempotency — same key returns same refund.")
    def test_refund_idempotency(self, payments_api, refunds_api, created_payment_intent_ids):
        pi_id = _succeed_payment(payments_api, created_payment_intent_ids, amount=2000)
        key = f"refund-idem-{uuid.uuid4()}"

        url = f"{refunds_api.base_url}/refunds"
        resp1 = refunds_api.session.post(
            url,
            data={"payment_intent": pi_id},
            headers={"Idempotency-Key": key},
            timeout=refunds_api.timeout,
        )
        resp2 = refunds_api.session.post(
            url,
            data={"payment_intent": pi_id},
            headers={"Idempotency-Key": key},
            timeout=refunds_api.timeout,
        )

        body1, body2 = resp1.json(), resp2.json()
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert body1["id"] == body2["id"]
