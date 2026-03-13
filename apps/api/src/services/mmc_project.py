# CRUD services for MMC Projects
from __future__ import annotations


import logging
from typing import Any
from pymongo import MongoClient
from bson import ObjectId
from src.core.config import settings


logger = logging.getLogger(__name__)


def _serialize_mongo_doc(doc: dict[str, Any]) -> dict[str, Any]:
    """Convert MongoDB document to JSON-serializable format

    Converts MongoDB document fields to JSON-serializable format.
    """
    if doc is None:
        return None

    serialized = {}

    for key, value in doc.items():
        # Ensure project_name is always a string
        if key == "project_name":
            serialized[key] = str(value) if value is not None else ""
        # Convert ObjectId to string for JSON serialization
        elif isinstance(value, ObjectId):
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


class ProjectService:
    """Service for managing MMC Projects"""

    def __init__(self, mongodb_uri: str = None, mongodb_database: str = None):
        """Initialize project service with MongoDB connection"""
        self.mongodb_uri = mongodb_uri or settings.mongodb_uri
        self.mongodb_database = mongodb_database or settings.mongodb_database
        self.client = MongoClient(self.mongodb_uri)
        self.db = self.client[self.mongodb_database]
        self.collection = self.db["Projects"]
        logger.info(f"ProjectService connected to MongoDB: {self.db.name}")

    def get_project_details(self, project_id: str, audit: Any = None) -> dict[str, Any]:
        """Load project details from MongoDB by _id"""
        try:
            # Convert project_id to ObjectId if possible
            try:
                obj_id = ObjectId(project_id)
            except Exception:
                obj_id = project_id

            project = self.collection.find_one({"_id": obj_id})

            if not project:
                raise ValueError(f"Project not found: {project_id}")

            logger.info(f"Retrieved project: {project.get('project_name')}")
            if audit:
                audit.add(
                    "get_project_details",
                    {
                        "project_id": project_id,
                        "project_name": project.get("project_name"),
                        "status": "success",
                    },
                )
            return _serialize_mongo_doc(project)
        except Exception as e:
            logger.error(f"Error retrieving project {project_id}: {str(e)}")
            if audit:
                audit.add(
                    "get_project_details_error",
                    {"project_id": project_id, "error": str(e)},
                )
            raise

    def get_project_by_id(self, project_id: str, audit: Any = None) -> dict[str, Any]:
        """Alias for get_project_details"""
        return self.get_project_details(project_id, audit=audit)

    def get_unprocessed_census_documents(
        self, project_id: str, audit: Any = None
    ) -> list[tuple[dict[str, Any], int]]:
        """Get census documents where is_processed is False or not set.

        Returns:
            List of (document, index) tuples for unprocessed census documents.
        """
        try:
            project = self.get_project_details(project_id, audit=audit)
            documents = project.get("documents") or []
            result = []
            for idx, doc in enumerate(documents):
                if doc.get("type") != "Census":
                    continue
                if doc.get("is_processed") is True:
                    continue
                result.append((doc, idx))
            if audit:
                audit.add(
                    "get_unprocessed_census",
                    {
                        "project_id": project_id,
                        "count": len(result),
                        "status": "success",
                    },
                )
            return result
        except Exception as e:
            logger.error(f"Error getting unprocessed census: {str(e)}")
            if audit:
                audit.add(
                    "get_unprocessed_census_error",
                    {"project_id": project_id, "error": str(e)},
                )
            raise

    def mark_document_as_processed(
        self, project_id: str, document_index: int, audit: Any = None
    ) -> dict[str, Any]:
        """Set is_processed=True for a document at the given index."""
        try:
            try:
                obj_id = ObjectId(project_id)
            except Exception:
                obj_id = project_id

            project = self.collection.find_one({"_id": obj_id})
            if not project:
                raise ValueError(f"Project not found: {project_id}")

            documents = project.get("documents") or []
            if document_index < 0 or document_index >= len(documents):
                raise ValueError(
                    f"Document index {document_index} out of range (0-{len(documents) - 1})"
                )

            key = f"documents.{document_index}.is_processed"
            result = self.collection.update_one(
                {"_id": obj_id}, {"$set": {key: True}}
            )

            if result.modified_count == 0:
                logger.warning(
                    f"Document {document_index} in project {project_id} was not modified"
                )
            else:
                logger.info(
                    f"Marked document {document_index} as processed for project {project_id}"
                )
                if audit:
                    audit.add(
                        "mark_document_processed",
                        {
                            "project_id": project_id,
                            "document_index": document_index,
                            "status": "success",
                        },
                    )

            updated = self.collection.find_one({"_id": obj_id})
            return _serialize_mongo_doc(updated)
        except Exception as e:
            logger.error(f"Error marking document processed: {str(e)}")
            if audit:
                audit.add(
                    "mark_document_processed_error",
                    {"project_id": project_id, "error": str(e)},
                )
            raise

    def get_project_list(
        self, skip: int = 0, limit: int = 100, audit: Any = None
    ) -> list[dict[str, Any]]:
        """Retrieve a list of all projects with pagination, including total jobs for each project."""
        try:
            projects = list(
                self.collection.find({"status": {"$ne": "0"}})
                .sort("start_date", -1)
                .skip(skip)
                .limit(limit)
            )
            jobs_collection = self.db["Jobs"]

            for project in projects:
                project_id = project.get("_id")
                total_jobs = 0
                if jobs_collection is not None and project_id:
                    total_jobs = jobs_collection.count_documents(
                        {"project_id": str(project_id)}
                    )
                project["total_jobs"] = total_jobs

            logger.info(
                f"Retrieved {len(projects)} projects (skip={skip}, limit={limit})"
            )
            if audit:
                audit.add(
                    "get_project_list",
                    {
                        "count": len(projects),
                        "skip": skip,
                        "limit": limit,
                        "status": "success",
                    },
                )

            return [_serialize_mongo_doc(project) for project in projects]
        except Exception as e:
            logger.error(f"Error retrieving project list: {str(e)}")
            if audit:
                audit.add("get_project_list_error", {"error": str(e)})
            raise

    def create_project(
        self, project_data: dict[str, Any], audit: Any = None
    ) -> dict[str, Any]:
        """Create a new project in MongoDB

        Args:
            project_data: Project document containing fields like:
                - projet_id (required): Project ID
                - project_name (required): Project name
                - other fields as needed
            audit (optional): Audit trail object for logging

        Returns:
            Created project document with _id (serialized as string)
        """
        try:
            if not project_data.get("projet_id"):
                raise ValueError("projet_id is required")
            if not project_data.get("project_name"):
                raise ValueError("project_name is required")

            result = self.collection.insert_one(project_data)
            created_project = self.collection.find_one({"_id": result.inserted_id})

            logger.info(
                f"Created new project: {result.inserted_id} - {project_data.get('project_name')}"
            )
            if audit:
                audit.add(
                    "create_project",
                    {
                        "project_id": str(result.inserted_id),
                        "projet_id": project_data.get("projet_id"),
                        "project_name": project_data.get("project_name"),
                        "status": "success",
                    },
                )
            return _serialize_mongo_doc(created_project)
        except Exception as e:
            logger.error(f"Error creating project: {str(e)}")
            if audit:
                audit.add(
                    "create_project_error",
                    {"projet_id": project_data.get("projet_id"), "error": str(e)},
                )
            raise

    def update_project(
        self, project_id: str, project_data: dict[str, Any], audit: Any = None
    ) -> dict[str, Any]:
        """Update an existing project

        Args:
            project_id: Project ID (string)
            project_data: Updated project fields
            audit (optional): Audit trail object for logging

        Returns:
            Updated project document
        """
        try:
            # Convert project_id to ObjectId if possible
            try:
                obj_id = ObjectId(project_id)
            except Exception:
                obj_id = project_id

            # Verify project exists
            existing = self.collection.find_one({"_id": obj_id})
            if not existing:
                raise ValueError(f"Project not found: {project_id}")

            # Update the project
            result = self.collection.update_one({"_id": obj_id}, {"$set": project_data})

            if result.modified_count == 0:
                logger.warning(f"Project {project_id} was not modified (no changes)")
                if audit:
                    audit.add("update_project_no_change", {"project_id": project_id})
            else:
                logger.info(f"Updated project: {project_id}")
                if audit:
                    audit.add(
                        "update_project",
                        {
                            "project_id": project_id,
                            "fields_updated": list(project_data.keys()),
                            "status": "success",
                        },
                    )

            # Return updated document
            updated_project = self.collection.find_one({"_id": obj_id})
            return _serialize_mongo_doc(updated_project)
        except Exception as e:
            logger.error(f"Error updating project {project_id}: {str(e)}")
            if audit:
                audit.add(
                    "update_project_error", {"project_id": project_id, "error": str(e)}
                )
            raise

    def delete_project(self, project_id: str, audit: Any = None) -> dict[str, Any]:
        """Delete a project from MongoDB

        Args:
            project_id: Project ID (string)
            audit (optional): Audit trail object for logging

        Returns:
            Confirmation with deleted project count
        """
        try:
            # Convert project_id to ObjectId if possible
            try:
                obj_id = ObjectId(project_id)
            except Exception:
                obj_id = project_id

            # Get project before deletion for logging
            project = self.collection.find_one({"_id": obj_id})
            if not project:
                raise ValueError(f"Project not found: {project_id}")

            result = self.collection.delete_one({"_id": obj_id})

            logger.info(f"Deleted project: {project_id}")
            if audit:
                audit.add(
                    "delete_project",
                    {
                        "project_id": project_id,
                        "projet_id": project.get("projet_id"),
                        "project_name": project.get("project_name"),
                        "status": "success",
                    },
                )

            return {
                "deleted_count": result.deleted_count,
                "project_id": project_id,
                "message": f"Project {project_id} deleted successfully",
            }
        except Exception as e:
            logger.error(f"Error deleting project {project_id}: {str(e)}")
            if audit:
                audit.add(
                    "delete_project_error", {"project_id": project_id, "error": str(e)}
                )
            raise

    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("ProjectService MongoDB connection closed")
