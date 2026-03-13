from typing import Any
from pymongo import MongoClient
from bson import ObjectId
from src.core.config import settings
import logging
from src.utility.helper import _serialize_mongo_doc

logger = logging.getLogger(__name__)


class MatchResultService:
    def __init__(self, mongodb_uri: str = None, mongodb_database: str = None):
        self.mongodb_uri = mongodb_uri or settings.mongodb_uri
        self.mongodb_database = mongodb_database or settings.mongodb_database
        self.client = MongoClient(self.mongodb_uri)
        self.db = self.client[self.mongodb_database]
        self.collection = self.db["matchResults"]
        logger.info(f"MatchResultService connected to MongoDB: {self.db.name}")

    def bulk_insert_match_results(
        self, results_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Bulk insert multiple match result documents."""
        try:
            if not results_data:
                raise ValueError("results_data cannot be empty")
            result = self.collection.insert_many(results_data)
            inserted = list(self.collection.find({"_id": {"$in": result.inserted_ids}}))
            logger.info(f"Bulk inserted {len(result.inserted_ids)} match results")
            return {
                "inserted_ids": [str(_id) for _id in result.inserted_ids],
                "count": len(result.inserted_ids),
                "inserted": [_serialize_mongo_doc(doc) for doc in inserted],
                "message": f"Successfully inserted {len(result.inserted_ids)} match results",
            }
        except Exception as e:
            logger.error(f"Error bulk inserting match results: {str(e)}")
            raise

    def insert_match_result(self, result_data: dict[str, Any]) -> dict[str, Any]:
        """Insert a new match result document."""
        try:
            result = self.collection.insert_one(result_data)
            inserted = self.collection.find_one({"_id": result.inserted_id})
            logger.info(f"Inserted match result: {result.inserted_id}")
            return _serialize_mongo_doc(inserted)
        except Exception as e:
            logger.error(f"Error inserting match result: {str(e)}")
            raise

    def update_match_result(
        self, matchresult_id: str, update_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an existing match result document by _id."""
        try:
            try:
                obj_id = ObjectId(matchresult_id)
            except Exception:
                obj_id = matchresult_id
            result = self.collection.update_one({"_id": obj_id}, {"$set": update_data})
            if result.matched_count == 0:
                raise ValueError(f"Match result not found: {matchresult_id}")
            updated = self.collection.find_one({"_id": obj_id})
            logger.info(f"Updated match result: {matchresult_id}")
            return _serialize_mongo_doc(updated)
        except Exception as e:
            logger.error(f"Error updating match result {matchresult_id}: {str(e)}")
            raise

    def delete_match_result(self, matchresult_id: str) -> dict[str, Any]:
        """Delete a match result document by _id."""
        try:
            try:
                obj_id = ObjectId(matchresult_id)
            except Exception:
                obj_id = matchresult_id
            doc = self.collection.find_one({"_id": obj_id})
            if not doc:
                raise ValueError(f"Match result not found: {matchresult_id}")
            result = self.collection.delete_one({"_id": obj_id})
            logger.info(f"Deleted match result: {matchresult_id}")
            return {
                "deleted_count": result.deleted_count,
                "matchresult_id": matchresult_id,
                "message": f"Match result {matchresult_id} deleted successfully",
            }
        except Exception as e:
            logger.error(f"Error deleting match result {matchresult_id}: {str(e)}")
            raise

    def close(self):
        if self.client:
            self.client.close()
            logger.info("MatchResultService MongoDB connection closed")
