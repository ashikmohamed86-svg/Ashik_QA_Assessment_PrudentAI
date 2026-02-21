from typing import Any

import requests

from api_client.base_client import BaseAPIClient


class PaymentIntentsAPI(BaseAPIClient):
    """Stripe PaymentIntents resource wrapper."""

    RESOURCE = "payment_intents"

    def create(self, idempotency_key: str | None = None, **fields: Any) -> requests.Response:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        return self.post(self.RESOURCE, data=fields, headers=headers)

    def retrieve(self, intent_id: str) -> requests.Response:
        return self.get(f"{self.RESOURCE}/{intent_id}")

    def confirm(self, intent_id: str, **fields: Any) -> requests.Response:
        return self.post(f"{self.RESOURCE}/{intent_id}/confirm", data=fields)

    def capture(self, intent_id: str, **fields: Any) -> requests.Response:
        return self.post(f"{self.RESOURCE}/{intent_id}/capture", data=fields)

    def cancel(self, intent_id: str, **fields: Any) -> requests.Response:
        return self.post(f"{self.RESOURCE}/{intent_id}/cancel", data=fields or None)

    def list_intents(self, limit: int = 10, starting_after: str | None = None, **filters: Any) -> requests.Response:
        params = {"limit": limit, **filters}
        if starting_after:
            params["starting_after"] = starting_after
        return self.get(self.RESOURCE, params=params)

    def update(self, intent_id: str, **fields: Any) -> requests.Response:
        return self.post(f"{self.RESOURCE}/{intent_id}", data=fields)
