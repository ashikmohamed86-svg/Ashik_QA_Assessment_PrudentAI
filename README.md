# Stripe API Automation Framework

Automated API test suite built with **PyTest** to validate key behaviours of the Stripe **test-mode** APIs (Customers, PaymentIntents). The framework emphasises modular design, input validation, schema verification, and end-to-end payment-flow coverage.

---

## Project Structure

```
Ashik_QA_Assessment_PrudentAI/
├── api_client/               # API client layer
│   ├── base_client.py        # Session, auth, HTTP helpers
│   ├── customers.py          # /customers resource
│   └── payment_intents.py    # /payment_intents resource
├── config/
│   └── settings.py           # Environment & config management
├── schemas/
│   ├── customer_schema.py    # JSON Schema for Customer objects
│   └── payment_intent_schema.py  # JSON Schema for PaymentIntent objects
├── utils/
│   ├── validators.py         # Schema, email, phone, currency validators
│   └── test_data.py          # Test payloads & Stripe test-card tokens
├── tests/
│   ├── test_customers.py         # Customer CRUD + validation tests
│   ├── test_payment_intents.py   # PaymentIntent lifecycle tests
│   └── test_negative_validation.py  # Negative / boundary / decline tests
├── docs/
│   └── TEST_CASES.md         # Detailed test-case document
├── .github/workflows/
│   └── test.yml              # GitHub Actions CI pipeline
├── conftest.py               # Session-scoped fixtures & cleanup
├── pytest.ini                # PyTest configuration & markers
├── requirements.txt          # Python dependencies
└── .env.example              # Environment variable template
```

## Prerequisites

- **Python 3.10+**
- A **Stripe test-mode secret key** (starts with `sk_test_...`). Obtain one from the [Stripe Dashboard → Developers → API keys](https://dashboard.stripe.com/test/apikeys).

## Setup

```bash
# 1. Clone the repository
git clone <repo-url> && cd Assignment

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
# Run the full suite
pytest

# Run only smoke tests
pytest -m smoke

# Run customer tests
pytest -m customers

# Run payment-intent tests
pytest -m payment_intents

# Run negative / validation tests
pytest -m negative

# Run end-to-end tests
pytest -m e2e

# Generate HTML report
pytest --html=reports/report.html --self-contained-html
```

### Available Markers

| Marker | Description |
|--------|-------------|
| `smoke` | Quick sanity checks for create endpoints |
| `customers` | All Customer API tests |
| `payment_intents` | All PaymentIntent API tests |
| `negative` | Negative and input-validation tests |
| `e2e` | End-to-end payment flow tests |

## Framework Design

### API Client Layer
A lightweight `BaseAPIClient` wraps `requests.Session` with:
- Automatic Bearer-token auth injection
- Base URL management
- Request logging

Resource-specific clients (`CustomersAPI`, `PaymentIntentsAPI`) expose clean, typed methods for each endpoint.

### Config Management
- All config is read from environment variables (or a `.env` file via `python-dotenv`).
- A startup validation check ensures the key exists and uses the test-mode prefix.

### Data Validation
- **JSON Schema** validation (`jsonschema`) verifies every response against strict schemas.
- Dedicated helper validators check email format (RFC-5322 pattern), phone format (E.164), and ISO 4217 currency codes.

### PyTest Features Used
- **Fixtures** – session-scoped API clients, auto-cleanup of created resources.
- **Parametrize** – data-driven currency-validation tests.
- **Markers** – selective test execution by category.
- **Strict markers** – prevents typos in marker names.
- **HTML reporting** – via `pytest-html`.

### Test Coverage

| Area | Tests |
|------|-------|
| Customer CRUD | Create (full/minimal/no-email), Fetch, List, Update, Delete |
| Customer validation | Email format, phone format, schema |
| PaymentIntent lifecycle | Create, Confirm, Capture, Fetch |
| Status transitions | `requires_payment_method` → `succeeded`, manual-capture flow |
| Input validation | Missing/invalid/boundary amounts, invalid currencies |
| Decline scenarios | Declined, insufficient funds, expired card, incorrect CVC |
| End-to-end | Automatic capture flow, manual capture flow |

## CI Integration

The GitHub Actions workflow (`.github/workflows/test.yml`) runs the full suite on every push/PR to `main`. Add your Stripe test key as a repository secret named `STRIPE_TEST_SECRET_KEY`.

## Test Reports

After running tests, an HTML report is generated at `reports/report.html`. In CI, the report is uploaded as a build artifact.
