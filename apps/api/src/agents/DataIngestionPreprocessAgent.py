from __future__ import annotations

import io
import logging
from typing import Any, Dict

import httpx
import pandas as pd

from src.agents.base import AgentBase
from src.core.audit import AuditTrail
from src.schemas.common import AgentResult
from src.services.mmc_jobs import JobService
from src.services.mmc_project import ProjectService
from src.utility.helper import (
    clean_extracted_text,
    extract_jobs_from_dataframe,
    fix_headers_in_dataframe,
)

logger = logging.getLogger(__name__)


class DataIngestionPreprocessingAgent(AgentBase):
    """Agent that extracts text, normalizes it, and/or processes census files.

    Two modes:
    1. Document mode (state.document_extracted): Extract text from document, normalize
       (remove URLs, image links, control chars, etc.), return normalized_text.
    2. Census mode (state.project_id): Process unprocessed census Excel files,
       bulk insert jobs, mark is_processed=true.
    """

    name = "data_ingestion_preprocessing"

    async def _extract_and_normalize_document(
        self, state: Dict[str, Any], audit: AuditTrail
    ) -> AgentResult | None:
        """Extract text from document_extracted and normalize. Returns AgentResult or None if not applicable."""
        document_extracted = state.get("document_extracted") or {}
        if not document_extracted:
            return None

        text = document_extracted.get("text") or document_extracted.get("content") or ""

        # If no text but we have file_url, fetch and extract via Document Processing API
        if not text and document_extracted.get("file_url"):
            file_url = document_extracted.get("file_url")
            filename = document_extracted.get("filename", "document")
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(file_url)
                    response.raise_for_status()
                    content = response.content
            except Exception as e:
                logger.error(f"Failed to fetch document from {file_url}: {e}")
                audit.add("document_fetch_error", {"file_url": file_url, "error": str(e)})
                return AgentResult(
                    agent=self.name,
                    output={
                        "status": "error",
                        "message": str(e),
                        "normalized_text": "",
                    },
                    rationale=str(e),
                )

            try:
                from src.clients.doc_processing_api import DocumentProcessingAPIClient

                doc_client = DocumentProcessingAPIClient()
                result = await doc_client.extract(
                    filename,
                    content,
                    mime_type=document_extracted.get("mime_type"),
                )
                # Extract API already applies clean_extracted_text; get text from result
                text = (
                    result.get("text")
                    or result.get("content")
                    or result.get("extracted_text")
                    or ""
                )
                if isinstance(text, list):
                    text = " ".join(str(t) for t in text)
            except Exception as e:
                logger.error(f"Failed to extract text from {filename}: {e}")
                audit.add("document_extract_error", {"filename": filename, "error": str(e)})
                return AgentResult(
                    agent=self.name,
                    output={
                        "status": "error",
                        "message": str(e),
                        "normalized_text": "",
                    },
                    rationale=str(e),
                )

        normalized_text = clean_extracted_text(text)
        audit.add(
            "document_normalized",
            {"chars_before": len(text), "chars_after": len(normalized_text)},
        )

        return AgentResult(
            agent=self.name,
            output={
                "status": "success",
                "normalized_text": normalized_text,
                "doc_metadata": document_extracted.get("metadata", {}),
            },
            rationale="Text extracted and normalized",
        )

    async def run(self, state: Dict[str, Any], audit: AuditTrail) -> AgentResult:
        audit.add("agent_start", {"agent": self.name})

        # Mode 1: Document extraction and normalization (for ingestion_node)
        doc_result = await self._extract_and_normalize_document(state, audit)
        if doc_result is not None:
            audit.add("agent_end", {"agent": self.name, "mode": "document"})
            return doc_result

        # Mode 2: Census processing
        project_id = state.get("project_id")
        if not project_id:
            audit.add("agent_end", {"agent": self.name, "error": "project_id required"})
            return AgentResult(
                agent=self.name,
                output={
                    "status": "error",
                    "message": "project_id is required in state",
                    "processed_count": 0,
                },
                rationale="project_id is required",
            )

        project_service = ProjectService()
        job_service = JobService()

        try:
            census_docs = project_service.get_unprocessed_census_documents(
                project_id, audit=audit
            )
        except Exception as e:
            logger.error(f"Failed to get unprocessed census: {e}")
            project_service.close()
            job_service.close()
            audit.add("agent_end", {"agent": self.name, "error": str(e)})
            return AgentResult(
                agent=self.name,
                output={
                    "status": "error",
                    "message": str(e),
                    "processed_count": 0,
                },
                rationale=str(e),
            )

        if not census_docs:
            project_service.close()
            job_service.close()
            audit.add(
                "agent_end",
                {"agent": self.name, "processed_count": 0, "reason": "no_unprocessed"},
            )
            return AgentResult(
                agent=self.name,
                output={
                    "status": "success",
                    "message": "No unprocessed census documents found",
                    "processed_count": 0,
                    "files_processed": [],
                },
                rationale="No unprocessed census documents",
            )

        files_processed = []
        total_jobs_inserted = 0

        for doc, doc_index in census_docs:
            file_url = doc.get("file_url")
            file_name = doc.get("file_name", "census.xlsx")

            if not file_url:
                logger.warning(f"Census document at index {doc_index} has no file_url")
                audit.add("census_skip", {"index": doc_index, "reason": "no_file_url"})
                continue

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(file_url)
                    response.raise_for_status()
                    content = response.content
            except Exception as e:
                logger.error(f"Failed to fetch census file {file_url}: {e}")
                audit.add(
                    "census_fetch_error",
                    {"file_url": file_url, "index": doc_index, "error": str(e)},
                )
                continue

            try:
                df = pd.read_excel(io.BytesIO(content), engine="openpyxl", sheet_name=0)
                df, _ = fix_headers_in_dataframe(df)

                if df.empty:
                    audit.add(
                        "census_skip",
                        {"index": doc_index, "file_name": file_name, "reason": "empty"},
                    )
                    project_service.mark_document_as_processed(
                        project_id, doc_index, audit=audit
                    )
                    files_processed.append(
                        {"file_name": file_name, "jobs_inserted": 0, "status": "empty"}
                    )
                    continue

                jobs_data = extract_jobs_from_dataframe(df, project_id)

                if not jobs_data:
                    audit.add(
                        "census_skip",
                        {
                            "index": doc_index,
                            "file_name": file_name,
                            "reason": "no_jobs_extracted",
                        },
                    )
                    project_service.mark_document_as_processed(
                        project_id, doc_index, audit=audit
                    )
                    files_processed.append(
                        {
                            "file_name": file_name,
                            "jobs_inserted": 0,
                            "status": "no_jobs_extracted",
                        }
                    )
                    continue

                result = job_service.bulk_insert(
                    jobs_data, project_id=project_id, audit=audit
                )
                inserted_count = result.get("count", 0)
                total_jobs_inserted += inserted_count

                project_service.mark_document_as_processed(
                    project_id, doc_index, audit=audit
                )

                audit.add(
                    "census_processed",
                    {
                        "file_name": file_name,
                        "index": doc_index,
                        "jobs_inserted": inserted_count,
                        "status": "success",
                    },
                )
                files_processed.append(
                    {
                        "file_name": file_name,
                        "jobs_inserted": inserted_count,
                        "status": "success",
                    }
                )

            except Exception as e:
                logger.error(f"Failed to process census {file_name}: {e}")
                audit.add(
                    "census_process_error",
                    {"file_name": file_name, "index": doc_index, "error": str(e)},
                )
                files_processed.append(
                    {"file_name": file_name, "jobs_inserted": 0, "status": "error", "error": str(e)}
                )

        project_service.close()
        job_service.close()

        audit.add(
            "agent_end",
            {
                "agent": self.name,
                "processed_count": len(files_processed),
                "total_jobs_inserted": total_jobs_inserted,
            },
        )

        return AgentResult(
            agent=self.name,
            output={
                "status": "success",
                "message": f"Processed {len(files_processed)} census file(s), inserted {total_jobs_inserted} jobs",
                "processed_count": len(files_processed),
                "total_jobs_inserted": total_jobs_inserted,
                "files_processed": files_processed,
            },
            rationale=f"Processed {len(files_processed)} census files, {total_jobs_inserted} jobs inserted",
        )
