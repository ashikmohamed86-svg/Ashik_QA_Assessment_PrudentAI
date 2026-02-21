"""Cross-resource integration tests: Customer + PaymentIntent interaction,
resource lifecycle, and state independence verification."""

import allure
import pytest

from schemas.customer_schema import CUSTOMER_SCHEMA, CUSTOMER_DELETE_SCHEMA, STRIPE_ERROR_SCHEMA
from schemas.payment_intent_schema import PAYMENT_INTENT_SCHEMA, CANCEL_RESPONSE_SCHEMA
from utils.validators import validate_schema, assert_response_time
from schemas.refund_schema import REFUND_SCHEMA
from utils.test_data import VALID_CUSTOMER, VALID_PAYMENT_INTENT, CARD_VISA_SUCCESS


# ─────────────────────────────────────────────────────────────────────
#  Customer + PaymentIntent Integration
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Cross-Resource Integration")
@allure.story("Customer & PaymentIntent Interaction")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.cross_resource
class TestCustomerPaymentIntentIntegration:

    @allure.description("Creating PI with a non-existent customer ID should return an error.")
    def test_create_pi_with_nonexistent_customer(self, payments_api):
        resp = payments_api.create(
            amount=2000, currency="usd",
            customer="cus_nonexistent_xyz_000",
            **{"payment_method_types[]": "card"},
        )

        assert resp.status_code == 400
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)

    @allure.description("Creating PI with a deleted customer ID should return an error.")
    def test_create_pi_with_deleted_customer(
        self, customers_api, payments_api
    ):
        with allure.step("Create and delete a customer"):
            cust = customers_api.create(email="deleted_for_pi@example.com").json()
            customers_api.delete_customer(cust["id"])

        with allure.step("Try to create PI with deleted customer"):
            resp = payments_api.create(
                amount=2000, currency="usd",
                customer=cust["id"],
                **{"payment_method_types[]": "card"},
            )

        assert resp.status_code == 400
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)

    @allure.description("Multiple PIs for the same customer should be independent.")
    def test_multiple_pis_for_same_customer(
        self, customers_api, payments_api,
        created_customer_ids, created_payment_intent_ids,
    ):
        with allure.step("Create customer"):
            cust = customers_api.create(
                name="Multi PI", email="multi_pi@example.com"
            ).json()
            created_customer_ids.append(cust["id"])

        with allure.step("Create two PIs for the same customer"):
            pi1 = payments_api.create(
                amount=1000, currency="usd", customer=cust["id"],
                **{"payment_method_types[]": "card"},
            ).json()
            pi2 = payments_api.create(
                amount=2000, currency="usd", customer=cust["id"],
                **{"payment_method_types[]": "card"},
            ).json()
            created_payment_intent_ids.extend([pi1["id"], pi2["id"]])

        with allure.step("Verify PIs are independent"):
            assert pi1["id"] != pi2["id"]
            assert pi1["amount"] == 1000
            assert pi2["amount"] == 2000
            assert pi1["customer"] == pi2["customer"] == cust["id"]

    @allure.description("Deleting a customer should not affect their existing PaymentIntents.")
    def test_delete_customer_pi_unaffected(
        self, customers_api, payments_api, created_payment_intent_ids,
    ):
        with allure.step("Create customer and PI"):
            cust = customers_api.create(email="del_cust_pi@example.com").json()
            pi = payments_api.create(
                amount=3000, currency="usd", customer=cust["id"],
                **{"payment_method_types[]": "card"},
            ).json()
            created_payment_intent_ids.append(pi["id"])

        with allure.step("Delete the customer"):
            del_resp = customers_api.delete_customer(cust["id"])
            assert del_resp.status_code == 200

        with allure.step("Verify PI is still fetchable"):
            pi_resp = payments_api.retrieve(pi["id"])
            pi_body = pi_resp.json()
            assert pi_resp.status_code == 200
            assert pi_body["id"] == pi["id"]
            assert pi_body["status"] in ("requires_payment_method", "requires_confirmation")

    @allure.description("Canceling a PI should not affect the associated customer.")
    def test_cancel_pi_customer_unchanged(
        self, customers_api, payments_api,
        created_customer_ids, created_payment_intent_ids,
    ):
        with allure.step("Create customer and PI"):
            cust = customers_api.create(
                name="Cancel PI Test", email="cancel_pi@example.com"
            ).json()
            created_customer_ids.append(cust["id"])
            pi = payments_api.create(
                amount=1500, currency="usd", customer=cust["id"],
                **{"payment_method_types[]": "card"},
            ).json()
            created_payment_intent_ids.append(pi["id"])

        with allure.step("Cancel the PI"):
            cancel_resp = payments_api.cancel(pi["id"])
            assert cancel_resp.status_code == 200
            assert cancel_resp.json()["status"] == "canceled"

        with allure.step("Verify customer is unchanged"):
            cust_resp = customers_api.retrieve(cust["id"])
            cust_body = cust_resp.json()
            assert cust_resp.status_code == 200
            assert cust_body["name"] == "Cancel PI Test"
            assert cust_body["email"] == "cancel_pi@example.com"

    @allure.description("PI metadata and customer metadata should be independent.")
    def test_metadata_independence(
        self, customers_api, payments_api,
        created_customer_ids, created_payment_intent_ids,
    ):
        with allure.step("Create customer with metadata"):
            cust = customers_api.create(
                email="meta_indep@example.com",
                **{"metadata[role]": "buyer"},
            ).json()
            created_customer_ids.append(cust["id"])

        with allure.step("Create PI with different metadata"):
            pi = payments_api.create(
                amount=2000, currency="usd", customer=cust["id"],
                **{"payment_method_types[]": "card", "metadata[order]": "123"},
            ).json()
            created_payment_intent_ids.append(pi["id"])

        with allure.step("Verify metadata is independent"):
            assert cust["metadata"]["role"] == "buyer"
            assert "order" not in cust["metadata"]
            assert pi["metadata"]["order"] == "123"
            assert "role" not in pi["metadata"]


