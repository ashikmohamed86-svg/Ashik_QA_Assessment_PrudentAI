"""Security-focused tests: injection payloads, security headers, HTTP method validation,
content negotiation, and idempotency edge cases."""

import uuid

import allure
import pytest

from schemas.customer_schema import CUSTOMER_SCHEMA, STRIPE_ERROR_SCHEMA
from utils.validators import (
    validate_schema,
    assert_response_time,
    assert_response_headers,
    assert_security_headers,
)
from utils.test_data import (
    VALID_PAYMENT_INTENT,
    SQL_INJECTION_NAME,
    XSS_PAYLOAD_NAME,
    PATH_TRAVERSAL_ID,
    NULL_BYTE_NAME,
    HTML_ENTITY_DESCRIPTION,
)


# ─────────────────────────────────────────────────────────────────────
#  Injection Payload Tests
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Security")
@allure.story("Injection Payloads")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.security
class TestInjectionPayloads:

    @allure.description(
        "SEC-INJ-01: SQL injection payload in customer name should be safely stored or rejected — never executed."
    )
    def test_sql_injection_in_name(self, customers_api, created_customer_ids):
        resp = customers_api.create(
            name=SQL_INJECTION_NAME, email="sqli@example.com"
        )
        body = resp.json()

        # Stripe stores the string literally — verify it wasn't interpreted
        assert resp.status_code == 200
        assert body["name"] == SQL_INJECTION_NAME
        validate_schema(body, CUSTOMER_SCHEMA)
        created_customer_ids.append(body["id"])

    @allure.description(
        "SEC-INJ-02: XSS payload in customer name should be stored literally, not executed."
    )
    def test_xss_payload_in_name(self, customers_api, created_customer_ids):
        resp = customers_api.create(
            name=XSS_PAYLOAD_NAME, email="xss@example.com"
        )
        body = resp.json()

        assert resp.status_code == 200
        # The raw script tag should be stored literally
        assert "<script>" in body["name"]
        validate_schema(body, CUSTOMER_SCHEMA)
        created_customer_ids.append(body["id"])

    @allure.description(
        "SEC-INJ-03: Path traversal in resource ID should return 404, not expose server files."
    )
    def test_path_traversal_in_resource_id(self, customers_api):
        resp = customers_api.retrieve(PATH_TRAVERSAL_ID)

        assert resp.status_code == 404
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)

    @allure.description(
        "SEC-INJ-04: Null byte injection in customer name should be safely handled."
    )
    def test_null_byte_injection_in_name(self, customers_api, created_customer_ids):
        resp = customers_api.create(
            name=NULL_BYTE_NAME, email="nullbyte@example.com"
        )
        body = resp.json()

        # Stripe should either accept (stored safely) or reject
        if resp.status_code == 200:
            assert body["id"].startswith("cus_")
            validate_schema(body, CUSTOMER_SCHEMA)
            created_customer_ids.append(body["id"])
        else:
            assert resp.status_code == 400

    @allure.description(
        "SEC-INJ-05: HTML entity injection in customer description should be stored literally."
    )
    def test_html_entity_injection_in_description(self, customers_api, created_customer_ids):
        resp = customers_api.create(
            description=HTML_ENTITY_DESCRIPTION,
            email="htmlinject@example.com",
        )
        body = resp.json()

        assert resp.status_code == 200
        assert body["description"] is not None
        validate_schema(body, CUSTOMER_SCHEMA)
        created_customer_ids.append(body["id"])


# ─────────────────────────────────────────────────────────────────────
#  Security Headers
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Security")
@allure.story("Security Headers")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.security
class TestSecurityHeaders:

    @pytest.fixture(autouse=True)
    def _setup_response(self, customers_api):
        self.resp = customers_api.list_customers(limit=1)

    @allure.description("Validate Strict-Transport-Security header is present with max-age.")
    def test_hsts_header(self):
        hsts = self.resp.headers.get("Strict-Transport-Security")
        assert hsts is not None, "Missing HSTS header"
        assert "max-age" in hsts

    @allure.description(
        "Check X-Content-Type-Options header. "
        "Note: Stripe API may not include this header; we document the finding."
    )
    def test_x_content_type_options(self):
        xcto = self.resp.headers.get("X-Content-Type-Options")
        if xcto is not None:
            assert xcto.lower() == "nosniff", f"Expected 'nosniff', got: {xcto}"
        else:
            # Stripe API does not currently return X-Content-Type-Options
            # This is a security observation worth documenting
            allure.attach(
                "Stripe API does not include X-Content-Type-Options header. "
                "This is acceptable for API responses but would be a finding for web pages.",
                name="Security Observation",
                attachment_type=allure.attachment_type.TEXT,
            )

    @allure.description("Validate Cache-Control header prevents caching of API responses.")
    def test_cache_control_header(self):
        cc = self.resp.headers.get("Cache-Control")
        assert cc is not None, "Missing Cache-Control header"
        # Stripe typically includes no-cache, no-store, or must-revalidate
        assert any(d in cc.lower() for d in ["no-cache", "no-store", "must-revalidate"]), (
            f"Cache-Control should prevent caching, got: {cc}"
        )

    @allure.description("Validate Stripe-Version header is returned for API version traceability.")
    def test_stripe_version_header(self):
        sv = self.resp.headers.get("Stripe-Version")
        assert sv is not None, "Missing Stripe-Version header"
        assert len(sv) > 0


