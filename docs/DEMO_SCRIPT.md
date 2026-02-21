# Demo Script — QA Assessment Walkthrough

> Use this script while screen-recording your demo. Estimated recording time: 10–12 minutes.

---

## SLIDE 1 — Title (Show README or project in IDE)

**SAY:**
> "Hi, I'm Ashik. This is my QA Assessment for PrudentAI — a comprehensive API test automation framework for Stripe's Customers, PaymentIntents, and Refunds APIs. Let me walk you through the architecture, test coverage, and a live test run."

**DO:** Show the project folder structure in your IDE.

---

## SLIDE 2 — Framework Architecture (30 seconds)

**SAY:**
> "The framework follows a layered architecture:
> - **API Client layer** — reusable wrappers for each Stripe resource (Customers, PaymentIntents, Refunds) with built-in retry logic, logging, and idempotency support.
> - **Schema layer** — JSON Schema validation for every API response.
> - **Utilities** — validators for email, phone, currency, response time, and security headers.
> - **Tests** — organized by resource, concern, and risk level across 9 test modules."

**DO:** Quickly expand each folder in the IDE:
1. `api_client/` → show `base_client.py`, `customers.py`, `payment_intents.py`, `refunds.py`
2. `schemas/` → show the schema files
3. `utils/` → show `validators.py`, `test_data.py`
4. `tests/` → show all 9 test files

---

## SLIDE 3 — Test Coverage Overview (45 seconds)

**SAY:**
> "We have **236 tests** across **9 modules**, covering:
> - **Customers API** (47 tests) — Full CRUD, pagination, search, metadata, boundary values
> - **PaymentIntents API** (70 tests) — Create, confirm, capture lifecycle, zero-decimal currencies, list, search, update, cancellation reasons, charge & receipt verification
> - **Refunds API** (21 tests) — Full refund, partial, lifecycle, reason codes, metadata, idempotency
> - **Security** (22 tests) — Injection payloads (SQL, XSS, path traversal), security headers, HTTP method validation, content negotiation, idempotency edge cases
> - **Cross-Resource Integration** (12 tests) — Customer-to-PaymentIntent interactions, lifecycle tests, refund E2E, multi-currency
> - **Data Integrity** (20 tests) — Encoding, internationalization, error quality, metadata edge cases
> - **Auth & Headers** (10 tests) — Authentication enforcement, auth format variations, encoding
> - **Rate Limit & Resilience** (8 tests) — Concurrent requests, rapid-fire, card type variety
> - **Negative Validation** (26 tests) — Error handling, invalid inputs, 8 decline scenarios (expired, insufficient, CVC, stolen, lost, fraud/radar)"

**DO:** Show `pytest.ini` to highlight the markers.

---

## SLIDE 4 — Live Test Run (2–3 minutes)

**SAY:**
> "Let me run the full test suite live."

**DO:** Open terminal and run:

```bash
source .venv/bin/activate
python -m pytest -v --tb=short
```

**WHILE TESTS RUN, SAY:**
> "Notice a few things:
> - Each test has clear naming — you can tell what it validates just from the name.
> - Tests are grouped by class — each class maps to a specific feature or concern.
> - We're hitting the real Stripe test-mode API, not mocks, so these are true integration tests.
> - The framework includes auto-retry (2 retries with 1-second delay) for flaky network issues.
> - Tests run in parallel across multiple CPU cores using pytest-xdist for fast feedback.
> - Session-scoped fixtures automatically clean up all created resources after the run."

**WHEN DONE, SAY:**
> "All 236 tests passed in under 2 minutes — that's because we run them in parallel across multiple workers using pytest-xdist. The custom HTML report just opened — let me show you that."

---

## SLIDE 5 — Custom HTML Report (1 minute)

**SAY:**
> "This is our custom-built test report. At the top you see:
> - Pass rate donut chart
> - Total tests, passed, failed, skipped counts
> - Duration and platform info
>
> Below that, module summary cards show each of the 9 test areas with its own pass rate and progress bar.
>
> Each module section is expandable. Let me click into the Security module..."

**DO:** Click to expand a module section, then click "Details" on a test to show the API call panel.

**SAY:**
> "Every test captures the actual API calls made — the HTTP method, URL, request payload, response body, and response time. This makes debugging failures trivial."

---

## SLIDE 6 — Security Tests Deep Dive (1 minute)

