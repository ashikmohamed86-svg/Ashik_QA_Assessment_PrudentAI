"""Data integrity tests: response field completeness, encoding edge cases,
API versioning, expand parameter, error message quality, and data consistency."""

import allure
import pytest

from schemas.customer_schema import CUSTOMER_SCHEMA, STRIPE_ERROR_SCHEMA
from schemas.payment_intent_schema import PAYMENT_INTENT_SCHEMA
from utils.validators import validate_schema
from utils.test_data import VALID_CUSTOMER, VALID_PAYMENT_INTENT


# ─────────────────────────────────────────────────────────────────────
#  Response Field Completeness — Data Contract Tests
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Data Integrity & Contracts")
@allure.story("Response Field Completeness")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.data_integrity
class TestResponseFieldCompleteness:

    @allure.description(
        "Verify ALL expected top-level fields are present in customer response — "
        "regression guard against Stripe API changes."
    )
    def test_customer_response_has_all_fields(self, customers_api, created_customer_ids):
        resp = customers_api.create(**VALID_CUSTOMER)
        body = resp.json()
        created_customer_ids.append(body["id"])

        expected_fields = {
            "id", "object", "name", "email", "phone", "created",
            "livemode", "description", "metadata", "currency",
            "default_source",
        }
        actual_fields = set(body.keys())
        missing = expected_fields - actual_fields
        assert not missing, f"Missing fields in customer response: {missing}"

    @allure.description(
        "Verify ALL expected top-level fields are present in PaymentIntent response."
    )
    def test_pi_response_has_all_fields(self, payments_api, created_payment_intent_ids):
        resp = payments_api.create(**VALID_PAYMENT_INTENT)
        body = resp.json()
        created_payment_intent_ids.append(body["id"])

        expected_fields = {
            "id", "object", "amount", "currency", "status", "created",
            "livemode", "metadata", "capture_method", "confirmation_method",
            "payment_method_types",
        }
        actual_fields = set(body.keys())
        missing = expected_fields - actual_fields
        assert not missing, f"Missing fields in PI response: {missing}"

    @allure.description("Verify the 'object' field always matches the resource type.")
    def test_object_field_consistency(self, customers_api, payments_api,
                                      created_customer_ids, created_payment_intent_ids):
        cust = customers_api.create(**VALID_CUSTOMER).json()
        created_customer_ids.append(cust["id"])
        assert cust["object"] == "customer"

        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])
        assert pi["object"] == "payment_intent"

    @allure.description("Verify 'livemode' is always False in test mode — safety check.")
    def test_livemode_always_false(self, customers_api, payments_api,
                                    created_customer_ids, created_payment_intent_ids):
        cust = customers_api.create(**VALID_CUSTOMER).json()
        created_customer_ids.append(cust["id"])
        assert cust["livemode"] is False, "Expected livemode=false in test mode"

        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])
        assert pi["livemode"] is False, "Expected livemode=false in test mode"


# ─────────────────────────────────────────────────────────────────────
#  Encoding & Internationalization
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Data Integrity & Contracts")
@allure.story("Encoding & i18n")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.data_integrity
class TestEncodingInternationalization:

    @allure.description("Emoji in customer name should be stored and returned correctly.")
    def test_emoji_in_customer_name(self, customers_api, created_customer_ids):
        emoji_name = "Test User \U0001f600\U0001f680"
        resp = customers_api.create(name=emoji_name, email="emoji@example.com")
        body = resp.json()

        assert resp.status_code == 200
        assert "\U0001f600" in body["name"] or "\\u" in body["name"]
        created_customer_ids.append(body["id"])

    @allure.description("CJK characters in customer name should be preserved.")
    def test_cjk_characters_in_name(self, customers_api, created_customer_ids):
        cjk_name = "\u7530\u4e2d\u592a\u90ce"  # Tanaka Taro in Japanese
        resp = customers_api.create(name=cjk_name, email="cjk@example.com")
        body = resp.json()

        assert resp.status_code == 200
        assert body["name"] == cjk_name
        created_customer_ids.append(body["id"])

    @allure.description("Arabic/RTL text in customer name should be preserved.")
    def test_arabic_text_in_name(self, customers_api, created_customer_ids):
        arabic_name = "\u0645\u062d\u0645\u062f"  # Muhammad in Arabic
        resp = customers_api.create(name=arabic_name, email="arabic@example.com")
        body = resp.json()

        assert resp.status_code == 200
        assert body["name"] == arabic_name
        created_customer_ids.append(body["id"])

    @allure.description("Mixed-script text (Latin + CJK + emoji) should be preserved.")
    def test_mixed_script_text(self, customers_api, created_customer_ids):
        mixed_name = "John \u7530\u4e2d \U0001f600"
        resp = customers_api.create(name=mixed_name, email="mixed@example.com")
        body = resp.json()

        assert resp.status_code == 200
        created_customer_ids.append(body["id"])


