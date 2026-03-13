from __future__ import annotations

from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(
        ..., description="Conversation/session identifier for history & personalization"
    )
    user_query: str
    user_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context. Supports: project_id (str), job_ids (list[str])",
    )
    # Optional routing hint, otherwise the orchestrator infers intent.
    task: str | None = Field(
        default=None, description="classification|grading|matching|job_description|auto"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session-123",
                "user_query": "job matching for project id 1",
                "user_context": {"project_id": "1"},
                "task": "auto",
            }
        }


class UploadRequest(BaseModel):
    session_id: str
    filename: str
    mime_type: str | None = None


class ClientDataRequest(BaseModel):
    """Client information nested in project"""

    company_name: str | None = Field(None, description="Name of the company")
    company_weburl: str | None = Field(None, description="Company website URL")
    notes: str | None = Field(None, description="Additional notes about the client")


class OperationsTagsRequest(BaseModel):
    """Operations tags nested in project tags"""

    job_matching: int | None = Field(None, description="Job matching operation flag")
    job_grading: int | None = Field(None, description="Job grading operation flag")
    job_description: int | None = Field(
        None, description="Job description operation flag"
    )


class ProjectTagsRequest(BaseModel):
    """Tags nested in project"""

    operations: OperationsTagsRequest | None = Field(
        None, description="Operations tags"
    )
    concerns: str | None = Field(None, description="Project concerns")
    regulatory_req: str | None = Field(None, description="Regulatory requirements")


class DocumentRequest(BaseModel):
    """Document information nested in project"""

    file_name: str = Field(..., description="Document file name")
    file_url: str = Field(..., description="Document file URL")
    uploaded_by: str = Field(..., description="User who uploaded the document")
    upload_date: datetime | None = Field(None, description="Document upload date")
    type: str = Field(
        ..., description="Document type (e.g., Census, Job Descriptions)"
    )
    notes: str | None = Field(None, description="Additional notes about the document")
    is_processed: bool | None = Field(
        None,
        description="Whether census/job document has been processed (extracted and bulk-inserted). Default False for Census.",
    )


class CreateProjectRequest(BaseModel):
    """Request model for creating a project"""

    projet_id: str = Field(..., description="Unique project identifier")
    project_name: str = Field(..., description="Name of the project")
    project_code: str | None = Field(None, description="Project code")
    project_description: str | None = Field(None, description="Project description")
    client_data: ClientDataRequest | None = Field(
        None, description="Client information"
    )
    start_date: datetime | None = Field(None, description="Project start date")
    end_date: datetime | None = Field(None, description="Project end date")
    status: int | None = Field(1, description="Project status code")
    Analysts: list[int] | None = Field(None, description="List of analyst IDs")
    Reviewers: list[int] | None = Field(None, description="List of reviewer IDs")
    tags: ProjectTagsRequest | None = Field(
        None, description="Project tags and metadata"
    )
    documents: list[DocumentRequest] | None = Field(
        None, description="Project documents"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "projet_id": "PROJ001",
                "project_name": "Job Matching Model POC",
                "project_code": "JMM-POC",
                "project_description": "Proof of concept for job matching and grading system",
                "client_data": {
                    "company_name": "Example Company",
                    "company_weburl": "https://example.com",
                    "notes": "Initial project setup",
                },
                "start_date": "2025-01-01T00:00:00Z",
                "end_date": "2025-06-30T00:00:00Z",
                "status": 1,
                "Analysts": [1, 2, 3],
                "Reviewers": [4, 5],
                "tags": {
                    "operations": {
                        "job_matching": 1,
                        "job_grading": 0,
                        "job_description": 0,
                    },
                    "concerns": "skill gap",
                    "regulatory_req": "gdpr",
                },
                "documents": [
                    {
                        "file_name": "project_plan.pdf",
                        "file_url": "https://example.com/project_plan.pdf",
                        "uploaded_by": "admin",
                        "type": "Employee List",
                        "notes": "Initial project plan document",
                    }
                ],
            }
        }


class UpdateProjectRequest(BaseModel):
    """Request model for updating a project"""

    project_name: str | None = Field(None, description="Updated project name")
    project_code: str | None = Field(None, description="Updated project code")
    project_description: str | None = Field(
        None, description="Updated project description"
    )
    client_data: ClientDataRequest | None = Field(
        None, description="Updated client information"
    )
    start_date: datetime | None = Field(None, description="Updated project start date")
    end_date: datetime | None = Field(None, description="Updated project end date")
    status: int | None = Field(None, description="Updated project status code")
    Analysts: list[int] | None = Field(None, description="Updated analyst IDs")
    Reviewers: list[int] | None = Field(None, description="Updated reviewer IDs")
    tags: ProjectTagsRequest | None = Field(None, description="Updated project tags")
    documents: list[DocumentRequest] | None = Field(
        None, description="Updated project documents"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "project_name": "Updated Project Name",
                "status": 2,
                "Analysts": [1, 2, 3, 6],
            }
        }


class CreateJobRequest(BaseModel):
    """Request model for creating a job"""

    project_id: str = Field(..., description="Project ID for the job")
    job_title: str = Field(..., description="Job title")
    job_description: str = Field(..., description="Full description of the job")
    job_code: str | None = Field(None, description="Optional job code")
    mjl_title: str | None = Field(None, description="Optional MJL title")

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "PROJECT123",
                "job_title": "Software Engineer",
                "job_description": "Full description of the job...",
                "job_code": "ENG001",
                "mjl_title": "Optional MJL title",
            }
        }


class UpdateJobRequest(BaseModel):
    """Request model for updating a job"""

    job_title: str | None = Field(None, description="Updated job title")
    job_description: str | None = Field(None, description="Updated job description")
    job_code: str | None = Field(None, description="Updated job code")
    mjl_title: str | None = Field(None, description="Updated MJL title")

    class Config:
        json_schema_extra = {
            "example": {
                "job_title": "Senior Software Engineer",
                "job_description": "Updated description...",
            }
        }
