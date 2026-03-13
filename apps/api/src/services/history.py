from __future__ import annotations

import logging
from typing import Any
from datetime import datetime
from pymongo import MongoClient

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
        # No ObjectId conversion, treat all as string
        if isinstance(value, dict):
            serialized[key] = _serialize_mongo_doc(value)
        elif isinstance(value, list):
            serialized[key] = [
                _serialize_mongo_doc(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            serialized[key] = value

    return serialized


class SessionHistoryService:
    """Knowledge Base & History Service.

    Store and retrieve conversation history from MongoDB history collection.
    """

    def __init__(
        self, core_api=None, mongodb_uri: str = None, mongodb_database: str = None
    ) -> None:
        """Initialize session history service with MongoDB connection

        Args:
            core_api: Legacy parameter, kept for backward compatibility (not used)
            mongodb_uri: MongoDB connection URI (defaults to settings.mongodb_uri)
            mongodb_database: MongoDB database name (defaults to settings.mongodb_database)
        """
        self.mongodb_uri = mongodb_uri or settings.mongodb_uri
        self.mongodb_database = mongodb_database or settings.mongodb_database
        self.client = MongoClient(self.mongodb_uri)
        self.db = self.client[self.mongodb_database]
        self.collection = self.db["history"]
        logger.info(
            f"SessionHistoryService connected to MongoDB: {self.db.name}.history"
        )

    async def get(self, session_id: str) -> dict[str, Any]:
        """Get session history by session_id

        Args:
            session_id: Session identifier

        Returns:
            Dict with session history including messages list
        """
        try:
            history = self.collection.find_one({"session_id": session_id})

            if not history:
                logger.info(
                    f"No history found for session: {session_id}, returning empty"
                )
                return {
                    "session_id": session_id,
                    "messages": [],
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }

            logger.info(
                f"Retrieved history for session: {session_id} with {len(history.get('messages', []))} messages"
            )
            return _serialize_mongo_doc(history)

        except Exception as e:
            logger.error(f"Error retrieving session history {session_id}: {str(e)}")
            return {
                "session_id": session_id,
                "messages": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

    async def append(self, session_id: str, role: str, content: str) -> None:
        """Append a message to session history

        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system)
            content: Message content
        """
        try:
            message = {"role": role, "content": content, "timestamp": datetime.utcnow()}

            # Try to update existing session, or create new one
            result = self.collection.update_one(
                {"session_id": session_id},
                {
                    "$push": {"messages": message},
                    "$set": {"updated_at": datetime.utcnow()},
                    "$setOnInsert": {
                        "session_id": session_id,
                        "created_at": datetime.utcnow(),
                    },
                },
                upsert=True,
            )

            if result.upserted_id:
                logger.info(f"Created new session history: {session_id}")
            else:
                logger.info(f"Appended message to session: {session_id} (role: {role})")

        except Exception as e:
            logger.error(f"Error appending to session history {session_id}: {str(e)}")
            raise

    def get_all_sessions(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get all session summaries

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session summaries with basic info
        """
        try:
            sessions = list(
                self.collection.find(
                    {},
                    {
                        "session_id": 1,
                        "created_at": 1,
                        "updated_at": 1,
                        "messages": {"$slice": 1},
                    },
                )
                .sort("updated_at", -1)
                .limit(limit)
            )

            return [_serialize_mongo_doc(session) for session in sessions]

        except Exception as e:
            logger.error(f"Error retrieving all sessions: {str(e)}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """Delete a session history

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False otherwise
        """
        try:
            result = self.collection.delete_one({"session_id": session_id})

            if result.deleted_count > 0:
                logger.info(f"Deleted session history: {session_id}")
                return True
            else:
                logger.warning(f"Session history not found: {session_id}")
                return False

        except Exception as e:
            logger.error(f"Error deleting session history {session_id}: {str(e)}")
            return False

    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("SessionHistoryService MongoDB connection closed")

    def create_indexes(self):
        """Create indexes for optimized queries on history collection"""
        try:
            # Index on session_id for fast lookups
            self.collection.create_index("session_id", unique=True)
            logger.info("Created unique index on session_id")

            # Index on updated_at for sorting recent sessions
            self.collection.create_index([("updated_at", -1)])
            logger.info("Created index on updated_at (descending)")

            # Compound index for session queries with time range
            self.collection.create_index([("session_id", 1), ("created_at", -1)])
            logger.info("Created compound index on session_id and created_at")

            logger.info("All indexes created successfully for history collection")

        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")
            raise
