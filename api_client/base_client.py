import json
import logging
import threading
from typing import Any

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from config.settings import Settings

logger = logging.getLogger(__name__)

# ── Per-test API call capture ────────────────────────────────────
# Thread-local storage so parallel test runs don't clash.
_capture_store = threading.local()


def start_capture():
    """Start capturing API calls for the current test."""
    _capture_store.calls = []


def stop_capture():
    """Stop capturing and return the collected API calls."""
    calls = getattr(_capture_store, "calls", [])
    _capture_store.calls = None
    return calls


def _record_call(method, url, payload, response):
    """Record a single API call if capture is active."""
    calls = getattr(_capture_store, "calls", None)
    if calls is None:
        return
    try:
        resp_body = response.json()
        resp_text = json.dumps(resp_body, indent=2)
    except Exception:
        resp_text = response.text[:2000] if response.text else ""
    calls.append({
        "method": method.upper(),
        "url": url,
        "request_payload": payload,
        "status_code": response.status_code,
        "response_time": round(response.elapsed.total_seconds(), 3),
        "response_body": resp_text,
    })


class BaseAPIClient:
    """Thin wrapper around requests that handles auth, base URL, logging, and retries."""

    def __init__(self) -> None:
        Settings.validate()
        self.base_url = Settings.BASE_URL
        self.session = requests.Session()
        self.session.headers.update(Settings.get_headers())
        self.timeout = Settings.REQUEST_TIMEOUT

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _log_request(self, method: str, url: str, **kwargs: Any) -> None:
        logger.debug(">>> %s %s  payload=%s", method.upper(), url, kwargs.get("data") or kwargs.get("params"))

    def _log_response(self, method: str, url: str, resp: requests.Response) -> None:
        logger.info("%s %s -> %s (%.2fs)", method.upper(), url, resp.status_code, resp.elapsed.total_seconds())
        if resp.status_code >= 400:
            logger.warning("<<< %s %s  status=%s  body=%s", method.upper(), url, resp.status_code, resp.text[:500])
        else:
            logger.debug("<<< %s %s  body=%s", method.upper(), url, resp.text[:500])

    def get(self, path: str, params: dict | None = None) -> requests.Response:
        url = self._url(path)
        self._log_request("GET", url, params=params)
        resp = self.session.get(url, params=params, timeout=self.timeout)
        self._log_response("GET", url, resp)
        _record_call("GET", url, params, resp)
        return resp

    def post(self, path: str, data: dict[str, Any] | None = None, headers: dict | None = None) -> requests.Response:
        url = self._url(path)
        self._log_request("POST", url, data=data)
        resp = self.session.post(url, data=data, headers=headers, timeout=self.timeout)
        self._log_response("POST", url, resp)
        _record_call("POST", url, data, resp)
        return resp

    def delete(self, path: str) -> requests.Response:
        url = self._url(path)
        self._log_request("DELETE", url)
        resp = self.session.delete(url, timeout=self.timeout)
        self._log_response("DELETE", url, resp)
        _record_call("DELETE", url, None, resp)
        return resp