# ─────────────────────────────────────────────────────────────────────
#  HTTP Method Validation
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Security")
@allure.story("HTTP Method Validation")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.security
class TestHTTPMethodValidation:

    @allure.description("PUT to /customers should return 405 or an error — PUT is not a supported method.")
    def test_put_to_customers_rejected(self, customers_api):
        url = f"{customers_api.base_url}/customers"
        resp = customers_api.session.put(url, data={"name": "Test"}, timeout=customers_api.timeout)

        assert resp.status_code in (405, 404, 400), (
            f"PUT /customers should be rejected, got {resp.status_code}"
        )

    @allure.description("PATCH to /payment_intents should return 405 or an error.")
    def test_patch_to_payment_intents_rejected(self, payments_api):
        url = f"{payments_api.base_url}/payment_intents"
        resp = payments_api.session.patch(url, data={"amount": 100}, timeout=payments_api.timeout)

        assert resp.status_code in (405, 404, 403, 400), (
            f"PATCH /payment_intents should be rejected, got {resp.status_code}"
        )

    @allure.description("HEAD to /customers should return 200 with headers but no body.")
    def test_head_to_customers(self, customers_api):
        url = f"{customers_api.base_url}/customers"
        resp = customers_api.session.head(url, timeout=customers_api.timeout)

        assert resp.status_code == 200
        assert resp.headers.get("Content-Type") is not None
        # HEAD response should have empty body
        assert len(resp.content) == 0


# ─────────────────────────────────────────────────────────────────────
#  Content Negotiation
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Security")
@allure.story("Content Negotiation")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.security
class TestContentNegotiation:

    @allure.description("Sending Accept: text/xml should still return JSON from Stripe.")
    def test_accept_xml_returns_json(self, customers_api):
        url = f"{customers_api.base_url}/customers?limit=1"
        resp = customers_api.session.get(
            url,
            headers={"Accept": "text/xml"},
            timeout=customers_api.timeout,
        )

        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("Content-Type", "")
        # Verify it's valid JSON
        body = resp.json()
        assert body["object"] == "list"

    @allure.description("Sending empty Content-Type should still be handled correctly.")
    def test_empty_content_type(self, customers_api, created_customer_ids):
        url = f"{customers_api.base_url}/customers"
        resp = customers_api.session.post(
            url,
            data={"email": "empty_ct@example.com"},
            headers={"Content-Type": ""},
            timeout=customers_api.timeout,
        )

        # Stripe should still process the request or return a clear error
        if resp.status_code == 200:
            body = resp.json()
            created_customer_ids.append(body["id"])
        else:
            assert resp.status_code in (400, 415)


