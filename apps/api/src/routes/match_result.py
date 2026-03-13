from fastapi import APIRouter, Query
from src.services.mjl.match_result import MatchResultService
from src.utility.helper import _serialize_mongo_doc


router = APIRouter(prefix="/match_results", tags=["match_results"])


@router.get("/by_project/{project_id}")
def get_matches_by_project(project_id: str):
    """Return all match results for a given project_id, sorted by bestMatch.confidence descending."""
    try:
        service = MatchResultService()
        # Sort by bestMatch.confidence descending
        matches = list(
            service.collection.find({"project_id": project_id}).sort(
                [("bestMatch.confidence", -1)]
            )
        )
        service.close()
        return {
            "status": "success",
            "count": len(matches),
            "data": [_serialize_mongo_doc(m) for m in matches],
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to fetch match results: {str(e)}",
        }


@router.get("/by_job/{job_id}")
def get_matches_by_Jobid(job_id: str):
    """Return all match results for a given job_id, sorted by bestMatch.confidence descending."""
    try:
        service = MatchResultService()
        # Sort by bestMatch.confidence descending
        matches = list(
            service.collection.find({"companyJobId": job_id}).sort(
                [("bestMatch.confidence", -1)]
            )
        )
        service.close()
        return {
            "status": "success",
            "count": len(matches),
            "data": [_serialize_mongo_doc(m) for m in matches],
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to fetch match results: {str(e)}",
        }

@router.get("/by_job/{job_id}")
def update_match_result(job_id: str):
    """Return all match results for a given job_id, sorted by bestMatch.confidence descending."""
    try:
        service = MatchResultService()
        matches = list(
            service.collection.find({"companyJobId": job_id}).sort(
                [("bestMatch.confidence", -1)]
            )
        )
        service.close()
        return {
            "status": "success",
            "count": len(matches),
            "data": [_serialize_mongo_doc(m) for m in matches[:3]],
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to fetch match results: {str(e)}",
        }
