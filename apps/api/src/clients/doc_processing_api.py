from __future__ import annotations

import base64
import logging
from typing import Any

from src.clients.http_base import HttpClientBase
from src.core.config import settings
from src.utility.helper import clean_extracted_text


logger = logging.getLogger(__name__)

# Keys that typically hold extracted text to clean
_TEXT_KEYS = frozenset(
    {
        "text",
        "content",
        "extracted_text",
        "body",
        "full_text",
        "raw_text",
        "plain_text",
        "ocr_text",
    }
)


def _clean_extraction_result(obj: Any) -> Any:
    """Recursively clean text fields in extraction API response."""
    if isinstance(obj, dict):
        return {
            k: _clean_extraction_result(v) if k not in _TEXT_KEYS else clean_extracted_text(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_clean_extraction_result(item) for item in obj]
    return obj


class DocumentProcessingAPIClient(HttpClientBase):
    """MMC-provided Document Processing API wrapper.

    Expected responsibilities:
    - Fetch JWT token using client credentials
    - Extract text + metadata from PDFs/Word/etc for downstream processing
    """

    def __init__(self) -> None:
        super().__init__(
            base_url=settings.doc_processing_api_base_url,
            api_key=settings.doc_processing_api_key,
        )
        self.auth_base_url = "https://stg1.mmc-bedford-int-non-prod-ingress.mgti.mmc.com/authentication/v1"
        self.doc_processing_base_url = "https://stg1.mmc-dallas-int-non-prod-ingress.mgti.mmc.com/coreapi/document-processing/v1"
        self._jwt_token: str | None = None

    async def _fetch_token(self) -> str:
        """Fetch JWT token using client credentials (OAuth2).

        Returns:
            JWT token string
        """
        try:
            # Extract client_id and client_secret from settings
            # Using the doc_processing_api_key as client_secret and a derived client_id
            client_id = settings.fetch_token_username
            client_secret = settings.fetch_token_password

            url = f"{self.auth_base_url}/oauth2/token"

            # Make token request with basic auth
            import httpx

            async with httpx.AsyncClient(timeout=settings.http_timeout_s) as client:
                response = await client.post(
                    url,
                    auth=(client_id, client_secret),
                    data={"grant_type": "client_credentials"},
                )
                response.raise_for_status()
                token_data = response.json()
                self._jwt_token = token_data.get("access_token")
                logger.info("Successfully fetched JWT token for document processing")
                return self._jwt_token

        except Exception as e:
            logger.error(f"Failed to fetch JWT token: {e}")
            raise

    async def extract(
        self, filename: str, file_bytes: bytes, mime_type: str | None = None
    ) -> dict[str, Any]:
        """Extract text and metadata from document.

        Args:
            filename: Name of the file
            file_bytes: File content as bytes
            mime_type: MIME type of the file (defaults to application/octet-stream)

        Returns:
            Extracted document data
        """
        try:
            # Fetch token if not already cached
            if not self._jwt_token:
                await self._fetch_token()

            # Prepare request body
            body = {
                "filename": filename,
                "mime_type": mime_type or "application/octet-stream",
                "content_b64": base64.b64encode(file_bytes).decode("utf-8"),
            }

            # Make request with bearer token
            import httpx

            headers = {
                "Authorization": f"Bearer {self._jwt_token}",
                "x-api-key": settings.doc_processing_api_key,
            }

            async with httpx.AsyncClient(timeout=settings.http_timeout_s) as client:
                response = await client.post(
                    f"{self.doc_processing_base_url}/documents/extract",
                    json=body,
                    headers=headers,
                )
                response.raise_for_status()
                logger.info(f"Successfully extracted text from {filename}")
                result = response.json()
                result = _clean_extraction_result(result)
                return result

        except Exception as e:
            logger.error(f"Document extraction failed for {filename}: {e}")
            # Reset token on failure to retry with fresh token next time
            self._jwt_token = None
            raise

    async def upload(
        self, filename: str, file_bytes: bytes, mime_type: str | None = None
    ) -> dict[str, Any]:
        """Upload a document. Returns file ID for use with extract, summarize, etc.

        Args:
            filename: Name of the file
            file_bytes: File content as bytes
            mime_type: MIME type of the file (defaults to application/octet-stream)

        Returns:
            Upload response containing file/document ID
        """
        try:
            if not self._jwt_token:
                await self._fetch_token()

            body = {
                "filename": filename,
                "mime_type": mime_type or "application/octet-stream",
                "content_b64": base64.b64encode(file_bytes).decode("utf-8"),
            }

            import httpx

            headers = {
                "Authorization": f"Bearer {self._jwt_token}",
                "x-api-key": settings.doc_processing_api_key,
            }

            async with httpx.AsyncClient(timeout=settings.http_timeout_s) as client:
                response = await client.post(
                    f"{self.doc_processing_base_url}/documents/upload",
                    json=body,
                    headers=headers,
                )
                response.raise_for_status()
                logger.info(f"Successfully uploaded {filename}")
                return response.json()

        except Exception as e:
            logger.error(f"Document upload failed for {filename}: {e}")
            self._jwt_token = None
            raise
