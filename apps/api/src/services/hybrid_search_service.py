# Service wrapper for Hybrid Search functionality
from __future__ import annotations

import logging
from typing import Any, Tuple, List
from pymongo import MongoClient
from src.core.config import settings


logger = logging.getLogger(__name__)


class HybridSearchService:
    """Service for hybrid search combining vector and full-text search"""

    def __init__(self, mongodb_uri: str = None, mongodb_database: str = None):
        """Initialize hybrid search service with MongoDB connection"""
        self.mongodb_uri = mongodb_uri or settings.mongodb_uri
        self.mongodb_database = mongodb_database or settings.mongodb_database
        self.client = MongoClient(self.mongodb_uri)
        self.db = self.client[self.mongodb_database]
        logger.info(f"HybridSearchService connected to MongoDB: {self.db.name}")

        # Import here to avoid circular imports and to use the service's db
        from src.services.jobmatching.hybrid_search import HybridSearch

        self.search_engine = HybridSearch(self.mongodb_uri)
        self.search_engine.connect()

    def search_mjl(
        self, query: str
    ) -> Tuple[List[dict[str, Any]], List[dict[str, Any]]]:
        """
        Search for MJL (managed job levels) based on job description

        Args:
            query: Job title and/or job description text

        Returns:
            Tuple of (specialty_results, alias_results)
        """
        try:
            logger.info(f"Searching MJL for query: '{query}'")
            specialty_results, alias_results = self.search_engine.combined_search(query)

            logger.info(
                f"Found {len(specialty_results)} specialty matches and {len(alias_results)} alias matches"
            )
            return specialty_results, alias_results

        except Exception as e:
            logger.error(f"MJL search failed: {e}")
            raise

    def close(self):
        """Close MongoDB connection"""
        if self.search_engine:
            self.search_engine.close()
        if self.client:
            self.client.close()
            logger.info("HybridSearchService MongoDB connection closed")
