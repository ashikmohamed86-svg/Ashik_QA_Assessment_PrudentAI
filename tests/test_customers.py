"""Tests for Stripe Customers API – CRUD, schema, and field validation."""

import pytest

from schemas.customer_schema import CUSTOMER_SCHEMA, CUSTOMER_LIST_SCHEMA
from utils.validators import validate_schema, is_valid_email, is_valid_phone
from utils.test_data import VALID_CUSTOMER, CUSTOMER_MINIMAL


# ─────────────────────────────────────────────────────────────────────
#  Create Customer
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.smoke
@pytest.mark.customers
class TestCreateCustomer:

    def test_create_customer_with_all_fields(
        self, customers_api, created_customer_ids
    ):
        resp = customers_api.create(**VALID_CUSTOMER)
        body = resp.json()

        assert resp.status_code == 200
        assert body["id"].startswith("cus_")
        assert body["name"] == VALID_CUSTOMER["name"]
        assert body["email"] == VALID_CUSTOMER["email"]
        assert body["phone"] == VALID_CUSTOMER["phone"]
        validate_schema(body, CUSTOMER_SCHEMA)

        created_customer_ids.append(body["id"])

    def test_create_customer_minimal(
        self, customers_api, created_customer_ids
    ):
        resp = customers_api.create(**CUSTOMER_MINIMAL)
        body = resp.json()

        assert resp.status_code == 200
        assert body["id"].startswith("cus_")
        assert body["email"] == CUSTOMER_MINIMAL["email"]
        validate_schema(body, CUSTOMER_SCHEMA)

        created_customer_ids.append(body["id"])

    def test_create_customer_without_email(
        self, customers_api, created_customer_ids
    ):
        """Email is optional in Stripe; customer should still be created."""
        resp = customers_api.create(name="No Email", phone="+14155550000")
        body = resp.json()

        assert resp.status_code == 200
        assert body["id"].startswith("cus_")
        assert body["email"] is None
        validate_schema(body, CUSTOMER_SCHEMA)

        created_customer_ids.append(body["id"])

    def test_email_format_valid(self, customers_api, created_customer_ids):
        resp = customers_api.create(**VALID_CUSTOMER)
        body = resp.json()

        assert resp.status_code == 200
        assert is_valid_email(body["email"])

        created_customer_ids.append(body["id"])

    def test_phone_format_valid(self, customers_api, created_customer_ids):
        resp = customers_api.create(**VALID_CUSTOMER)
        body = resp.json()

        assert resp.status_code == 200
        assert is_valid_phone(body["phone"])

        created_customer_ids.append(body["id"])

    def test_response_schema(self, customers_api, created_customer_ids):
        resp = customers_api.create(**VALID_CUSTOMER)
        body = resp.json()

        validate_schema(body, CUSTOMER_SCHEMA)
        created_customer_ids.append(body["id"])


# ─────────────────────────────────────────────────────────────────────
#  Fetch Customer Details
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.customers
class TestFetchCustomer:

    @pytest.fixture(autouse=True)
    def _setup_customer(self, customers_api, created_customer_ids):
        resp = customers_api.create(**VALID_CUSTOMER)
        self.customer = resp.json()
        created_customer_ids.append(self.customer["id"])

    def test_fetch_existing_customer(self, customers_api):
        resp = customers_api.retrieve(self.customer["id"])
        body = resp.json()

        assert resp.status_code == 200
        assert body["id"] == self.customer["id"]
        assert body["email"] == VALID_CUSTOMER["email"]
        validate_schema(body, CUSTOMER_SCHEMA)

    def test_fetch_non_existing_customer(self, customers_api):
        resp = customers_api.retrieve("cus_nonexistent000000000")
        assert resp.status_code == 404

    def test_fetch_invalid_id_format(self, customers_api):
        resp = customers_api.retrieve("invalid_id")
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────
#  List / Update / Delete
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.customers
class TestCustomerOperations:

    def test_list_customers(self, customers_api):
        resp = customers_api.list_customers(limit=3)
        body = resp.json()

        assert resp.status_code == 200
        validate_schema(body, CUSTOMER_LIST_SCHEMA)
        assert len(body["data"]) <= 3

    def test_update_customer(self, customers_api, created_customer_ids):
        create_resp = customers_api.create(**VALID_CUSTOMER)
        cid = create_resp.json()["id"]
        created_customer_ids.append(cid)

        update_resp = customers_api.update(cid, name="Updated Name")
        body = update_resp.json()

        assert update_resp.status_code == 200
        assert body["name"] == "Updated Name"
        assert body["email"] == VALID_CUSTOMER["email"]

    def test_delete_customer(self, customers_api):
        create_resp = customers_api.create(email="delete_me@example.com")
        cid = create_resp.json()["id"]

        del_resp = customers_api.delete_customer(cid)
        body = del_resp.json()

        assert del_resp.status_code == 200
        assert body["deleted"] is True
        assert body["id"] == cid
