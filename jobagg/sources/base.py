from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Iterator

import httpx

from jobagg import config

_RETRYABLE_STATUSES = {408, 429, 500, 502, 503, 504}


class BaseJobSource(ABC):
    name: str

    def _make_client(self, extra_headers: dict[str, str] | None = None) -> httpx.Client:
        headers = {
            "Accept": "application/json",
            "User-Agent": config.USER_AGENT,
        }
        if extra_headers:
            headers.update(extra_headers)
        return httpx.Client(
            timeout=httpx.Timeout(config.REQUEST_TIMEOUT, connect=config.CONNECT_TIMEOUT),
            headers=headers,
        )

    def _get_json(
        self,
        client: httpx.Client,
        url: str,
        params: dict[str, Any] | None = None,
        retries: int = 3,
    ) -> Any:
        last_err: Exception | None = None
        for attempt in range(retries):
            try:
                resp = client.get(url, params=params)
                if resp.status_code in _RETRYABLE_STATUSES:
                    raise httpx.HTTPStatusError(
                        f"retryable status={resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:
                last_err = exc
                if attempt == retries - 1:
                    raise
                time.sleep((2**attempt) + 0.2)
        raise RuntimeError("unreachable") from last_err

    @abstractmethod
    def fetch(self, **kwargs: Any) -> Iterator[dict[str, Any]]:
        raise NotImplementedError
