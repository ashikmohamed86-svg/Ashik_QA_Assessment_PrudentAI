"""Tests for Stripe Customers API – CRUD, schema, and field validation."""

import allure
import pytest

from schemas.customer_schema import CUSTOMER_SCHEMA, CUSTOMER_LIST_SCHEMA, STRIPE_ERROR_SCHEMA
from utils.validators import (
    validate_schema, is_valid_email, is_valid_phone,
    assert_response_time, assert_response_headers,
)
import uuid

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

    @allure.description("Fetch non-existing customer returns 404 with error schema containing type, message.")
    def test_fetch_non_existing_customer(self, customers_api):
        resp = customers_api.retrieve("cus_nonexistent000000000")
        body = resp.json()

        assert resp.status_code == 404
        validate_schema(body, STRIPE_ERROR_SCHEMA)
        assert body["error"]["type"] is not None
        assert len(body["error"]["message"]) > 0

    def test_fetch_invalid_id_format(self, customers_api):
        resp = customers_api.retrieve("invalid_id")
        assert resp.status_code == 404
        validate_schema(resp.json(), STRIPE_ERROR_SCHEMA)


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

    @allure.description(
        "Verify behavior when limit=0 is passed. "
        "Stripe may accept it gracefully or return an error."
    )
    def test_limit_zero_edge_case(self, customers_api):
        resp = customers_api.list_customers(limit=0)
        body = resp.json()

        if resp.status_code == 200:
            # Stripe accepts limit=0 gracefully — returns results using default
            validate_schema(body, CUSTOMER_LIST_SCHEMA)
        else:
            assert resp.status_code == 400
            validate_schema(body, STRIPE_ERROR_SCHEMA)

    @allure.description(
        "Verify behavior when limit=101 exceeds Stripe max of 100. "
        "Stripe may cap it or return an error."
    )
    def test_limit_over_max_edge_case(self, customers_api):
        resp = customers_api.list_customers(limit=101)
        body = resp.json()

        if resp.status_code == 200:
            # Stripe accepts and caps at its max
            validate_schema(body, CUSTOMER_LIST_SCHEMA)
            assert len(body["data"]) <= 101
        else:
            assert resp.status_code == 400
            validate_schema(body, STRIPE_ERROR_SCHEMA)

    @allure.description("Verify invalid starting_after cursor returns an error.")
    def test_invalid_starting_after_cursor(self, customers_api):
        resp = customers_api.list_customers(limit=1, starting_after="cus_invalid_cursor_xyz")
        body = resp.json()

        # Stripe returns 400 (resource_missing) for invalid cursors
        assert resp.status_code in (400, 404), (
            f"Expected error for invalid cursor, got {resp.status_code}"
        )
        validate_schema(body, STRIPE_ERROR_SCHEMA)

    @allure.description("Paginate through all customers until has_more is false.")
    def test_full_pagination_loop(self, customers_api):
        """Walk pages until has_more=false (max 10 pages to avoid infinite loop)."""
        seen_ids = set()
        cursor = None
        pages = 0
        max_pages = 10

        while pages < max_pages:
            if cursor:
                resp = customers_api.list_customers(limit=5, starting_after=cursor)
            else:
                resp = customers_api.list_customers(limit=5)
            body = resp.json()
            assert resp.status_code == 200

            for cust in body["data"]:
                assert cust["id"] not in seen_ids, f"Duplicate customer ID across pages: {cust['id']}"
                seen_ids.add(cust["id"])

            pages += 1
            if not body["has_more"]:
                break
            cursor = body["data"][-1]["id"]

        assert len(seen_ids) > 0, "Expected at least one customer across all pages"


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

    @allure.description("Stripe allows duplicate emails — two customers with the same email should both be created.")
    def test_duplicate_email_allowed(self, customers_api, created_customer_ids):
        email = "duplicate_boundary@example.com"
        resp1 = customers_api.create(email=email, name="Dup One")
        resp2 = customers_api.create(email=email, name="Dup Two")
        body1, body2 = resp1.json(), resp2.json()

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert body1["id"] != body2["id"]
        assert body1["email"] == body2["email"] == email

        created_customer_ids.append(body1["id"])
        created_customer_ids.append(body2["id"])

    @allure.description("Stripe supports up to 50 metadata key-value pairs per object.")
    def test_max_metadata_keys(self, customers_api, created_customer_ids):
        metadata = {f"metadata[key_{i:02d}]": f"value_{i}" for i in range(50)}
        resp = customers_api.create(email="max_meta@example.com", **metadata)
        body = resp.json()

        assert resp.status_code == 200
        assert len(body["metadata"]) == 50
        created_customer_ids.append(body["id"])


# ─────────────────────────────────────────────────────────────────────
#  Customer – Invalid Phone Validation
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Customers API")
@allure.story("Phone Validation")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.negative
@pytest.mark.customers
class TestCustomerPhoneValidation:

    @allure.description(
        "CUS-NEG-04: Create customer with invalid phone 'abc123'. "
        "Stripe may accept it, but our E.164 validator should flag it."
    )
    def test_create_customer_invalid_phone(self, customers_api, created_customer_ids):
        resp = customers_api.create(
            name="Bad Phone", email="badphone@example.com", phone="abc123"
        )
        body = resp.json()

        if resp.status_code == 200:
            # Stripe accepted — but our validator correctly flags the format
            assert not is_valid_phone(body.get("phone", "")), (
                "Phone 'abc123' should fail E.164 validation"
            )
            created_customer_ids.append(body["id"])
        else:
            assert resp.status_code == 400
            validate_schema(body, STRIPE_ERROR_SCHEMA)


