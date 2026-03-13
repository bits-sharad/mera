from __future__ import annotations

from typing import Any

from src.clients.http_base import HttpClientBase
from src.core.config import settings


class CoreAPIClient(HttpClientBase):
    """-provided Core API wrapper.

    Expected responsibilities (per architecture):
    - LLM reasoning/generation
    - embeddings
    - vector search (MongoDB Atlas Vector Search)
    - metadata CRUD (MongoDB collections)
    """

    def __init__(self) -> None:
        super().__init__(
            base_url=settings.core_api_base_url, api_key=settings.core_api_key
        )
        self.embeddings_client = HttpClientBase(
            base_url=settings.embeddings_base_url, api_key=settings.core_api_key
        )
        self.embeddings_model = settings.embeddings_model

    async def llm_generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        system: str | None = None,
    ) -> dict[str, Any]:
        messages = []

        # Add system message if provided
        if system:
            messages.append({"role": "system", "content": system})

        # Add user message with the prompt
        messages.append({"role": "user", "content": prompt})

        body = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        # TODO: confirm  path contract
        return await self._request("POST", "", json_body=body)

    async def embed(
        self,
        texts: list[str],
        model: str | None = None,
        user: str | None = None,
        input_type: str = "query",
        encoding_format: str = "base64",
    ) -> dict[str, Any]:
        """Generate embeddings for texts.

        Args:
            texts: List of text strings to embed
            model: Model name (uses default from config if not provided)
            user: User identifier for tracking
            input_type: Type of input (query, passage, etc.)
            encoding_format: Format for embeddings (base64, float, etc.)

        Returns:
            Response containing embeddings list
        """
        # Use provided model or fall back to config default
        model_to_use = model or self.embeddings_model

        # Use embeddings client with model in path
        path = f"/{model_to_use}"

        body = {
            "input": texts,
            "model": model_to_use,
            "input_type": input_type,
            "encoding_format": encoding_format,
        }
        if user:
            body["user"] = user

        return await self.embeddings_client._request("POST", path, json_body=body)

    async def vector_search(
        self,
        query: str,
        index: str,
        top_k: int = 8,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = {
            "query": query,
            "index": index,
            "top_k": top_k,
            "filters": filters or {},
        }
        return await self._request("POST", "/vector/search", json_body=body)

    async def metadata_get(self, collection: str, key: str) -> dict[str, Any]:
        return await self._request("GET", f"/metadata/{collection}/{key}")

    async def metadata_put(
        self, collection: str, key: str, doc: dict[str, Any]
    ) -> dict[str, Any]:
        body = {"key": key, "doc": doc}
        return await self._request("PUT", f"/metadata/{collection}", json_body=body)