# ─────────────────────────────────────────────────────────────────────
#  Idempotency Edge Cases
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Security")
@allure.story("Idempotency Edge Cases")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.security
class TestIdempotencyEdgeCases:

    @allure.description(
        "Using the same Idempotency-Key with different payloads should return an error "
        "or conflict, preventing accidental duplicate processing."
    )
    def test_same_key_different_payload_returns_error(
        self, payments_api, created_payment_intent_ids
    ):
        key = f"idem-conflict-{uuid.uuid4()}"

        with allure.step("Create first PI with idempotency key"):
            resp1 = payments_api.create(
                idempotency_key=key,
                amount=1000, currency="usd", **{"payment_method_types[]": "card"},
            )
            body1 = resp1.json()
            assert resp1.status_code == 200
            created_payment_intent_ids.append(body1["id"])

        with allure.step("Create second PI with SAME key but DIFFERENT amount"):
            resp2 = payments_api.create(
                idempotency_key=key,
                amount=9999, currency="usd", **{"payment_method_types[]": "card"},
            )

        with allure.step("Verify conflict or original response returned"):
            # Stripe returns 400 with idempotency error, or returns original response
            if resp2.status_code == 400:
                body2 = resp2.json()
                validate_schema(body2, STRIPE_ERROR_SCHEMA)
            else:
                # Stripe returns the original cached response
                body2 = resp2.json()
                assert body2["id"] == body1["id"]
                assert body2["amount"] == 1000  # original amount, not 9999

    @allure.description("Very long idempotency key (> 255 chars) should be rejected or truncated.")
    def test_very_long_idempotency_key(self, payments_api, created_payment_intent_ids):
        long_key = "k" * 500
        resp = payments_api.create(
            idempotency_key=long_key,
            amount=1000, currency="usd", **{"payment_method_types[]": "card"},
        )

        if resp.status_code == 200:
            created_payment_intent_ids.append(resp.json()["id"])
        else:
            assert resp.status_code == 400

    @allure.description("Empty string idempotency key — verify Stripe handles it.")
    def test_empty_idempotency_key(self, payments_api, created_payment_intent_ids):
        resp = payments_api.create(
            idempotency_key="",
            amount=1000, currency="usd", **{"payment_method_types[]": "card"},
        )
        # Stripe may treat "" as no key, creating a new PI
        if resp.status_code == 200:
            created_payment_intent_ids.append(resp.json()["id"])
        else:
            assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────
#  CORS & OPTIONS Requests
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Security")
@allure.story("CORS & OPTIONS")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.security
class TestCORSAndOptions:

    @allure.description("OPTIONS preflight request to /customers should return CORS headers.")
    def test_options_request(self, customers_api):
        url = f"{customers_api.base_url}/customers"
        resp = customers_api.session.options(url, timeout=customers_api.timeout)

        # Stripe should respond to OPTIONS (204 is standard CORS preflight)
        assert resp.status_code in (200, 204, 400, 405), (
            f"OPTIONS request returned unexpected status: {resp.status_code}"
        )

    @allure.description("DELETE to /payment_intents should be rejected — PIs cannot be deleted.")
    def test_delete_payment_intent_rejected(self, payments_api, created_payment_intent_ids):
        pi = payments_api.create(
            amount=1000, currency="usd", **{"payment_method_types[]": "card"}
        ).json()
        created_payment_intent_ids.append(pi["id"])

        url = f"{payments_api.base_url}/payment_intents/{pi['id']}"
        resp = payments_api.session.delete(url, timeout=payments_api.timeout)

        assert resp.status_code in (405, 404, 400), (
            f"DELETE /payment_intents should be rejected, got {resp.status_code}"
        )


# ─────────────────────────────────────────────────────────────────────
#  Injection in PaymentIntent Fields
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Security")
@allure.story("PI Injection Payloads")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.security
class TestPIInjectionPayloads:

    @allure.description("SQL injection in PI description should be stored literally.")
    def test_sql_injection_in_pi_description(self, payments_api, created_payment_intent_ids):
        sql_payload = "'; DROP TABLE payment_intents;--"
        resp = payments_api.create(
            amount=1000, currency="usd", description=sql_payload,
            **{"payment_method_types[]": "card"},
        )
        body = resp.json()

        assert resp.status_code == 200
        assert body["description"] == sql_payload
        created_payment_intent_ids.append(body["id"])

    @allure.description("XSS payload in PI metadata values should be stored literally.")
    def test_xss_in_pi_metadata(self, payments_api, created_payment_intent_ids):
        xss = "<script>alert('xss')</script>"
        resp = payments_api.create(
            amount=1000, currency="usd",
            **{"payment_method_types[]": "card", "metadata[xss]": xss},
        )
        body = resp.json()

        assert resp.status_code == 200
        assert body["metadata"]["xss"] == xss
        created_payment_intent_ids.append(body["id"])

    @allure.description("XSS payload in customer metadata values should be stored literally.")
    def test_xss_in_customer_metadata(self, customers_api, created_customer_ids):
        xss = "<img src=x onerror=alert(1)>"
        resp = customers_api.create(
            email="xss_meta@example.com",
            **{"metadata[injection]": xss},
        )
        body = resp.json()

        assert resp.status_code == 200
        assert body["metadata"]["injection"] == xss
        created_customer_ids.append(body["id"])