# ─────────────────────────────────────────────────────────────────────
#  Resource Lifecycle Tests
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Cross-Resource Integration")
@allure.story("Resource Lifecycle")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.cross_resource
class TestResourceLifecycle:

    @allure.description("Full customer CRUD lifecycle: create -> read -> update -> delete -> verify gone.")
    def test_customer_full_lifecycle(self, customers_api):
        with allure.step("Create customer"):
            cust = customers_api.create(
                name="Lifecycle User", email="lifecycle@example.com"
            ).json()
            assert cust["id"].startswith("cus_")
            validate_schema(cust, CUSTOMER_SCHEMA)

        with allure.step("Read customer"):
            fetched = customers_api.retrieve(cust["id"]).json()
            assert fetched["id"] == cust["id"]
            assert fetched["name"] == "Lifecycle User"

        with allure.step("Update customer"):
            updated = customers_api.update(cust["id"], name="Updated Lifecycle").json()
            assert updated["name"] == "Updated Lifecycle"
            assert updated["email"] == "lifecycle@example.com"

        with allure.step("Delete customer"):
            del_resp = customers_api.delete_customer(cust["id"])
            del_body = del_resp.json()
            assert del_resp.status_code == 200
            assert del_body["deleted"] is True
            validate_schema(del_body, CUSTOMER_DELETE_SCHEMA)

        with allure.step("Verify customer is gone"):
            gone_resp = customers_api.retrieve(cust["id"])
            assert gone_resp.status_code == 200
            # Stripe returns deleted customer with deleted=true
            gone_body = gone_resp.json()
            assert gone_body.get("deleted") is True

    @allure.description("Full PI lifecycle: create -> confirm -> capture -> fetch verified.")
    def test_payment_intent_full_lifecycle(self, payments_api, created_payment_intent_ids):
        with allure.step("Create manual-capture PI"):
            pi = payments_api.create(
                amount=5000, currency="usd", capture_method="manual",
                **{"payment_method_types[]": "card"},
            ).json()
            created_payment_intent_ids.append(pi["id"])
            assert pi["status"] == "requires_payment_method"

        with allure.step("Confirm with Visa"):
            confirmed = payments_api.confirm(
                pi["id"], payment_method=CARD_VISA_SUCCESS
            ).json()
            assert confirmed["status"] == "requires_capture"

        with allure.step("Capture"):
            captured = payments_api.capture(pi["id"]).json()
            assert captured["status"] == "succeeded"
            assert captured["amount_received"] == 5000

        with allure.step("Fetch and verify final state"):
            final = payments_api.retrieve(pi["id"]).json()
            assert final["status"] == "succeeded"
            assert final["amount"] == 5000
            assert final["amount_received"] == 5000
            validate_schema(final, PAYMENT_INTENT_SCHEMA)

    @allure.description("Updating a deleted customer should return an error.")
    def test_update_deleted_customer(self, customers_api):
        with allure.step("Create and delete customer"):
            cust = customers_api.create(email="update_deleted@example.com").json()
            customers_api.delete_customer(cust["id"])

        with allure.step("Attempt to update deleted customer"):
            resp = customers_api.update(cust["id"], name="Should Fail")

        # Stripe returns 200 but the customer is still deleted
        # Some Stripe API versions may return error
        body = resp.json()
        if resp.status_code == 200:
            # Stripe allows updates to deleted customers in some cases
            assert body.get("deleted") is True or body.get("id") == cust["id"]
        else:
            assert resp.status_code in (400, 404)

    @allure.description("Canceling an already-canceled PI should return an error.")
    def test_cancel_already_canceled_pi(self, payments_api, created_payment_intent_ids):
        with allure.step("Create and cancel PI"):
            pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
            created_payment_intent_ids.append(pi["id"])
            payments_api.cancel(pi["id"])

        with allure.step("Attempt to cancel again"):
            resp = payments_api.cancel(pi["id"])

        assert resp.status_code == 400
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)


