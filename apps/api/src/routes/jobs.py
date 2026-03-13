from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
import pandas as pd
from difflib import SequenceMatcher
from fastapi import Body
from src.core.security import Principal, get_principal
from src.services.mmc_jobs import JobService
from src.schemas.requests import CreateJobRequest, UpdateJobRequest
from src.utility.helper import fix_headers_in_dataframe


router = APIRouter(prefix="/jobs", tags=["jobs"])


def _detect_column_match(
    column_name: str, keywords: list[str], threshold: float = 0.6
) -> bool:
    """
    Detect if a column name matches any of the keywords using fuzzy matching.

    Args:
        column_name: The column name to match
        keywords: List of keywords to match against
        threshold: Similarity threshold (0-1)

    Returns:
        True if the column matches any keyword above the threshold
    """
    col_lower = column_name.lower().strip()
    for keyword in keywords:
        keyword_lower = keyword.lower().strip()
        similarity = SequenceMatcher(None, col_lower, keyword_lower).ratio()
        if (
            similarity >= threshold
            or keyword_lower in col_lower
            or col_lower in keyword_lower
        ):
            return True
    return False


def _detect_excel_columns(df: pd.DataFrame) -> dict[str, str]:
    """
    Automatically detect job title, job code, and job description columns.

    Args:
        df: DataFrame from Excel file

    Returns:
        Dictionary with detected column mappings
    """
    columns = df.columns.tolist()
    result = {
        "job_title_column": None,
        "job_code_column": None,
        "job_description_column": None,
        "available_columns": columns,
        "confidence": {},
    }

    job_title_keywords = [
        "job title",
        "position",
        "title",
        "job_title",
        "position_title",
        "job name",
    ]
    job_code_keywords = ["job code", "code", "job_code", "code_number", "position_code"]
    job_desc_keywords = [
        "job description",
        "description",
        "job_desc",
        "job_description",
        "duties",
        "responsibilities",
    ]

    for col in columns:
        if _detect_column_match(col, job_title_keywords):
            result["job_title_column"] = col
            result["confidence"]["job_title"] = "high"

        if _detect_column_match(col, job_code_keywords):
            result["job_code_column"] = col
            result["confidence"]["job_code"] = "high"

        if _detect_column_match(col, job_desc_keywords):
            result["job_description_column"] = col
            result["confidence"]["job_description"] = "high"

    return result


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    principal: Principal = Depends(get_principal),
):
    """Get a specific job by ID"""
    try:
        job_service = JobService()
        job = job_service.get_job_by_id(job_id)
        job_service.close()

        return {
            "status": "success",
            "data": job,
        }
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to fetch job: {str(e)}",
        }


@router.post("/create_job")
async def create_job(
    job_data: CreateJobRequest,
    principal: Principal = Depends(get_principal),
):
    """Create a new job"""
    try:
        job_service = JobService()
        created_job = job_service.create_job(job_data.model_dump())
        job_service.close()

        return {
            "status": "success",
            "message": "Job created successfully",
            "data": created_job,
        }
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to create job: {str(e)}",
        }


@router.put("/{job_id}")
async def update_job(
    job_id: str,
    job_data: UpdateJobRequest,
    principal: Principal = Depends(get_principal),
):
    """Update an existing job"""
    try:
        job_service = JobService()
        updated_job = job_service.update_job(
            job_id, job_data.model_dump(exclude_unset=True)
        )
        job_service.close()

        return {
            "status": "success",
            "message": "Job updated successfully",
            "data": updated_job,
        }
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to update job: {str(e)}",
        }


@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    principal: Principal = Depends(get_principal),
):
    """Delete a job by ID"""
    try:
        job_service = JobService()
        result = job_service.delete_job(job_id)
        job_service.close()

        return {
            "status": "success",
            "message": "Job deleted successfully",
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
            "message": f"Failed to delete job: {str(e)}",
        }


@router.post("/catalog")
async def get_job_catalog_fields(
    filter: dict = Body(
        ...,
        description="""Get job catalog fields: jobCode, jobTitle, familyCode, subFamilyTitle. Filter results using a JSON body. Supports $in for list values.
    Example
{
  "jobTitle": ["Chair of the Board"]
}
    """,
    ),
    principal: Principal = Depends(get_principal),
):
    """Get job catalog fields: jobCode, jobTitle, familyCode, subFamilyTitle. Filter results using a JSON body. Supports $in for list values.
    {
      "jobTitle": ["executive", "manager"]
    }
    This will return all catalog entries where the jobTitle field contains either "executive" or "manager" as a substring.
    """
    try:
        job_service = JobService()
        mongo_filter = {}
        # Convert list values to $or regex queries for 'like' matching
        for k, v in filter.items():
            if isinstance(v, list):
                # $or for regex partial match
                mongo_filter["$or"] = mongo_filter.get("$or", [])
                for val in v:
                    mongo_filter["$or"].append({k: {"$regex": val, "$options": "i"}})
            else:
                # Single value: regex partial match
                mongo_filter[k] = {"$regex": v, "$options": "i"}
        fields = job_service.get_job_catalog_fields(filter=mongo_filter)
        job_service.close()
        return {
            "status": "success",
            "data": fields,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to fetch job catalog fields: {str(e)}",
        }


