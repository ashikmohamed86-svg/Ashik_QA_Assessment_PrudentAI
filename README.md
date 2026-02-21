# Stripe API Test Automation Framework

Comprehensive API test automation framework for Stripe's **Customers**, **PaymentIntents**, and **Refunds** APIs. Built with **Python + PyTest**, featuring **236 tests** across **9 modules** — covering CRUD operations, payment lifecycles, security testing, cross-resource integration, data integrity, and resilience.

All tests hit Stripe's **live test-mode API** — no mocks. Every response is validated against JSON Schema contracts.

---

## Project Structure

```
Ashik_QA_Assessment_PrudentAI/
├── api_client/                        # API client layer
│   ├── base_client.py                 # Session, auth, retry, logging, idempotency
│   ├── customers.py                   # /customers resource
│   ├── payment_intents.py             # /payment_intents resource
│   └── refunds.py                     # /refunds resource
├── config/
│   └── settings.py                    # Environment & config management
├── schemas/
│   ├── customer_schema.py             # JSON Schema for Customer + error responses
│   ├── payment_intent_schema.py       # JSON Schema for PaymentIntent + cancel
│   └── refund_schema.py               # JSON Schema for Refund responses
├── utils/
│   ├── validators.py                  # Schema, email, phone, currency, headers, security validators
│   └── test_data.py                   # Test payloads & Stripe test-card tokens
├── tests/
│   ├── test_customers.py              # Customer CRUD, pagination, search, metadata, boundary
│   ├── test_payment_intents.py        # PI lifecycle, currencies, list, search, charge verification
│   ├── test_refunds.py                # Full/partial refund, lifecycle, reason codes, idempotency
│   ├── test_negative_validation.py    # Error handling, invalid inputs, 8 decline scenarios
│   ├── test_security.py               # Injection, headers, HTTP methods, idempotency abuse
│   ├── test_cross_resource.py         # Customer↔PI↔Refund interactions, E2E flows
│   ├── test_data_integrity.py         # Encoding, i18n, consistency, error quality, metadata
│   ├── test_auth_headers.py           # Authentication enforcement & format variations
│   └── test_rate_limit_resilience.py  # Concurrent requests, rapid-fire, multi-card
├── docs/
│   ├── TEST_CASES.md                  # Detailed test-case documentation (236 tests)
│   ├── DEMO_SCRIPT.md                 # Screen recording walkthrough script
│   └── SLIDES_CONTENT.md             # Presentation slide content
├── .github/workflows/
│   └── test.yml                       # GitHub Actions CI pipeline
├── conftest.py                        # Fixtures, cleanup, custom HTML report, xdist support
├── pytest.ini                         # PyTest configuration & markers
├── requirements.txt                   # Python dependencies
└── .env.example                       # Environment variable template
```

## Test Coverage — 236 Tests

| Module | Tests | What It Covers |
|--------|------:|----------------|
| **Customers API** | 47 | Full CRUD, pagination, search, metadata, boundary values |
| **PaymentIntents API** | 70 | Create, confirm, capture lifecycle, zero-decimal currencies, list, search, update, cancellation reasons, charge & receipt verification |
| **Negative Validation** | 26 | Error handling, invalid inputs, 8 decline scenarios (expired, insufficient, CVC, stolen, lost, fraud/radar) |
| **Security** | 22 | SQL injection, XSS, path traversal, null bytes, security headers, HTTP method validation, idempotency abuse |
| **Refunds API** | 21 | Full refund, partial, lifecycle, reason codes, metadata, idempotency |
| **Data Integrity** | 20 | Encoding, i18n (emoji, CJK, Arabic), consistency, error quality, metadata edge cases |
| **Cross-Resource** | 12 | Customer↔PI interactions, deleted resource edges, multi-currency E2E, refund E2E |
| **Auth & Headers** | 10 | Authentication enforcement, auth format variations, encoding |
| **Rate Limit & Resilience** | 8 | Concurrent requests, rapid-fire, rate limit handling, multi-card |

## Prerequisites

