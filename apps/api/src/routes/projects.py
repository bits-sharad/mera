from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile

from src.clients.doc_processing_api import DocumentProcessingAPIClient
from src.core.security import Principal, get_principal
from src.services.mmc_project import ProjectService
from src.services.mmc_jobs import JobService
from src.schemas.requests import CreateProjectRequest, UpdateProjectRequest


def _doc_processing() -> DocumentProcessingAPIClient:
    return DocumentProcessingAPIClient()


router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/list_projects")
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    principal: Principal = Depends(get_principal),
):
    """Get a list of all projects with pagination"""
    try:
        project_service = ProjectService()
        projects = project_service.get_project_list(skip=skip, limit=limit)
        project_service.close()

        return {
            "status": "success",
            "total": len(projects),
            "skip": skip,
            "limit": limit,
            "data": projects,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to fetch projects: {str(e)}",
        }


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    principal: Principal = Depends(get_principal),
):
    """Get project details by project ID"""
    try:
        project_service = ProjectService()
        project = project_service.get_project_details(project_id)
        project_service.close()

        return {
            "status": "success",
            "data": project,
        }
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to fetch project: {str(e)}",
        }


@router.get("/{project_id}/jobs")
async def get_project_jobs(
    project_id: str,
    principal: Principal = Depends(get_principal),
):
    """Get all jobs for a specific project"""
    try:
        job_service = JobService()
        jobs = job_service.get_project_jobs(project_id)
        job_service.close()

        return {
            "status": "success",
            "project_id": project_id,
            "total_jobs": len(jobs),
            "data": jobs,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to fetch jobs: {str(e)}",
        }


@router.post("/create_project")
async def create_project(
    project_data: CreateProjectRequest,
    principal: Principal = Depends(get_principal),
):
    """Create a new project"""
    try:
        project_service = ProjectService()
        created_project = project_service.create_project(project_data.model_dump())
        project_service.close()

        return {
            "status": "success",
            "message": "Project created successfully",
            "data": created_project,
        }
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to create project: {str(e)}",
        }


@router.put("/{project_id}")
async def update_project(
    project_id: str,
    project_data: UpdateProjectRequest,
    principal: Principal = Depends(get_principal),
):
    """Update an existing project"""
    try:
        project_service = ProjectService()
        updated_project = project_service.update_project(
            project_id, project_data.model_dump(exclude_unset=True)
        )
        project_service.close()

        return {
            "status": "success",
            "message": "Project updated successfully",
            "data": updated_project,
        }
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to update project: {str(e)}",
        }


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    principal: Principal = Depends(get_principal),
):
    """Delete a project by ID"""
    try:
        project_service = ProjectService()
        result = project_service.delete_project(project_id)
        project_service.close()

        return {
            "status": "success",
            "message": "Project deleted successfully",
            "data": result,
        }
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to delete project: {str(e)}",
        }


@router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    principal: Principal = Depends(get_principal),
    doc_client: DocumentProcessingAPIClient = Depends(_doc_processing),
):
    """Upload a single document. Returns file ID for use with extract, summarize, etc."""
    try:
        content = await file.read()
        result = await doc_client.upload(
            file.filename or "document",
            content,
            mime_type=file.content_type,
        )
        file_id = result.get("file_id") or result.get("document_id") or result.get("id")
        return {
            "status": "success",
            "message": "File uploaded successfully",
            "file_id": file_id,
            "data": result,
        }
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to upload file: {str(e)}",
        }


@router.post("/files/extract")
async def extract_file(
    file: UploadFile = File(...),
    principal: Principal = Depends(get_principal),
    doc_client: DocumentProcessingAPIClient = Depends(_doc_processing),
):
    """Extract text from document. Returns cleaned text (URLs, image links, control chars removed)."""
    try:
        content = await file.read()
        result = await doc_client.extract(
            file.filename or "document",
            content,
            mime_type=file.content_type,
        )
        return {
            "status": "success",
            "message": "Text extracted and cleaned successfully",
            "data": result,
        }
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to extract text: {str(e)}",
        }


@router.post("/files/upload-multiple")
async def upload_files(
    files: list[UploadFile] = File(...),
    principal: Principal = Depends(get_principal),
    doc_client: DocumentProcessingAPIClient = Depends(_doc_processing),
):
    """Upload multiple documents. Returns file IDs for use with extract, summarize, etc."""
    try:
        results = []
        for upload_file_item in files:
            content = await upload_file_item.read()
            result = await doc_client.upload(
                upload_file_item.filename or "document",
                content,
                mime_type=upload_file_item.content_type,
            )
            file_id = result.get("file_id") or result.get("document_id") or result.get("id")
            results.append(
                {
                    "filename": upload_file_item.filename or "document",
                    "file_id": file_id,
                    "result": result,
                }
            )
        return {
            "status": "success",
            "message": f"Successfully uploaded {len(results)} file(s)",
            "data": results,
        }
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to upload files: {str(e)}",
        }
