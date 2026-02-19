import logging
from typing import Any

import requests

from config.settings import Settings

logger = logging.getLogger(__name__)


class BaseAPIClient:
    """Thin wrapper around requests that handles auth, base URL, and logging."""

    def __init__(self) -> None:
        Settings.validate()
        self.base_url = Settings.BASE_URL
        self.session = requests.Session()
        self.session.headers.update(Settings.get_headers())
        self.timeout = Settings.REQUEST_TIMEOUT

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _log(self, method: str, url: str, status: int) -> None:
        logger.info("%s %s -> %s", method.upper(), url, status)

    def get(self, path: str, params: dict | None = None) -> requests.Response:
        url = self._url(path)
        resp = self.session.get(url, params=params, timeout=self.timeout)
        self._log("GET", url, resp.status_code)
        return resp

    def post(self, path: str, data: dict[str, Any] | None = None) -> requests.Response:
        url = self._url(path)
        resp = self.session.post(url, data=data, timeout=self.timeout)
        self._log("POST", url, resp.status_code)
        return resp

    def delete(self, path: str) -> requests.Response:
        url = self._url(path)
        resp = self.session.delete(url, timeout=self.timeout)
        self._log("DELETE", url, resp.status_code)
        return resp
