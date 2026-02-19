from typing import Any

import requests

from api_client.base_client import BaseAPIClient


class PaymentIntentsAPI(BaseAPIClient):
    """Stripe PaymentIntents resource wrapper."""

    RESOURCE = "payment_intents"

    def create(self, **fields: Any) -> requests.Response:
        return self.post(self.RESOURCE, data=fields)

    def retrieve(self, intent_id: str) -> requests.Response:
        return self.get(f"{self.RESOURCE}/{intent_id}")

    def confirm(self, intent_id: str, **fields: Any) -> requests.Response:
        return self.post(f"{self.RESOURCE}/{intent_id}/confirm", data=fields)

    def capture(self, intent_id: str, **fields: Any) -> requests.Response:
        return self.post(f"{self.RESOURCE}/{intent_id}/capture", data=fields)

    def cancel(self, intent_id: str) -> requests.Response:
        return self.post(f"{self.RESOURCE}/{intent_id}/cancel")
