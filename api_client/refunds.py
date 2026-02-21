from typing import Any

import requests

from api_client.base_client import BaseAPIClient


class RefundsAPI(BaseAPIClient):
    """Stripe Refunds resource wrapper."""

    RESOURCE = "refunds"

    def create(self, payment_intent: str, **fields: Any) -> requests.Response:
        return self.post(self.RESOURCE, data={"payment_intent": payment_intent, **fields})

    def retrieve(self, refund_id: str) -> requests.Response:
        return self.get(f"{self.RESOURCE}/{refund_id}")

    def list_refunds(self, limit: int = 10, **filters: Any) -> requests.Response:
        params = {"limit": limit, **filters}
        return self.get(self.RESOURCE, params=params)
