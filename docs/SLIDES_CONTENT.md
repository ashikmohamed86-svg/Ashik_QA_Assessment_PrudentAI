# Slide Deck Content — QA Assessment Presentation

> Copy this content into Google Slides, Keynote, or PowerPoint.
> Suggested theme: Dark background, clean sans-serif font.

---

## Slide 1: Title

**Stripe API Test Automation Framework**
QA Assessment — PrudentAI

Ashik | February 2026

---

## Slide 2: What This Framework Does

- Automated integration tests against Stripe's **live test-mode API**
- Covers **Customers API**, **PaymentIntents API**, and **Refunds API**
- No mocks — every test makes real HTTP calls
- Built with **Python + PyTest** — industry-standard tooling

---

## Slide 3: By The Numbers

| Metric | Value |
|--------|-------|
| Total Tests | **236** |
| Test Modules | **9** |
| Test Classes | **64+** |
| API Endpoints Covered | **15+** |
| Pass Rate | **100%** |
| Avg Run Time | **~2 minutes** (parallel) |

---

## Slide 4: Test Coverage Map

```
Customers API          (47 tests)  ████████████████████░
Payment Intents API    (70 tests)  ██████████████████████████████████░
Negative Validation    (26 tests)  ████████████░
Security               (22 tests)  ██████████░
Refunds API            (21 tests)  █████████░
Data Integrity         (20 tests)  █████████░
Cross-Resource         (12 tests)  █████░
Auth & Headers         (10 tests)  ████░
Rate Limit/Resilience   (8 tests)  ███░
```

---

## Slide 5: Framework Architecture

```
┌─────────────────────────────────────────────┐
│                  Tests Layer                 │
│  test_customers    test_payment_intents      │
│  test_refunds      test_security             │
│  test_cross_resource  test_data_integrity    │
│  test_auth_headers  test_rate_limit          │
│  test_negative_validation                    │
├─────────────────────────────────────────────┤
│              Utilities Layer                 │
│  validators.py    test_data.py               │
│  schemas/         conftest.py                │
├─────────────────────────────────────────────┤
│             API Client Layer                 │
│  base_client.py (auth, retry, logging)       │
│  customers.py  payment_intents.py  refunds.py│
├─────────────────────────────────────────────┤
│           Stripe Test-Mode API               │
└─────────────────────────────────────────────┘
```

---

## Slide 6: What Makes This Stand Out

**1. Security Testing (22 tests)**
- SQL injection, XSS, path traversal, null bytes in both Customers & PIs
- Security header validation (HSTS, Cache-Control)
- HTTP method validation (PUT/PATCH/DELETE/HEAD/OPTIONS)
- Idempotency abuse detection

**2. Card Validation & Charge Verification (14 tests)**
- 8 decline scenarios: expired, insufficient funds, CVC, stolen, lost, fraud/radar
- Charge object verification after payment (latest_charge, receipt_url)
- Payment method details (card brand, last4, expiry)
- Manual capture charge state verification

**3. Cross-Resource Testing (12 tests)**
- Customer + PaymentIntent + Refund interactions
- Deleted resource edge cases
- Multi-currency E2E flow
- Metadata independence verification

**4. Production-Quality Infrastructure**
- Auto-retry (2 retries, 1s delay)
- Session-scoped cleanup
- JSON Schema validation on every response
- Custom HTML report with API call capture

---

## Slide 7: Security Tests — Why They Matter

| Attack Vector | Test | Result |
|--------------|------|--------|
| SQL Injection | `'; DROP TABLE customers;--` in name & PI description | Stored literally, not executed |
| XSS | `<script>alert('xss')</script>` in name & metadata | Stored as text, not rendered |
| Path Traversal | `../../etc/passwd` as resource ID | 404, no file exposure |
| Null Byte | `test\x00name` in name | Safely handled |
| Idempotency Abuse | Same key different payload; long key; empty key | Conflict detected or handled |

> These tests demonstrate awareness of OWASP API Security Top 10.

---

## Slide 8: Cross-Resource & Refund Edge Cases

| Scenario | Expected | Verified |
|----------|----------|----------|
| PI for deleted customer | Error | 400 |
| Delete customer with active PI | PI survives | PI fetchable |
| Cancel PI | Customer unchanged | Name/email intact |
| Full refund E2E with customer | Customer unaffected | Verified |
| Multi-currency (USD/EUR/GBP/JPY) | All succeed | Confirmed |
| Cancel already-canceled PI | Error | 400 |
| Double full refund | Error | 400 |
| Partial → remaining → over-refund | Third fails | 400 |

> These show **system-level thinking**, not just endpoint testing.

---

## Slide 9: Data Integrity & Resilience

**Data Integrity (20 tests)**
- Emoji, CJK, Arabic, mixed-script internationalization
- Create-then-retrieve consistency
- Error message quality (type, message, param)
- Metadata edge cases (empty, long, many keys, special chars)
- API versioning and expand[] parameter

**Resilience (8 tests)**
- 10+ rapid sequential requests
- 5 concurrent creates (ThreadPoolExecutor)
- Rate limit awareness (429 handling)
- Multiple card types (Visa, MC, AMEX, Discover)

---

## Slide 10: Custom HTML Report

- **Dashboard**: Pass rate donut chart, module summary cards
- **9 module sections**: Each with its own pass rate and progress bar
- **Per-test drill-down**: Expandable sections with test details
- **API Call Capture**: Every HTTP request/response logged per test
  - Method, URL, request payload
  - Status code, response time, response body
- **Auto-opens** in browser after test run

---

## Slide 11: Key Design Decisions

| Decision | Why |
|----------|-----|
| Real API (no mocks) | True integration confidence |
| Session-scoped fixtures | Efficient cleanup, no orphaned data |
| JSON Schema validation | Contract testing, not just status codes |
| Defensive assertions | Handle Stripe behavior variations |
| 5-second performance gates | SLA-aware testing |
| Custom markers | Targeted CI/CD runs (smoke, security, e2e, refunds) |
| Auto-retry with backoff | Handles transient network/rate-limit issues |
| Parallel execution (xdist) | 3x faster — ~2min vs ~6min sequential |

---

## Slide 12: CI/CD Ready

```yaml
# Run smoke tests on every commit
python -m pytest -m smoke -v

# Run security tests in security pipeline
python -m pytest -m security -v

# Run refund tests after payment changes
python -m pytest -m refunds -v

# Run full suite nightly
python -m pytest -v --tb=short

# Run E2E tests before release
python -m pytest -m e2e -v
```

Parallel execution (`-n auto`) reduces full suite from 6min to ~2min.

---

## Slide 13: Summary

- **236 tests** across **9 modules** — all passing
- **3 APIs covered** — Customers, PaymentIntents, Refunds
- **Security-aware** — injection, headers, method validation, CORS
- **Cross-resource** — system-level integration & refund E2E tests
- **Data integrity** — internationalization, consistency, error quality
- **Resilient** — concurrent requests, rate limiting, multi-card
- **Production-quality** — retry, cleanup, schema validation, custom reporting
- **Extensible** — easy to add new resources or test categories

> Built to demonstrate thoroughness, security awareness, and QA Lead-level thinking.

---

## Slide 14: Live Demo

> Switch to terminal for live test run

```bash
source .venv/bin/activate
python -m pytest -v --tb=short
```

> Then show the custom HTML report
