import logging
import sys

import pytest

from api_client.customers import CustomersAPI
from api_client.payment_intents import PaymentIntentsAPI

# ── Logging ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stdout,
)


# ── API client fixtures ─────────────────────────────────────────────
@pytest.fixture(scope="session")
def customers_api():
    return CustomersAPI()


@pytest.fixture(scope="session")
def payments_api():
    return PaymentIntentsAPI()


# ── Cleanup registries ──────────────────────────────────────────────
@pytest.fixture(scope="session")
def created_customer_ids():
    """Collect customer IDs for teardown."""
    return []


@pytest.fixture(scope="session")
def created_payment_intent_ids():
    """Collect payment-intent IDs for teardown."""
    return []


@pytest.fixture(autouse=True, scope="session")
def cleanup_customers(customers_api, created_customer_ids):
    yield
    for cid in created_customer_ids:
        try:
            customers_api.delete_customer(cid)
        except Exception:
            pass


@pytest.fixture(autouse=True, scope="session")
def cleanup_payment_intents(payments_api, created_payment_intent_ids):
    yield
    for pid in created_payment_intent_ids:
        try:
            payments_api.cancel(pid)
        except Exception:
            pass