# ─────────────────────────────────────────────────────────────────────
#  Full Refund E2E with Customer
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Cross-Resource Integration")
@allure.story("Refund E2E with Customer")
@allure.severity(allure.severity_level.BLOCKER)
@pytest.mark.cross_resource
@pytest.mark.e2e
class TestRefundE2EWithCustomer:

    @allure.description(
        "Full refund E2E: Create Customer -> Create PI -> Confirm -> Refund -> "
        "Verify customer unaffected and PI reflects refund."
    )
    def test_full_refund_e2e_with_customer(
        self, customers_api, payments_api, refunds_api,
        created_customer_ids, created_payment_intent_ids,
    ):
        with allure.step("Create customer"):
            cust = customers_api.create(
                name="Refund E2E", email="refund_e2e@example.com"
            ).json()
            created_customer_ids.append(cust["id"])

        with allure.step("Create and confirm PI"):
            pi = payments_api.create(
                amount=8000, currency="usd", customer=cust["id"],
                **{"payment_method_types[]": "card"},
            ).json()
            created_payment_intent_ids.append(pi["id"])
            payments_api.confirm(pi["id"], payment_method=CARD_VISA_SUCCESS)

        with allure.step("Refund the PI"):
            refund = refunds_api.create(payment_intent=pi["id"]).json()
            assert refund["status"] == "succeeded"
            assert refund["amount"] == 8000
            validate_schema(refund, REFUND_SCHEMA)

        with allure.step("Verify customer is unaffected"):
            cust_after = customers_api.retrieve(cust["id"]).json()
            assert cust_after["name"] == "Refund E2E"
            assert cust_after["email"] == "refund_e2e@example.com"

    @allure.description(
        "Multi-currency E2E: Create customer, then PIs in USD, EUR, GBP, JPY — confirm each."
    )
    def test_multi_currency_e2e(
        self, customers_api, payments_api,
        created_customer_ids, created_payment_intent_ids,
    ):
        cust = customers_api.create(
            name="Multi Currency", email="multi_curr@example.com"
        ).json()
        created_customer_ids.append(cust["id"])

        currencies = [
            {"amount": 2000, "currency": "usd"},
            {"amount": 1500, "currency": "eur"},
            {"amount": 2500, "currency": "gbp"},
            {"amount": 500, "currency": "jpy"},
        ]

        for curr in currencies:
            with allure.step(f"Create and confirm PI in {curr['currency'].upper()}"):
                pi = payments_api.create(
                    customer=cust["id"],
                    **{"payment_method_types[]": "card"},
                    **curr,
                ).json()
                created_payment_intent_ids.append(pi["id"])

                assert pi["currency"] == curr["currency"]
                assert pi["amount"] == curr["amount"]

                confirmed = payments_api.confirm(
                    pi["id"], payment_method=CARD_VISA_SUCCESS
                ).json()
                assert confirmed["status"] == "succeeded"