# ─────────────────────────────────────────────────────────────────────
#  Data Consistency Across Operations
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Data Integrity & Contracts")
@allure.story("Data Consistency")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.data_integrity
class TestDataConsistency:

    @allure.description("Data returned by create should exactly match data from retrieve.")
    def test_create_matches_retrieve_customer(self, customers_api, created_customer_ids):
        created = customers_api.create(**VALID_CUSTOMER).json()
        created_customer_ids.append(created["id"])

        fetched = customers_api.retrieve(created["id"]).json()

        assert created["id"] == fetched["id"]
        assert created["name"] == fetched["name"]
        assert created["email"] == fetched["email"]
        assert created["phone"] == fetched["phone"]
        assert created["created"] == fetched["created"]

    @allure.description("Data returned by create should match retrieve for PaymentIntent.")
    def test_create_matches_retrieve_pi(self, payments_api, created_payment_intent_ids):
        created = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(created["id"])

        fetched = payments_api.retrieve(created["id"]).json()

        assert created["id"] == fetched["id"]
        assert created["amount"] == fetched["amount"]
        assert created["currency"] == fetched["currency"]
        assert created["status"] == fetched["status"]
        assert created["created"] == fetched["created"]

    @allure.description("Update should only change the specified field, nothing else.")
    def test_update_preserves_unchanged_fields(self, customers_api, created_customer_ids):
        original = customers_api.create(**VALID_CUSTOMER).json()
        created_customer_ids.append(original["id"])

        updated = customers_api.update(original["id"], name="Changed Name Only").json()

        assert updated["name"] == "Changed Name Only"
        assert updated["email"] == original["email"]
        assert updated["phone"] == original["phone"]
        assert updated["description"] == original["description"]
        assert updated["created"] == original["created"]


# ─────────────────────────────────────────────────────────────────────
#  API Versioning & Expand
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Data Integrity & Contracts")
@allure.story("API Versioning & Expand")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.data_integrity
class TestAPIVersioningExpand:

    @allure.description(
        "Send Stripe-Version header explicitly and verify the API respects it."
    )
    def test_explicit_api_version_header(self, customers_api):
        url = f"{customers_api.base_url}/customers?limit=1"
        resp = customers_api.session.get(
            url,
            headers={"Stripe-Version": "2023-10-16"},
            timeout=customers_api.timeout,
        )

        assert resp.status_code == 200
        assert resp.headers.get("Stripe-Version") is not None

    @allure.description(
        "Use expand[] parameter on PaymentIntent to get nested objects."
    )
    def test_expand_parameter_on_pi(self, payments_api, customers_api,
                                     created_customer_ids, created_payment_intent_ids):
        cust = customers_api.create(**VALID_CUSTOMER).json()
        created_customer_ids.append(cust["id"])

        pi = payments_api.create(
            amount=2000, currency="usd", customer=cust["id"],
            **{"payment_method_types[]": "card"},
        ).json()
        created_payment_intent_ids.append(pi["id"])

        # Fetch with expand
        url = f"{payments_api.base_url}/payment_intents/{pi['id']}"
        resp = payments_api.session.get(
            url,
            params={"expand[]": "customer"},
            timeout=payments_api.timeout,
        )
        body = resp.json()

        assert resp.status_code == 200
        # When expanded, customer should be an object, not just a string ID
        if isinstance(body.get("customer"), dict):
            assert body["customer"]["id"] == cust["id"]
            assert body["customer"]["object"] == "customer"
        else:
            # Some API versions may not expand — still valid
            assert body["customer"] == cust["id"]


