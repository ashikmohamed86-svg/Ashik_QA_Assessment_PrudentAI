from typing import Any

import requests

from api_client.base_client import BaseAPIClient


class CustomersAPI(BaseAPIClient):
    """Stripe Customers resource wrapper."""

    RESOURCE = "customers"

    def create(self, **fields: Any) -> requests.Response:
        return self.post(self.RESOURCE, data=fields)

    def retrieve(self, customer_id: str) -> requests.Response:
        return self.get(f"{self.RESOURCE}/{customer_id}")

    def list_customers(self, limit: int = 10, starting_after: str | None = None) -> requests.Response:
        params = {"limit": limit}
        if starting_after:
            params["starting_after"] = starting_after
        return self.get(self.RESOURCE, params=params)

    def delete_customer(self, customer_id: str) -> requests.Response:
        return self.delete(f"{self.RESOURCE}/{customer_id}")

    def update(self, customer_id: str, **fields: Any) -> requests.Response:
        return self.post(f"{self.RESOURCE}/{customer_id}", data=fields)
