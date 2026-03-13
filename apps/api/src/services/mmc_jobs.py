# CRUD services for MMC Jobs
from __future__ import annotations


import logging
from typing import Any
from pymongo import MongoClient
from bson import ObjectId
from src.core.config import settings


logger = logging.getLogger(__name__)


def _serialize_mongo_doc(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    """Convert MongoDB document to JSON-serializable format

    Converts ObjectId fields to strings so FastAPI can serialize the response.
    """
    if doc is None:
        return None

    serialized = {}
    for key, value in doc.items():
        # Convert ObjectId to string for JSON serialization
        if isinstance(value, ObjectId):
            serialized[key] = str(value)
        elif isinstance(value, dict):
            serialized[key] = _serialize_mongo_doc(value)
        elif isinstance(value, list):
            serialized[key] = [
                _serialize_mongo_doc(item)
                if isinstance(item, dict)
                else (str(item) if isinstance(item, ObjectId) else item)
                for item in value
            ]
        else:
            serialized[key] = value

    return serialized


class JobService:
    """Service for managing MMC Jobs"""

    def __init__(self, mongodb_uri: str = None, mongodb_database: str = None):
        """Initialize job service with MongoDB connection"""
        self.mongodb_uri = mongodb_uri or settings.mongodb_uri
        self.mongodb_database = mongodb_database or settings.mongodb_database
        self.client = MongoClient(self.mongodb_uri)
        self.db = self.client[self.mongodb_database]
        self.collection = self.db["Jobs"]
        logger.info(f"JobService connected to MongoDB: {self.db.name}")

    def get_project_jobs(
        self, project_id: str, audit: Any = None
    ) -> list[dict[str, Any]]:
        """Load jobs associated with a project from MongoDB"""
        try:
            jobs = list(self.collection.find({"project_id": project_id}))

            logger.info(f"Retrieved {len(jobs)} jobs for project: {project_id}")
            if audit:
                audit.add(
                    "get_project_jobs",
                    {"project_id": project_id, "count": len(jobs), "status": "success"},
                )
            return [_serialize_mongo_doc(job) for job in jobs]
        except Exception as e:
            logger.error(f"Error retrieving jobs for project {project_id}: {str(e)}")
            if audit:
                audit.add(
                    "get_project_jobs_error",
                    {"project_id": project_id, "error": str(e)},
                )
            raise

    def get_job_by_id(self, job_id: str, audit: Any = None) -> dict[str, Any]:
        """Get a specific job by ID"""
        try:
            # Convert job_id to ObjectId if possible
            try:
                obj_id = ObjectId(job_id)
            except Exception:
                obj_id = job_id

            job = self.collection.find_one({"_id": obj_id})

            if not job:
                raise ValueError(f"Job not found: {job_id}")

            if audit:
                audit.add("get_job_by_id", {"job_id": job_id, "status": "success"})
            return _serialize_mongo_doc(job)
        except Exception as e:
            logger.error(f"Error retrieving job {job_id}: {str(e)}")
            if audit:
                audit.add("get_job_by_id_error", {"job_id": job_id, "error": str(e)})
            raise

    def create_job(self, job_data: dict[str, Any], audit: Any = None) -> dict[str, Any]:
        """Create a new job in MongoDB

        Args:
            job_data: Job document containing fields like:
                - project_id (required): Project ID
                - job_title (required): Job title
                - job_description (required): Job description
                - mjl_title (optional): MJL title
                - other fields as needed
            audit (optional): Audit trail object for logging

        Returns:
            Created job document with _id
        """
        try:
            if not job_data.get("project_id"):
                raise ValueError("project_id is required")
            if not job_data.get("job_title"):
                raise ValueError("job_title is required")
            if not job_data.get("job_description"):
                raise ValueError("job_description is required")

            result = self.collection.insert_one(job_data)
            created_job = self.collection.find_one({"_id": result.inserted_id})

            logger.info(
                f"Created new job: {result.inserted_id} for project: {job_data.get('project_id')}"
            )
            if audit:
                audit.add(
                    "create_job",
                    {
                        "job_id": str(result.inserted_id),
                        "project_id": job_data.get("project_id"),
                        "status": "success",
                    },
                )
            return _serialize_mongo_doc(created_job)
        except Exception as e:
            logger.error(f"Error creating job: {str(e)}")
            if audit:
                audit.add(
                    "create_job_error",
                    {"project_id": job_data.get("project_id"), "error": str(e)},
                )
            raise

    def bulk_insert(
        self, jobs_data: list[dict[str, Any]], project_id: str = None, audit: Any = None
    ) -> dict[str, Any]:
        """Bulk insert multiple jobs into MongoDB

        Args:
            jobs_data: List of job documents, each containing:
                - job_title (required): Job title
                - job_description (required): Job description
                - other fields as needed
            project_id (optional): Project ID to apply to all jobs. If provided,
                                   overrides any project_id in individual job documents.
            audit (optional): Audit trail object for logging

        Returns:
            Dictionary with inserted_ids and count

        Raises:
            ValueError: If jobs_data is empty or missing required fields
        """
        try:
            if not jobs_data:
                raise ValueError("jobs_data cannot be empty")

            # Apply project_id to all jobs if provided
            if project_id:
                for job in jobs_data:
                    job["project_id"] = project_id

            # Validate required fields in each job
            for idx, job in enumerate(jobs_data):
                if not job.get("project_id"):
                    raise ValueError(
                        f"Job {idx}: project_id is required (provide as parameter or in job data)"
                    )
                if not job.get("job_title"):
                    raise ValueError(f"Job {idx}: job_title is required")

            result = self.collection.insert_many(jobs_data)

            logger.info(
                f"Bulk inserted {len(result.inserted_ids)} jobs"
                + (f" for project: {project_id}" if project_id else "")
            )
            if audit:
                audit.add(
                    "bulk_insert",
                    {
                        "count": len(result.inserted_ids),
                        "project_id": project_id,
                        "status": "success",
                    },
                )

            return {
                "inserted_ids": [str(id) for id in result.inserted_ids],
                "count": len(result.inserted_ids),
                "message": f"Successfully inserted {len(result.inserted_ids)} jobs",
            }
        except Exception as e:
            logger.error(f"Error bulk inserting jobs: {str(e)}")
            if audit:
                audit.add(
                    "bulk_insert_error",
                    {
                        "project_id": project_id,
                        "count": len(jobs_data),
                        "error": str(e),
                    },
                )
            raise

    def update_job(
        self, job_id: str, job_data: dict[str, Any], audit: Any = None
    ) -> dict[str, Any]:
        """Update an existing job

        Args:
            job_id: Job ID (MongoDB ObjectId)
            job_data: Updated job fields
            audit (optional): Audit trail object for logging

        Returns:
            Updated job document
        """
        try:
            # Convert job_id to ObjectId if possible
            try:
                obj_id = ObjectId(job_id)
            except Exception:
                obj_id = job_id

            # Verify job exists
            existing = self.collection.find_one({"_id": obj_id})
            if not existing:
                raise ValueError(f"Job not found: {job_id}")

            # Update the job
            result = self.collection.update_one({"_id": obj_id}, {"$set": job_data})

            if result.modified_count == 0:
                logger.warning(f"Job {job_id} was not modified (no changes)")
                if audit:
                    audit.add("update_job_no_change", {"job_id": job_id})
            else:
                logger.info(f"Updated job: {job_id}")
                if audit:
                    audit.add(
                        "update_job",
                        {
                            "job_id": job_id,
                            "fields_updated": list(job_data.keys()),
                            "status": "success",
                        },
                    )

            # Return updated document
            updated_job = self.collection.find_one({"_id": obj_id})
            return _serialize_mongo_doc(updated_job)
        except Exception as e:
            logger.error(f"Error updating job {job_id}: {str(e)}")
            if audit:
                audit.add("update_job_error", {"job_id": job_id, "error": str(e)})
            raise

    def delete_job(self, job_id: str, audit: Any = None) -> dict[str, Any]:
        """Delete a job from MongoDB

        Args:
            job_id: Job ID (MongoDB ObjectId)
            audit (optional): Audit trail object for logging

        Returns:
            Confirmation with deleted job count
        """
        try:
            # Convert job_id to ObjectId if possible
            try:
                obj_id = ObjectId(job_id)
            except Exception:
                obj_id = job_id

            # Get job before deletion for logging
            job = self.collection.find_one({"_id": obj_id})
            if not job:
                raise ValueError(f"Job not found: {job_id}")

            result = self.collection.delete_one({"_id": obj_id})

            logger.info(f"Deleted job: {job_id}")
            if audit:
                audit.add(
                    "delete_job",
                    {
                        "job_id": job_id,
                        "project_id": job.get("project_id"),
                        "status": "success",
                    },
                )

            return {
                "deleted_count": result.deleted_count,
                "job_id": job_id,
                "message": f"Job {job_id} deleted successfully",
            }
        except Exception as e:
            logger.error(f"Error deleting job {job_id}: {str(e)}")
            if audit:
                audit.add("delete_job_error", {"job_id": job_id, "error": str(e)})
            raise

    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("JobService MongoDB connection closed")

    def get_job_catalog_fields(
        self, filter: dict[str, Any] = None
    ) -> list[dict[str, Any]]:
        """Get jobCode, jobTitle, familyCode, and subFamilyTitle from jobCatalog collection."""
        try:
            catalog = self.db["jobCatalog"]
            query = filter if filter else {}
            projection = {
                "_id": 0,
                "jobCode": 1,
                "jobTitle": 1,
                "familyCode": 1,
                "subFamilyTitle": 1,
            }
            results = list(
                catalog.find(query, projection).sort(
                    [("familyCode", 1), ("subFamilyTitle", 1)]
                )
            )
            return results
        except Exception as e:
            logger.error(f"Error fetching job catalog fields: {str(e)}")
            raise
