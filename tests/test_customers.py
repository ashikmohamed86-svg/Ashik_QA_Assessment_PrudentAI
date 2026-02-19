"""Tests for Stripe Customers API – CRUD, schema, and field validation."""

import allure
import pytest

from schemas.customer_schema import CUSTOMER_SCHEMA, CUSTOMER_LIST_SCHEMA, STRIPE_ERROR_SCHEMA
from utils.validators import (
    validate_schema, is_valid_email, is_valid_phone,
    assert_response_time, assert_response_headers,
)
from utils.test_data import VALID_CUSTOMER, CUSTOMER_MINIMAL


# ─────────────────────────────────────────────────────────────────────
#  Create Customer
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Customers API")
@allure.story("Create Customer")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.smoke
@pytest.mark.customers
class TestCreateCustomer:

    @allure.description("Verify that a customer with name, email, phone is created and all fields echo back correctly.")
    def test_create_customer_with_all_fields(
        self, customers_api, created_customer_ids
    ):
        with allure.step("Send POST /customers with all fields"):
            resp = customers_api.create(**VALID_CUSTOMER)
            body = resp.json()

        with allure.step("Validate status, ID prefix, and field values"):
            assert resp.status_code == 200
            assert_response_time(resp)
            assert_response_headers(resp)
            assert body["id"].startswith("cus_")
            assert body["name"] == VALID_CUSTOMER["name"]
            assert body["email"] == VALID_CUSTOMER["email"]
            assert body["phone"] == VALID_CUSTOMER["phone"]

        with allure.step("Validate response schema"):
            validate_schema(body, CUSTOMER_SCHEMA)

        created_customer_ids.append(body["id"])

    def test_create_customer_minimal(
        self, customers_api, created_customer_ids
    ):
        with allure.step("Create customer with email only"):
            resp = customers_api.create(**CUSTOMER_MINIMAL)
            body = resp.json()

        with allure.step("Verify minimal customer created"):
            assert resp.status_code == 200
            assert body["id"].startswith("cus_")
            assert body["email"] == CUSTOMER_MINIMAL["email"]
            validate_schema(body, CUSTOMER_SCHEMA)

        created_customer_ids.append(body["id"])

    @allure.description("Email is optional in Stripe; customer should still be created with email=null.")
    def test_create_customer_without_email(
        self, customers_api, created_customer_ids
    ):
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
@allure.feature("Customers API")
@allure.story("Fetch Customer")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.customers
class TestFetchCustomer:

    @pytest.fixture(autouse=True)
    def _setup_customer(self, customers_api, created_customer_ids):
        resp = customers_api.create(**VALID_CUSTOMER)
        self.customer = resp.json()
        created_customer_ids.append(self.customer["id"])

    def test_fetch_existing_customer(self, customers_api):
        with allure.step(f"Fetch customer {self.customer['id']}"):
            resp = customers_api.retrieve(self.customer["id"])
            body = resp.json()

        with allure.step("Verify correct details returned"):
            assert resp.status_code == 200
            assert_response_headers(resp)
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
@allure.feature("Customers API")
@allure.story("Customer Operations")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.customers
class TestCustomerOperations:

    def test_list_customers(self, customers_api):
        resp = customers_api.list_customers(limit=3)
        body = resp.json()

        assert resp.status_code == 200
        validate_schema(body, CUSTOMER_LIST_SCHEMA)
        assert len(body["data"]) <= 3

    def test_update_customer_name(self, customers_api, created_customer_ids):
        with allure.step("Create a customer to update"):
            create_resp = customers_api.create(**VALID_CUSTOMER)
            cid = create_resp.json()["id"]
            created_customer_ids.append(cid)

        with allure.step("Update customer name"):
            update_resp = customers_api.update(cid, name="Updated Name")
            body = update_resp.json()

        with allure.step("Verify name changed, other fields unchanged"):
            assert update_resp.status_code == 200
            assert body["name"] == "Updated Name"
            assert body["email"] == VALID_CUSTOMER["email"]

    def test_update_customer_email(self, customers_api, created_customer_ids):
        cust = customers_api.create(**VALID_CUSTOMER).json()
        created_customer_ids.append(cust["id"])

        updated = customers_api.update(cust["id"], email="updated@example.com").json()

        assert updated["email"] == "updated@example.com"
        assert updated["name"] == VALID_CUSTOMER["name"]

    @allure.description("Verify the description field is stored and returned correctly.")
    def test_create_customer_with_description(self, customers_api, created_customer_ids):
        resp = customers_api.create(**VALID_CUSTOMER)
        body = resp.json()

        assert resp.status_code == 200
        assert body["description"] == VALID_CUSTOMER["description"]
        created_customer_ids.append(body["id"])

    def test_delete_customer(self, customers_api):
        create_resp = customers_api.create(email="delete_me@example.com")
        cid = create_resp.json()["id"]

        del_resp = customers_api.delete_customer(cid)
        body = del_resp.json()

        assert del_resp.status_code == 200
        assert body["deleted"] is True
        assert body["id"] == cid


# ─────────────────────────────────────────────────────────────────────
#  Pagination
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Customers API")
@allure.story("Pagination")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.customers
class TestCustomerPagination:

    @allure.description("Verify that the limit parameter restricts the number of results returned.")
    def test_limit_returns_correct_count(self, customers_api):
        resp = customers_api.list_customers(limit=1)
        body = resp.json()

        assert resp.status_code == 200
        assert len(body["data"]) == 1

    @allure.description("Fetch page 1, then page 2 using the starting_after cursor to verify pagination works.")
    def test_paginate_with_starting_after(self, customers_api):
        with allure.step("Fetch first page"):
            page1 = customers_api.list_customers(limit=1).json()
            assert len(page1["data"]) == 1

        with allure.step("Fetch second page using cursor"):
            last_id = page1["data"][-1]["id"]
            page2 = customers_api.list_customers(limit=1, starting_after=last_id).json()

        with allure.step("Verify different customer returned"):
            assert page2["data"][0]["id"] != last_id

    def test_has_more_flag(self, customers_api):
        """With limit=1, has_more should be True if more than 1 customer exists."""
        resp = customers_api.list_customers(limit=1).json()
        assert isinstance(resp["has_more"], bool)
        assert resp["has_more"] is True