# ─────────────────────────────────────────────────────────────────────
#  Customer – Idempotency
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Customers API")
@allure.story("Idempotency")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.customers
class TestCustomerIdempotency:

    @allure.description(
        "IDEMP-E2E-02: Same Idempotency-Key on POST /customers returns the same customer."
    )
    def test_same_idempotency_key_returns_same_customer(
        self, customers_api, created_customer_ids
    ):
        key = f"cust-idem-{uuid.uuid4()}"
        headers = {"Idempotency-Key": key}

        with allure.step("Create customer twice with same idempotency key"):
            resp1 = customers_api.session.post(
                f"{customers_api.base_url}/customers",
                data={"email": "idem@example.com", "name": "Idem Test"},
                headers=headers,
                timeout=customers_api.timeout,
            )
            resp2 = customers_api.session.post(
                f"{customers_api.base_url}/customers",
                data={"email": "idem@example.com", "name": "Idem Test"},
                headers=headers,
                timeout=customers_api.timeout,
            )

        with allure.step("Verify both return the same customer ID"):
            body1 = resp1.json()
            body2 = resp2.json()
            assert resp1.status_code == 200
            assert resp2.status_code == 200
            assert body1["id"] == body2["id"]

        created_customer_ids.append(body1["id"])


# ─────────────────────────────────────────────────────────────────────
#  Customer – Search & Filter
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Customers API")
@allure.story("Search & Filter")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.customers
class TestCustomerSearch:

    @allure.description("Search customers by email — verify filtered results.")
    def test_search_by_email(self, customers_api, created_customer_ids):
        unique_email = f"search_{uuid.uuid4().hex[:8]}@example.com"
        cust = customers_api.create(email=unique_email, name="Search Test").json()
        created_customer_ids.append(cust["id"])

        resp = customers_api.list_customers(limit=1, email=unique_email)
        body = resp.json()

        assert resp.status_code == 200
        assert len(body["data"]) == 1
        assert body["data"][0]["email"] == unique_email
        assert body["data"][0]["id"] == cust["id"]

    @allure.description("Search by email that does not exist returns empty list.")
    def test_search_nonexistent_email(self, customers_api):
        resp = customers_api.list_customers(limit=1, email="nonexistent_xyz_999@example.com")
        body = resp.json()

        assert resp.status_code == 200
        assert len(body["data"]) == 0


# ─────────────────────────────────────────────────────────────────────
#  Customer – Additional Update Tests
# ─────────────────────────────────────────────────────────────────────
@allure.feature("Customers API")
@allure.story("Update Fields")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.customers
class TestCustomerUpdateFields:

    @allure.description("Update customer phone independently without affecting other fields.")
    def test_update_phone(self, customers_api, created_customer_ids):
        cust = customers_api.create(**VALID_CUSTOMER).json()
        created_customer_ids.append(cust["id"])

        updated = customers_api.update(cust["id"], phone="+442071234567").json()
        assert updated["phone"] == "+442071234567"
        assert updated["name"] == VALID_CUSTOMER["name"]
        assert updated["email"] == VALID_CUSTOMER["email"]

    @allure.description("Update customer description after creation.")
    def test_update_description(self, customers_api, created_customer_ids):
        cust = customers_api.create(**VALID_CUSTOMER).json()
        created_customer_ids.append(cust["id"])

        updated = customers_api.update(cust["id"], description="Updated description").json()
        assert updated["description"] == "Updated description"
        assert updated["name"] == VALID_CUSTOMER["name"]

    @allure.description("Whitespace-only name should be accepted by Stripe (distinct from empty string).")
    def test_whitespace_only_name(self, customers_api, created_customer_ids):
        resp = customers_api.create(name="   ", email="whitespace@example.com")
        body = resp.json()

        assert resp.status_code == 200
        created_customer_ids.append(body["id"])

    @allure.description("Verify created timestamp is within reasonable delta of current time (UTC).")
    def test_timestamp_is_recent(self, customers_api, created_customer_ids):
        import time
        before = int(time.time())
        cust = customers_api.create(email="timestamp@example.com").json()
        after = int(time.time())
        created_customer_ids.append(cust["id"])

        assert before - 5 <= cust["created"] <= after + 5, (
            f"Timestamp {cust['created']} not within expected range [{before}, {after}]"
        )

    @allure.description("Sending extra/unknown parameters should be rejected by Stripe.")
    def test_extra_unknown_parameters_rejected(self, customers_api):
        resp = customers_api.create(
            email="extra_params@example.com",
            unknown_field="should_be_rejected",
            another_fake_field="also_rejected",
        )
        body = resp.json()

        # Stripe rejects unknown parameters with 400
        assert resp.status_code == 400
        validate_schema(body, STRIPE_ERROR_SCHEMA)
        assert body["error"]["code"] == "parameter_unknown"
