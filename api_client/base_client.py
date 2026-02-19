import logging
from typing import Any

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from config.settings import Settings

logger = logging.getLogger(__name__)


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
        return resp

    def post(self, path: str, data: dict[str, Any] | None = None, headers: dict | None = None) -> requests.Response:
        url = self._url(path)
        self._log_request("POST", url, data=data)
        resp = self.session.post(url, data=data, headers=headers, timeout=self.timeout)
        self._log_response("POST", url, resp)
        return resp

    def delete(self, path: str) -> requests.Response:
        url = self._url(path)
        self._log_request("DELETE", url)
        resp = self.session.delete(url, timeout=self.timeout)
        self._log_response("DELETE", url, resp)
        return resp