**SAY:**
> "Let me highlight the security tests — this is what I think sets this assessment apart.
>
> We test **8 injection types**: SQL injection in both customers and PIs, XSS in names and metadata, path traversal, null bytes, and HTML entity injection. We verify the API stores these safely without executing them.
>
> We validate **security headers**: HSTS, Cache-Control, X-Content-Type-Options, and Stripe-Version.
>
> We test **HTTP method validation** — PUT, PATCH, DELETE, HEAD, and OPTIONS to endpoints that shouldn't support them.
>
> And we test **idempotency edge cases** — what happens with reused keys, very long keys, and empty keys."

**DO:** Show `tests/test_security.py` in the IDE, scrolling through the test classes.

---

## SLIDE 7 — Cross-Resource & Refunds (45 seconds)

**SAY:**
> "The cross-resource tests show system-level thinking.
>
> For example: What happens when you create a PaymentIntent for a deleted customer? Does deleting a customer break their existing PaymentIntents? Are metadata isolated between resources?
>
> We also have full lifecycle tests and a complete refund E2E flow — customer creation through to refund, verifying the customer is unaffected.
>
> The multi-currency test creates PIs in USD, EUR, GBP, and JPY for the same customer, confirming each one."

**DO:** Show `tests/test_cross_resource.py` and `tests/test_refunds.py` in the IDE.

---

## SLIDE 8 — Data Integrity & Resilience (45 seconds)

**SAY:**
> "The data integrity module tests things evaluators often look for:
>
> - **Internationalization**: emoji, CJK, Arabic, and mixed-script text in customer names
> - **Response consistency**: create-then-retrieve matches, update-then-retrieve matches
> - **Error message quality**: machine-readable types, human-readable messages, param identification
> - **Metadata edge cases**: empty values, long values, many keys, special characters
>
> The resilience module tests concurrent requests, rapid-fire sequences, and multiple card types (Visa, Mastercard, AMEX, Discover)."

**DO:** Show `tests/test_data_integrity.py` briefly.

---

## SLIDE 9 — Key Design Decisions (45 seconds)

**SAY:**
> "A few key design decisions worth noting:
>
> 1. **Real API testing** — No mocks. Every test hits Stripe's test-mode API for true integration confidence.
>
> 2. **Automatic cleanup** — Session-scoped fixtures collect all created resource IDs and clean them up after the run.
>
> 3. **Schema validation everywhere** — Every response is validated against JSON Schema, not just status codes.
>
> 4. **Defensive assertions** — Where Stripe behavior might vary (like accepting weird inputs), tests handle both possible outcomes instead of making assumptions.
>
> 5. **Performance gates** — Every endpoint is validated against a 5-second response time threshold."

---

## SLIDE 10 — Running Specific Test Subsets (30 seconds)

**DO:** Run these commands one at a time:

```bash
# Run only security tests
python -m pytest -m security -v --tb=short

# Run only refund tests
python -m pytest -m refunds -v --tb=short

# Run a single test file
python -m pytest tests/test_cross_resource.py -v --tb=short
```

**SAY:**
> "The framework supports targeted test runs using pytest markers. This is useful in CI/CD — you might run smoke tests on every commit, security tests in a security pipeline, and the full suite nightly."

---

## SLIDE 11 — Closing (15 seconds)

**SAY:**
> "To summarize: 236 tests, 9 modules, covering positive flows, negative validation, security, cross-resource integration, refunds, data integrity, resilience, performance, and end-to-end scenarios — all with a custom HTML report that captures every API call. Thank you for reviewing."

---

## Quick Reference — Terminal Commands for Demo

```bash
# Activate environment
source .venv/bin/activate

# Full parallel test run (this is the main one — ~2 min)
python -m pytest -v --tb=short

# Sequential run (for debugging)
python -m pytest -n 0 -v --tb=short

# Security tests only
python -m pytest -m security -v

# Cross-resource tests only
python -m pytest -m cross_resource -v

# Refund tests only
python -m pytest -m refunds -v

# Data integrity tests only
python -m pytest -m data_integrity -v

# Smoke tests only
python -m pytest -m smoke -v

# Customer tests only
python -m pytest -m customers -v

# E2E tests only
python -m pytest -m e2e -v

# Negative validation tests only
python -m pytest -m negative -v

# Count tests without running
python -m pytest --collect-only -q
```

---

## Tips for Recording

1. **Font size**: Increase terminal font to 16–18pt so it's readable
2. **IDE**: Use a dark theme with good contrast
3. **Speed**: Don't rush — pause briefly between sections
4. **Browser**: Have the custom report ready to show (it auto-opens after test run)
5. **Errors**: If a test fails due to network issues, mention the auto-retry feature
6. **Duration**: Aim for 10–12 minutes total
