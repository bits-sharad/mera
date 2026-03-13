from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

from src.clients.core_api import CoreAPIClient
from src.core.audit import AuditTrail
from src.schemas.common import AgentResult, RAGSource


logger = logging.getLogger(__name__)


class AgentBase(ABC):
    name: str

    def __init__(self, core_api: CoreAPIClient):
        self.core_api = core_api

    @abstractmethod
    async def run(self, state: dict[str, Any], audit: AuditTrail) -> AgentResult:
        raise NotImplementedError

    async def _llm_generate_with_retry(
        self,
        prompt: str,
        system: str,
        model: str,
        audit: AuditTrail,
        max_retries: int = 3,
        initial_delay: float = 0.0,  # Start with 60 seconds as per Azure OpenAI recommendation
        **kwargs,
    ) -> dict[str, Any]:
        """LLM generate with exponential backoff retry for rate limiting

        Azure OpenAI rate limits typically require 60 second waits.
        This implements retry logic with increasing delays.
        """
        retry_delay = initial_delay

        for attempt in range(max_retries):
            try:
                resp = await self.core_api.llm_generate(
                    prompt=prompt, system=system, model=model, **kwargs
                )
                return resp
            except Exception as e:
                error_msg = str(e)
                is_rate_limit = (
                    "429" in error_msg
                    or "Too Many Requests" in error_msg
                    or "RateLimitReached" in error_msg
                    or "rate limit" in error_msg.lower()
                )

                if is_rate_limit:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Rate limit hit in {self.name}, retrying in {retry_delay}s... "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        audit.add(
                            "rate_limit_retry",
                            {
                                "agent": self.name,
                                "attempt": attempt + 1,
                                "retry_delay": retry_delay,
                                "error_snippet": error_msg[:200],
                            },
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay = min(retry_delay * 1.5, 180)  # Cap at 3 minutes
                        continue
                    else:
                        logger.error(
                            f"Rate limit exceeded in {self.name} after {max_retries} attempts. "
                            f"Consider reducing concurrent requests or increasing quota."
                        )
                        audit.add(
                            "rate_limit_failed",
                            {
                                "agent": self.name,
                                "attempts": max_retries,
                                "final_error": error_msg[:200],
                            },
                        )
                        raise
                else:
                    # Non-rate-limit error, raise immediately
                    logger.error(f"LLM generate error in {self.name}: {error_msg}")
                    raise

    async def _retrieve(
        self,
        query: str,
        index: str,
        top_k: int = 8,
        filters: dict[str, Any] | None = None,
    ) -> list[RAGSource]:
        resp = await self.core_api.vector_search(
            query=query, index=index, top_k=top_k, filters=filters
        )
        items = resp.get("results", []) or []
        sources: list[RAGSource] = []
        for it in items:
            sources.append(
                RAGSource(
                    id=str(it.get("id", "")),
                    score=float(it.get("score", 0.0)),
                    text=str(it.get("text", "")),
                    metadata=dict(it.get("metadata", {}) or {}),
                )
            )
        return sources