@router.post("/bulk/detect-columns")
async def detect_excel_columns(
    file: UploadFile = File(...),
    sheet_name: str | int = 0,
    principal: Principal = Depends(get_principal),
):
    """Detect and suggest column mappings from an Excel file

    Returns available columns and automatically detects:
    - job_title_column
    - job_code_column
    - job_description_column

    Query parameters:
    - sheet_name: Sheet name or index to read (default: 0 for first sheet)
    """
    try:
        # Read Excel file
        content = await file.read()
        df = pd.read_excel(content, sheet_name=sheet_name, nrows=100)
        df = fix_headers_in_dataframe(df)

        if df.empty:
            return {
                "status": "error",
                "message": "Excel file is empty",
            }

        # Detect columns
        column_mapping = _detect_excel_columns(df)

        return {
            "status": "success",
            "data": column_mapping,
            "sample_row": df.iloc[0].to_dict() if len(df) > 0 else None,
            "total_rows": len(df),
            "message": "Columns detected successfully",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to detect columns: {str(e)}",
        }


@router.post("/bulk")
async def bulk_insert_jobs(
    project_id: str,
    Jobs_file: UploadFile = File(...),
    sheet_name: str | int = 0,
    job_title_column: str = None,
    job_code_column: str = None,
    job_description_column: str = None,
    principal: Principal = Depends(get_principal),
):
    """Bulk insert jobs from an Excel file with automatic column detection

    The Excel file columns will be automatically detected for:
    - Job title (job title, position, title, etc.)
    - Job code (job code, code, position_code, etc.)
    - Job description (job description, description, duties, etc.)

    Query parameters:
    - project_id (required): Project ID for all jobs
    - sheet_name: Sheet name or index to read (default: 0 for first sheet)
    - job_title_column (optional): Override auto-detected job title column name
    - job_code_column (optional): Override auto-detected job code column name
    - job_description_column (optional): Override auto-detected job description column name
    """
    try:
        if not project_id:
            return {
                "status": "error",
                "message": "project_id is required",
            }

        # Read Excel file
        content = await Jobs_file.read()
        df = pd.read_excel(content, engine="openpyxl", sheet_name=sheet_name)
        df = fix_headers_in_dataframe(df)

        if df.empty:
            return {
                "status": "error",
                "message": "Excel file is empty",
            }

        # Auto-detect columns if not provided
        if not job_title_column or not job_description_column:
            detected = _detect_excel_columns(df)
            job_title_column = job_title_column or detected.get("job_title_column")
            job_code_column = job_code_column or detected.get("job_code_column")
            job_description_column = job_description_column or detected.get(
                "job_description_column"
            )

        # Validate detected columns
        if not job_title_column:
            return {
                "status": "error",
                "message": "Could not detect job title column. Please specify 'job_title_column' parameter. Available columns: "
                + ", ".join(df.columns.tolist()),
            }

        if not job_description_column:
            return {
                "status": "error",
                "message": "Could not detect job description column. Please specify 'job_description_column' parameter. Available columns: "
                + ", ".join(df.columns.tolist()),
            }

        # Validate columns exist in dataframe
        missing_cols = []
        for col in [job_title_column, job_description_column]:
            if col not in df.columns:
                missing_cols.append(col)

        if missing_cols:
            return {
                "status": "error",
                "message": f"Columns not found in Excel file: {', '.join(missing_cols)}. Available columns: "
                + ", ".join(df.columns.tolist()),
            }

        # Convert DataFrame rows to list of dictionaries
        jobs_data = []
        for idx, row in df.iterrows():
            job = {
                "project_id": project_id,
            }

            # Add job code if detected
            if (
                job_code_column
                and job_code_column in df.columns
                and pd.notna(row.get(job_code_column))
            ):
                job["job_code"] = row[job_code_column]

            if (
                job_title_column
                and job_code_column in df.columns
                and pd.notna(row.get(job_title_column))
            ):
                job["job_title"] = row[job_title_column]

            if (
                job_description_column
                and job_description_column in df.columns
                and pd.notna(row.get(job_description_column))
            ):
                job["job_description"] = row[job_description_column]

            # Add other columns that aren't already mapped
            tags = {}
            for col in df.columns:
                if col not in [
                    job_title_column,
                    job_description_column,
                    job_code_column,
                ]:
                    if pd.notna(row[col]):
                        tags[col] = row[col]
            job["tags"] = tags
            jobs_data.append(job)

        # Perform bulk insert with project_id
        job_service = JobService()
        result = job_service.bulk_insert(jobs_data, project_id=project_id)
        job_service.close()

        return {
            "status": "success",
            "message": f"Successfully imported {result['count']} jobs for project {project_id}",
            "data": result,
            "column_mapping": {
                "job_title": job_title_column,
                "job_code": job_code_column,
                "job_description": job_description_column,
            },
        }
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to bulk insert jobs: {str(e)}",
        }