# ─────────────────────────────────────────────────────────────────────
#  Metadata CRUD
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Customers API")
@allure.story("Metadata")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.customers
class TestCustomerMetadata:

    @allure.description("Stripe metadata is a key-value store; verify it persists on creation.")
    def test_create_customer_with_metadata(
        self, customers_api, created_customer_ids
    ):
        resp = customers_api.create(
            email="meta@example.com",
            **{"metadata[env]": "test", "metadata[source]": "automation"},
        )
        body = resp.json()

        assert resp.status_code == 200
        assert body["metadata"]["env"] == "test"
        assert body["metadata"]["source"] == "automation"
        created_customer_ids.append(body["id"])

    def test_update_metadata(self, customers_api, created_customer_ids):
        with allure.step("Create customer with metadata version=1"):
            cust = customers_api.create(
                email="meta_update@example.com",
                **{"metadata[version]": "1"},
            ).json()
            created_customer_ids.append(cust["id"])

        with allure.step("Update metadata version to 2"):
            updated = customers_api.update(
                cust["id"], **{"metadata[version]": "2"}
            ).json()

        with allure.step("Verify metadata updated"):
            assert updated["metadata"]["version"] == "2"

    def test_clear_metadata(self, customers_api, created_customer_ids):
        cust = customers_api.create(
            email="meta_clear@example.com",
            **{"metadata[key]": "value"},
        ).json()
        created_customer_ids.append(cust["id"])

        cleared = customers_api.update(
            cust["id"], **{"metadata[key]": ""}
        ).json()

        assert cleared["metadata"].get("key", "") == ""


# ─────────────────────────────────────────────────────────────────────
#  Negative – Customer Error Scenarios
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Customers API")
@allure.story("Negative Error Scenarios")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.negative
@pytest.mark.customers
class TestCustomerNegativeErrors:

    def test_delete_non_existing_customer(self, customers_api):
        resp = customers_api.delete_customer("cus_nonexistent000000000")
        assert resp.status_code == 404

    def test_double_delete_customer(self, customers_api):
        """Deleting an already-deleted customer should return an error."""
        cust = customers_api.create(email="double_del@example.com").json()
        customers_api.delete_customer(cust["id"])

        resp = customers_api.delete_customer(cust["id"])
        assert resp.status_code == 404

    def test_update_non_existing_customer(self, customers_api):
        resp = customers_api.update("cus_nonexistent000000000", name="Ghost")
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────
#  Performance – Customer Response Times
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Customers API")
@allure.story("Performance")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.customers
class TestCustomerPerformance:

    def test_create_response_time(self, customers_api, created_customer_ids):
        resp = customers_api.create(**VALID_CUSTOMER)
        assert_response_time(resp, max_seconds=5.0)
        created_customer_ids.append(resp.json()["id"])

    def test_fetch_response_time(self, customers_api, created_customer_ids):
        cust = customers_api.create(**VALID_CUSTOMER).json()
        created_customer_ids.append(cust["id"])

        resp = customers_api.retrieve(cust["id"])
        assert_response_time(resp, max_seconds=5.0)

    def test_list_response_time(self, customers_api):
        resp = customers_api.list_customers(limit=10)
        assert_response_time(resp, max_seconds=5.0)

    def test_update_response_time(self, customers_api, created_customer_ids):
        cust = customers_api.create(**VALID_CUSTOMER).json()
        created_customer_ids.append(cust["id"])

        resp = customers_api.update(cust["id"], name="Perf Test")
        assert_response_time(resp, max_seconds=5.0)

    def test_delete_response_time(self, customers_api):
        cust = customers_api.create(email="perf_del@example.com").json()

        resp = customers_api.delete_customer(cust["id"])
        assert_response_time(resp, max_seconds=5.0)


# ─────────────────────────────────────────────────────────────────────
#  Boundary / Limit – Customer Fields
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Customers API")
@allure.story("Boundary & Limit")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.negative
@pytest.mark.customers
class TestCustomerBoundary:

    @allure.description("Verify special characters (unicode, emojis) in customer name are handled.")
    def test_special_characters_in_name(self, customers_api, created_customer_ids):
        resp = customers_api.create(name="Tester Mller", email="unicode@example.com")
        body = resp.json()

        assert resp.status_code == 200
        assert "Mller" in body["name"]
        created_customer_ids.append(body["id"])

    def test_empty_string_name(self, customers_api, created_customer_ids):
        """Empty string name should be accepted — Stripe stores it as empty."""
        resp = customers_api.create(name="", email="empty_name@example.com")
        body = resp.json()

        assert resp.status_code == 200
        created_customer_ids.append(body["id"])

    def test_empty_string_phone(self, customers_api, created_customer_ids):
        """Empty phone should be accepted by Stripe."""
        resp = customers_api.create(email="empty_phone@example.com", phone="")
        body = resp.json()

        assert resp.status_code == 200
        created_customer_ids.append(body["id"])

    def test_list_max_limit(self, customers_api):
        """Stripe allows limit up to 100."""
        resp = customers_api.list_customers(limit=100)
        body = resp.json()

        assert resp.status_code == 200
        assert len(body["data"]) <= 100
        validate_schema(body, CUSTOMER_LIST_SCHEMA)
