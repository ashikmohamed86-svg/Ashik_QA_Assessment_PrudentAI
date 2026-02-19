import logging
import os
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


# ── Reports directory (fresh-clone fix) ────────────────────────────
@pytest.fixture(autouse=True, scope="session")
def _ensure_reports_dir():
    os.makedirs("reports", exist_ok=True)


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
    logger = logging.getLogger("cleanup")
    for cid in created_customer_ids:
        try:
            customers_api.delete_customer(cid)
        except Exception as exc:
            logger.warning("Failed to delete customer %s: %s", cid, exc)


@pytest.fixture(autouse=True, scope="session")
def cleanup_payment_intents(payments_api, created_payment_intent_ids):
    yield
    logger = logging.getLogger("cleanup")
    for pid in created_payment_intent_ids:
        try:
            pi = payments_api.retrieve(pid).json()
            if pi.get("status") in ("requires_payment_method", "requires_capture", "requires_confirmation"):
                payments_api.cancel(pid)
        except Exception as exc:
            logger.warning("Failed to cancel payment intent %s: %s", pid, exc)
