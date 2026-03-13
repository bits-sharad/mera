from __future__ import annotations

from typing import Any

import httpx
import asyncio
import time

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


def async_retry(max_attempts: int, min_wait: float = 1.0, max_wait: float = 8.0):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            attempt = 0
            wait = min_wait
            max_attempts_int = int(max_attempts)
            while attempt < max_attempts_int:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt >= max_attempts_int:
                        raise
                    logger.warning(
                        f"Retry {attempt}/{max_attempts_int} after error: {e}. Waiting {wait} seconds."
                    )
                    await asyncio.sleep(wait)
                    wait = min(wait * 2, max_wait)

        return wrapper

    return decorator


class HttpClientBase:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        # Ensure timeout is always a float
        timeout = float(settings.http_timeout_s)
        self._client = httpx.AsyncClient(timeout=timeout)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "x-api-key": f"{self.api_key}",
        }

    @async_retry(max_attempts=settings.http_max_retries, min_wait=1, max_wait=8)
    async def _request(
        self, method: str, path: str, json_body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        logger.debug(f"Making {method} request to {url}")

        resp = await self._client.request(
            method, url, headers=self._headers(), json=json_body
        )

        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error {e.response.status_code} from {url}: {e.response.text}"
            )
            raise

        result = resp.json()
        logger.debug(f"Response from {url}: {result}")
        return result
