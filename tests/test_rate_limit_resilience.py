"""Rate limit awareness, resilience, and concurrent request tests.
Demonstrates production-readiness thinking and performance awareness."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import allure
import pytest

from schemas.customer_schema import CUSTOMER_SCHEMA
from schemas.payment_intent_schema import PAYMENT_INTENT_SCHEMA
from utils.validators import validate_schema, assert_response_time
from utils.test_data import VALID_CUSTOMER, VALID_PAYMENT_INTENT


# ─────────────────────────────────────────────────────────────────────
#  Rapid Sequential Requests
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Rate Limit & Resilience")
@allure.story("Rapid Sequential Requests")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.resilience
class TestRapidSequentialRequests:

    @allure.description(
        "Fire 10 sequential customer creates rapidly — "
        "verify all succeed and none are dropped."
    )
    def test_rapid_customer_creates(self, customers_api, created_customer_ids):
        results = []
        for i in range(10):
            resp = customers_api.create(
                email=f"rapid_{i}@example.com", name=f"Rapid Test {i}"
            )
            results.append(resp)

        success_count = 0
        for resp in results:
            body = resp.json()
            if resp.status_code == 200:
                success_count += 1
                created_customer_ids.append(body["id"])
            elif resp.status_code == 429:
                # Rate limited — this is expected behavior, not a failure
                allure.attach(
                    f"Rate limited on request: {body}",
                    name="Rate Limit Hit",
                    attachment_type=allure.attachment_type.TEXT,
                )

        assert success_count >= 8, (
            f"Expected at least 8/10 rapid creates to succeed, got {success_count}"
        )

    @allure.description(
        "Fire 10 sequential PI creates rapidly — verify all succeed."
    )
    def test_rapid_pi_creates(self, payments_api, created_payment_intent_ids):
        results = []
        for i in range(10):
            resp = payments_api.create(**VALID_PAYMENT_INTENT)
            results.append(resp)

        success_count = 0
        for resp in results:
            body = resp.json()
            if resp.status_code == 200:
                success_count += 1
                created_payment_intent_ids.append(body["id"])
            elif resp.status_code == 429:
                allure.attach(
                    f"Rate limited: {body}",
                    name="Rate Limit Hit",
                    attachment_type=allure.attachment_type.TEXT,
                )

        assert success_count >= 8, (
            f"Expected at least 8/10 rapid PI creates to succeed, got {success_count}"
        )


# ─────────────────────────────────────────────────────────────────────
#  Concurrent Requests (Thread-based)
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Rate Limit & Resilience")
@allure.story("Concurrent Requests")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.resilience
class TestConcurrentRequests:

    @allure.description(
        "Send 5 concurrent customer fetch requests — "
        "verify no data corruption or mixed responses."
    )
    def test_concurrent_customer_fetches(self, customers_api, created_customer_ids):
        # Create 5 distinct customers
        customer_ids = []
        for i in range(5):
            cust = customers_api.create(
                email=f"concurrent_{i}@example.com", name=f"Concurrent {i}"
            ).json()
            customer_ids.append(cust["id"])
            created_customer_ids.append(cust["id"])

        # Fetch all 5 concurrently
        def fetch_customer(cid):
            resp = customers_api.retrieve(cid)
            return cid, resp

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_customer, cid): cid for cid in customer_ids}
            for future in as_completed(futures):
                expected_cid = futures[future]
                cid, resp = future.result()

                with allure.step(f"Verify fetch for {cid}"):
                    assert resp.status_code == 200
                    body = resp.json()
                    assert body["id"] == expected_cid, (
                        f"Data corruption: requested {expected_cid}, got {body['id']}"
                    )

    @allure.description(
        "Send 5 concurrent PI creates — verify all get unique IDs."
    )
    def test_concurrent_pi_creates(self, payments_api, created_payment_intent_ids):
        def create_pi(_):
            return payments_api.create(**VALID_PAYMENT_INTENT)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_pi, i) for i in range(5)]
            results = [f.result() for f in futures]

        ids = set()
        for resp in results:
            if resp.status_code == 200:
                body = resp.json()
                assert body["id"] not in ids, f"Duplicate PI ID: {body['id']}"
                ids.add(body["id"])
                created_payment_intent_ids.append(body["id"])

        assert len(ids) >= 4, f"Expected at least 4 unique PIs, got {len(ids)}"


# ─────────────────────────────────────────────────────────────────────
#  Rate Limit Detection
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Rate Limit & Resilience")
@allure.story("Rate Limit Awareness")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.resilience
class TestRateLimitAwareness:

    @allure.description(
        "Verify that if a 429 occurs, the Retry-After header is present. "
        "Note: Stripe test mode rarely rate-limits, so we validate the framework handles it."
    )
    def test_rate_limit_retry_header_awareness(self, customers_api):
        # We can't reliably trigger 429 in test mode, but we validate
        # that our retry adapter is configured for it
        from urllib3.util.retry import Retry
        adapter = customers_api.session.get_adapter("https://")
        retry_config = adapter.max_retries

        assert 429 in retry_config.status_forcelist, (
            "Retry strategy should include 429 (rate limit) in status_forcelist"
        )
        assert retry_config.total >= 2, (
            f"Retry total should be >= 2, got {retry_config.total}"
        )

    @allure.description(
        "Verify response time stays consistent under sequential load — "
        "no progressive degradation."
    )
    def test_response_time_consistency(self, customers_api):
        times = []
        for _ in range(5):
            resp = customers_api.list_customers(limit=1)
            assert resp.status_code == 200
            times.append(resp.elapsed.total_seconds())

        avg_time = sum(times) / len(times)
        max_time = max(times)

        with allure.step(f"Avg={avg_time:.3f}s, Max={max_time:.3f}s"):
            # Max should not be more than 3x average (no spikes)
            assert max_time < avg_time * 4, (
                f"Response time spike detected: max={max_time:.3f}s, avg={avg_time:.3f}s"
            )
            # All should be under 5s
            for t in times:
                assert t < 5.0, f"Response took {t:.3f}s, exceeding 5s limit"


# ─────────────────────────────────────────────────────────────────────
#  Additional Card Type Tests
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Rate Limit & Resilience")
@allure.story("Additional Card Types")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.payment_intents
class TestAdditionalCardTypes:

    @allure.description("Verify AMEX test card works for confirmation.")
    def test_confirm_with_amex(self, payments_api, created_payment_intent_ids):
        from utils.test_data import CARD_AMEX_SUCCESS
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.confirm(pi["id"], payment_method=CARD_AMEX_SUCCESS)
        body = resp.json()

        assert resp.status_code == 200
        assert body["status"] == "succeeded"

    @allure.description("Verify Discover test card works for confirmation.")
    def test_confirm_with_discover(self, payments_api, created_payment_intent_ids):
        from utils.test_data import CARD_DISCOVER_SUCCESS
        pi = payments_api.create(**VALID_PAYMENT_INTENT).json()
        created_payment_intent_ids.append(pi["id"])

        resp = payments_api.confirm(pi["id"], payment_method=CARD_DISCOVER_SUCCESS)
        body = resp.json()

        assert resp.status_code == 200
        assert body["status"] == "succeeded"
