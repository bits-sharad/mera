"""
Hybrid Search Module
Implements hybrid search combining vector search and full-text search
using MongoDB's $rankFusion
"""

from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Tuple
import logging
from src.core.config import settings
import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HybridSearch:
    def __init__(self, mongodb_uri: str):
        """Initialize hybrid search with MongoDB connection"""
        self.mongodb_uri = mongodb_uri
        self.client = None
        self.db = None
        self.embedding_model = None

    def connect(self):
        """Connect to MongoDB and load embedding model"""
        try:
            self.client = MongoClient(self.mongodb_uri)
            self.db = self.client[settings.mongodb_database]
            logger.info(f"Connected to MongoDB database: {settings.mongodb_database}")

            # logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
            # self.embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
            # logger.info("Embedding model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to connect or load model: {e}")
            raise

    # def create_query_embedding(self, query: str) -> List[float]:
    #     """Create embedding for search query"""
    #     embedding = self.embedding_model.encode(query, normalize_embeddings=True)
    #     return embedding.tolist()
    def create_query_embedding(self, text: str) -> List[float]:  # (texts):
        """
        Simple function to call MMC embeddings API
        """

        url = "https://stg1.mmc-bedford-int-non-prod-ingress.mgti.mmc.com/coreapi/llm/embeddings/v1/mmc-tech-text-embedding-3-large"

        headers = {
            "x-api-key": "3d0e6c31-7016-4038-883b-e7f97ef4439b-12e88bc6-e92f-4d26-98c9-74f164fe51e7",
            "Content-Type": "application/json",
        }

        data = {
            "input": text,
            "user": "user-123",
            "input_type": "query",
            "encoding_format": "float",
            "model": "text-embedding-3-large",
        }

        response = requests.post(url, headers=headers, json=data)
        result = response.json() if response.status_code == 200 else response.text
        embeddings_data = sorted(result["data"], key=lambda x: x["index"])
        embeddings = [item["embedding"] for item in embeddings_data]
        return embeddings[0]

    def _combine_results(
        self,
        vector_results: List[Dict],
        fulltext_results: List[Dict],
        vector_weight: float,
        fulltext_weight: float,
        vector_score_key: str,
        fulltext_score_key: str,
    ) -> List[Dict[str, Any]]:
        """
        Combine vector and fulltext search results using weighted scoring
        Uses Reciprocal Rank Fusion (RRF) algorithm
        """
        # K constant for RRF (typically 60)
        k = 60

        # Create dictionaries to track scores and documents
        doc_scores = {}
        doc_data = {}

        # Process vector results
        for rank, doc in enumerate(vector_results, 1):
            doc_id = str(doc["_id"])
            rrf_score = vector_weight / (k + rank)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score

            if doc_id not in doc_data:
                doc_data[doc_id] = doc.copy()
                doc_data[doc_id]["vector_score"] = doc.get(vector_score_key, 0)
                doc_data[doc_id]["fulltext_score"] = 0
                doc_data[doc_id]["combined_score"] = 0

        # Process fulltext results
        for rank, doc in enumerate(fulltext_results, 1):
            doc_id = str(doc["_id"])
            rrf_score = fulltext_weight / (k + rank)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score

            if doc_id not in doc_data:
                doc_data[doc_id] = doc.copy()
                doc_data[doc_id]["vector_score"] = 0
                doc_data[doc_id]["fulltext_score"] = doc.get(fulltext_score_key, 0)
                doc_data[doc_id]["combined_score"] = 0
            else:
                doc_data[doc_id]["fulltext_score"] = doc.get(fulltext_score_key, 0)

        # Update combined scores
        for doc_id, score in doc_scores.items():
            doc_data[doc_id]["combined_score"] = score

        # Sort by combined score and return
        sorted_results = sorted(
            doc_data.values(), key=lambda x: x["combined_score"], reverse=True
        )

        return sorted_results

    def search_specialties(
        self, query: str, vector_weight: float = 0.5, fulltext_weight: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search on specialties collection
        Combines vector search on embeddings and full-text search on spec_title and combined_text
        """
        try:
            collection = self.db[settings.spec_collection]

            # Create query embedding
            query_embedding = self.create_query_embedding(query)

            # Vector search pipeline
            vector_pipeline = [
                {
                    "$vectorSearch": {
                        "index": settings.spec_vector_index,
                        "path": "embedding",
                        "queryVector": query_embedding,
                        "numCandidates": int(settings.total_candidates_spec),
                        "limit": int(settings.top_k_per_search),
                    }
                },
                {"$addFields": {"vector_score": {"$meta": "vectorSearchScore"}}},
                {
                    "$project": {
                        "_id": 1,
                        "spec_code": 1,
                        "spec_title": 1,
                        "spec_description": 1,
                        "family_code": 1,
                        "family_title": 1,
                        "sub_family_code": 1,
                        "sub_family_title": 1,
                        "combined_text": 1,
                        "vector_score": 1,
                    }
                },
            ]

            # Full-text search pipeline
            fulltext_pipeline = [
                {
                    "$search": {
                        "index": settings.spec_fulltext_index,
                        "text": {
                            "query": query,
                            "path": ["spec_title", "combined_text", "spec_description"],
                            "fuzzy": {"maxEdits": 1},
                        },
                    }
                },
                {"$addFields": {"fulltext_score": {"$meta": "searchScore"}}},
                {"$limit": int(settings.top_k_per_search)},
                {
                    "$project": {
                        "_id": 1,
                        "spec_code": 1,
                        "spec_title": 1,
                        "spec_description": 1,
                        "family_code": 1,
                        "family_title": 1,
                        "sub_family_code": 1,
                        "sub_family_title": 1,
                        "combined_text": 1,
                        "fulltext_score": 1,
                    }
                },
            ]

            # Execute both searches
            vector_results = list(collection.aggregate(vector_pipeline))
            fulltext_results = list(collection.aggregate(fulltext_pipeline))

            # Combine results using Reciprocal Rank Fusion (RRF)
            results = self._combine_results(
                vector_results,
                fulltext_results,
                vector_weight,
                fulltext_weight,
                "vector_score",
                "fulltext_score",
            )

            logger.info(f"Found {len(results)} results from specialties search")

            # Add source information
            for result in results:
                result["source"] = "specialty"
                result["query"] = query

            return results[: int(settings.top_k_per_search)]

        except Exception as e:
            logger.error(f"Specialties search failed: {e}")
            raise

    def search_aliases(
        self, query: str, vector_weight: float = 0.5, fulltext_weight: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search on aliases collection
        Combines vector search on embeddings and full-text search on alias_title
        """
        try:
            collection = self.db[settings.alias_collection]

            # Create query embedding
            query_embedding = self.create_query_embedding(query)

            # Vector search pipeline
            vector_pipeline = [
                {
                    "$vectorSearch": {
                        "index": settings.alias_vector_index,
                        "path": "embedding",
                        "queryVector": query_embedding,
                        "numCandidates": int(settings.total_candidates_alias),
                        "limit": int(settings.top_k_per_search),
                    }
                },
                {"$addFields": {"vector_score": {"$meta": "vectorSearchScore"}}},
                {
                    "$project": {
                        "_id": 1,
                        "alias_title": 1,
                        "spec_code": 1,
                        "spec_title": 1,
                        "family_code": 1,
                        "family_title": 1,
                        "sub_family_code": 1,
                        "sub_family_title": 1,
                        "vector_score": 1,
                    }
                },
            ]

            # Full-text search pipeline
            fulltext_pipeline = [
                {
                    "$search": {
                        "index": settings.alias_fulltext_index,
                        "text": {
                            "query": query,
                            "path": ["alias_title", "spec_title"],
                            "fuzzy": {"maxEdits": 1},
                        },
                    }
                },
                {"$addFields": {"fulltext_score": {"$meta": "searchScore"}}},
                {"$limit": int(settings.top_k_per_search)},
                {
                    "$project": {
                        "_id": 1,
                        "alias_title": 1,
                        "spec_code": 1,
                        "spec_title": 1,
                        "family_code": 1,
                        "family_title": 1,
                        "sub_family_code": 1,
                        "sub_family_title": 1,
                        "fulltext_score": 1,
                    }
                },
            ]

            # Execute both searches
            vector_results = list(collection.aggregate(vector_pipeline))
            fulltext_results = list(collection.aggregate(fulltext_pipeline))

            # Combine results using Reciprocal Rank Fusion (RRF)
            results = self._combine_results(
                vector_results,
                fulltext_results,
                vector_weight,
                fulltext_weight,
                "vector_score",
                "fulltext_score",
            )

            logger.info(f"Found {len(results)} results from aliases search")

            # Add source information
            for result in results:
                result["source"] = "alias"
                result["query"] = query

            return results[: int(settings.top_k_per_search)]

        except Exception as e:
            logger.error(f"Aliases search failed: {e}")
            raise

    def combined_search(
        self, query: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Perform both specialty and alias searches
        Returns tuple of (specialty_results, alias_results)
        """
        logger.info(f"Performing hybrid search for query: '{query}'")

        # Search specialties
        specialty_results = self.search_specialties(
            query=query,
            vector_weight=float(settings.vector_weight),
            fulltext_weight=float(settings.fulltext_weight),
        )

        # Search aliases
        alias_results = self.search_aliases(
            query=query,
            vector_weight=float(settings.vector_weight),
            fulltext_weight=float(settings.fulltext_weight),
        )

        return specialty_results, alias_results

    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


if __name__ == "__main__":
    # Test the hybrid search
    search = HybridSearch(mongodb_uri=settings.mongodb_uri)
    search.connect()

    # Example query
    test_query = """At least five years of demonstrated postsecondary content expertise, with a minimum of three years in the nonprofit, public, or philanthropic sector required. Key responsibilities Manage postsecondary grantmaking, initiatives, and projects; develop grantmaking guidelines and oversee executed grants. Engage with stakeholders and community partners to support systemic responsiveness and improve postsecondary outcomes for underserved populations. The role involves strategic grantmaking, policy analysis, and collaboration with various stakeholders, requiring a deep understanding of postsecondary education systems and the ability to influence policy and practice. It also necessitates managing multiple projects and partnerships simultaneously to achieve desired outcomes. Bachelor’s degree required; Master’s level degree in a related field preferred. At least five years of relevant experience in program design, implementation, and grantmaking is required."""

    try:
        spec_results, alias_results = search.combined_search(test_query)

        print("\n" + "=" * 80)
        print(f"SEARCH RESULTS FOR: '{test_query}'")
        print("=" * 80)

        print(f"\n--- SPECIALTY RESULTS ({len(spec_results)}) ---")
        for i, result in enumerate(spec_results[:5], 1):
            print(f"\n{i}. {result.get('spec_title', 'N/A')}")
            print(f"   Code: {result.get('spec_code', 'N/A')}")
            print(f"   Vector Score: {result.get('vector_score', 0):.4f}")
            print(f"   Fulltext Score: {result.get('fulltext_score', 0):.4f}")
            print(f"   Combined Score: {result.get('combined_score', 0):.4f}")

        print(f"\n--- ALIAS RESULTS ({len(alias_results)}) ---")
        for i, result in enumerate(alias_results[:5], 1):
            print(f"\n{i}. {result.get('alias_title', 'N/A')}")
            print(f"   Spec: {result.get('spec_title', 'N/A')}")
            print(f"   Code: {result.get('spec_code', 'N/A')}")
            print(f"   Vector Score: {result.get('vector_score', 0):.4f}")
            print(f"   Fulltext Score: {result.get('fulltext_score', 0):.4f}")
            print(f"   Combined Score: {result.get('combined_score', 0):.4f}")

    finally:
        search.close()