- **Python 3.10+**
- A **Stripe test-mode secret key** (starts with `sk_test_...` or `rk_test_...`). Get one from the [Stripe Dashboard → Developers → API keys](https://dashboard.stripe.com/test/apikeys).

## Setup

```bash
# 1. Clone the repository
git clone <repo-url> && cd Ashik_QA_Assessment_PrudentAI

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your Stripe test key
cp .env.example .env
# Edit .env and set STRIPE_TEST_SECRET_KEY=sk_test_...
```

## Running Tests

```bash
# Full suite — parallel execution (~2 minutes)
python -m pytest

# Sequential run (for debugging)
python -m pytest -n 0

# Debug logging (full request/response bodies)
python -m pytest -n 0 --log-cli-level=DEBUG
```

### Run by Category

```bash
python -m pytest -m smoke              # Quick sanity checks
python -m pytest -m customers          # Customer API tests
python -m pytest -m payment_intents    # PaymentIntent API tests
python -m pytest -m refunds            # Refund API tests
python -m pytest -m security           # Security tests
python -m pytest -m cross_resource     # Cross-resource integration
python -m pytest -m data_integrity     # Data contract & encoding
python -m pytest -m negative           # Negative validation & declines
python -m pytest -m resilience         # Rate limit & resilience
python -m pytest -m e2e                # End-to-end flows
```

### Available Markers

| Marker | Description |
|--------|-------------|
| `smoke` | Quick sanity checks for create endpoints |
| `customers` | All Customer API tests |
| `payment_intents` | All PaymentIntent API tests |
| `refunds` | All Refund API tests |
| `negative` | Negative and input-validation tests |
| `e2e` | End-to-end payment flow tests |
| `security` | Injection, headers, HTTP methods, idempotency abuse |
| `cross_resource` | Cross-resource integration tests |
| `data_integrity` | Data contract, encoding, and consistency tests |
| `resilience` | Rate limit and resilience tests |

## Framework Architecture

```
┌─────────────────────────────────────────────────┐
│                   Tests Layer                    │
│  9 modules · 64+ test classes · 236 tests       │
├─────────────────────────────────────────────────┤
│                Utilities Layer                   │
│  validators.py · test_data.py · schemas/        │
├─────────────────────────────────────────────────┤
│               API Client Layer                   │
│  base_client.py (auth, retry, logging)           │
│  customers.py · payment_intents.py · refunds.py  │
├─────────────────────────────────────────────────┤
│             Stripe Test-Mode API                 │
└─────────────────────────────────────────────────┘
```

### API Client Layer

`BaseAPIClient` wraps `requests.Session` with:
- Automatic Bearer-token auth injection
- Base URL management
- Request/response debug logging (full payload at DEBUG level, warnings on 4xx/5xx)
- Automatic retry with backoff (2 retries, 1-second delay for 429/5xx)
- Idempotency-Key header support for safe retries

Resource clients (`CustomersAPI`, `PaymentIntentsAPI`, `RefundsAPI`) expose clean methods for each endpoint — create, retrieve, update, delete, list, confirm, capture, cancel, search.

### Config Management

All config is read from environment variables (or `.env` via `python-dotenv`). A startup validation check ensures the key exists and uses the test-mode prefix.

### Data Validation

- **JSON Schema** validation (`jsonschema`) verifies every response against strict schemas
- Dedicated validators for email (RFC-5322), phone (E.164), ISO 4217 currencies, response time, response headers, and security headers (HSTS, Cache-Control, X-Content-Type-Options)

### Test Infrastructure

- **Parallel execution** — `pytest-xdist` runs tests across multiple CPU cores (~2 min vs ~6 min sequential)
- **Fixtures** — session-scoped API clients, automatic cleanup of all created resources per worker
- **Parametrize** — data-driven tests for currencies, card types, decline scenarios
- **Markers** — 10 markers for selective execution by category
- **Auto-retry** — flaky API tests re-run twice with 1-second delay via `pytest-rerunfailures`
- **Allure reporting** — severity levels, step annotations, business descriptions
- **Custom HTML report** — dashboard with pass rate chart, module summary cards, per-test API call capture (method, URL, request/response body, response time). Auto-opens after test run.

## Test Reports

### Custom HTML Report

After running tests, a custom HTML report is generated at `reports/custom_report.html` and auto-opens in your browser. It includes:
- Pass rate donut chart and summary stats
- Module summary cards with progress bars for each of the 9 test areas
- Expandable per-test sections with API call details (HTTP method, URL, request payload, response body, response time)

### Allure Report

```bash
# Install Allure CLI (macOS)
brew install allure

# Generate and open Allure report
allure serve reports/allure-results
```

### Standard HTML Report

A `pytest-html` report is also generated at `reports/report.html`.

## CI Integration

The GitHub Actions workflow (`.github/workflows/test.yml`) runs the full suite on every push/PR to `main` or `develop`. Add your Stripe test key as a repository secret named `STRIPE_TEST_SECRET_KEY`.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Real API (no mocks) | True integration confidence — tests catch real API behavior changes |
| Session-scoped fixtures | Efficient cleanup, no orphaned test data in Stripe |
| JSON Schema validation | Contract testing, not just status codes |
| Defensive assertions | Handle Stripe behavior variations gracefully |
| 5-second performance gates | SLA-aware response time validation |
| Parallel execution (xdist) | 3x faster — ~2 min vs ~6 min sequential |
| Custom HTML report | API call capture makes debugging failures trivial |
| 10 pytest markers | Targeted CI/CD runs (smoke on commit, security in pipeline, full nightly) |
| Auto-retry with backoff | Handles transient network and rate-limit issues |