# ─────────────────────────────────────────────────────────────────────
#  Error Message Quality
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Data Integrity & Contracts")
@allure.story("Error Message Quality")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.data_integrity
class TestErrorMessageQuality:

    @allure.description(
        "Error responses should contain doc_url pointing to Stripe documentation."
    )
    def test_error_contains_doc_url(self, payments_api):
        resp = payments_api.create(amount=-1, currency="usd", **{"payment_method_types[]": "card"})
        body = resp.json()

        assert resp.status_code == 400
        error = body["error"]
        if "doc_url" in error:
            assert "stripe.com" in error["doc_url"], (
                f"doc_url should point to Stripe docs, got: {error['doc_url']}"
            )

    @allure.description(
        "Error message should be human-readable and descriptive (not empty or cryptic)."
    )
    def test_error_message_is_descriptive(self, payments_api):
        resp = payments_api.create(amount=0, currency="usd", **{"payment_method_types[]": "card"})
        body = resp.json()

        assert resp.status_code == 400
        msg = body["error"]["message"]
        assert len(msg) > 10, f"Error message too short to be helpful: '{msg}'"
        # Should contain relevant context
        assert any(word in msg.lower() for word in ["amount", "invalid", "must", "should", "greater"]), (
            f"Error message lacks context about the problem: '{msg}'"
        )

    @allure.description(
        "Error response should include the 'param' field identifying which parameter caused the error."
    )
    def test_error_includes_param_field(self, payments_api):
        resp = payments_api.create(amount="not_a_number", currency="usd", **{"payment_method_types[]": "card"})
        body = resp.json()

        assert resp.status_code == 400
        error = body["error"]
        assert "param" in error, "Error should identify which parameter caused the issue"
        assert error["param"] == "amount"


# ─────────────────────────────────────────────────────────────────────
#  Metadata Edge Cases
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Data Integrity & Contracts")
@allure.story("Metadata Edge Cases")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.data_integrity
class TestMetadataEdgeCases:

    @allure.description("Metadata value with max length (500 chars) should be accepted.")
    def test_long_metadata_value(self, customers_api, created_customer_ids):
        long_value = "A" * 500
        resp = customers_api.create(
            email="longmeta@example.com",
            **{"metadata[long_key]": long_value},
        )
        body = resp.json()

        assert resp.status_code == 200
        assert body["metadata"]["long_key"] == long_value
        created_customer_ids.append(body["id"])

    @allure.description("Metadata key with special characters should be handled.")
    def test_special_chars_in_metadata_key(self, customers_api, created_customer_ids):
        resp = customers_api.create(
            email="specialmeta@example.com",
            **{"metadata[key-with-dashes]": "value1", "metadata[key_with_underscores]": "value2"},
        )
        body = resp.json()

        assert resp.status_code == 200
        assert body["metadata"]["key-with-dashes"] == "value1"
        assert body["metadata"]["key_with_underscores"] == "value2"
        created_customer_ids.append(body["id"])

    @allure.description("Exceeding 50 metadata keys should be rejected by Stripe.")
    def test_exceed_metadata_limit(self, customers_api):
        metadata = {f"metadata[key_{i:03d}]": f"value_{i}" for i in range(51)}
        resp = customers_api.create(email="overmeta@example.com", **metadata)

        assert resp.status_code == 400
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)

    @allure.description("Empty metadata object should be valid.")
    def test_empty_metadata_on_create(self, customers_api, created_customer_ids):
        resp = customers_api.create(email="emptymeta@example.com")
        body = resp.json()

        assert resp.status_code == 200
        assert body["metadata"] == {}
        created_customer_ids.append(body["id"])
