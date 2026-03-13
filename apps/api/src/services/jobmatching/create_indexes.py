"""
Create MongoDB Search Indexes
Creates vector search and full-text search indexes for both collections
"""

from pymongo import MongoClient
from pymongo.operations import SearchIndexModel
import time
import logging
import config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class IndexCreator:
    def __init__(self, mongodb_uri: str):
        """Initialize with MongoDB connection"""
        self.mongodb_uri = mongodb_uri
        self.client = None
        self.db = None

    def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(self.mongodb_uri)
            self.db = self.client[config.DATABASE_NAME]
            logger.info(f"Connected to MongoDB database: {config.DATABASE_NAME}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def wait_for_index(self, collection, index_name: str):
        """Wait for index to become queryable"""
        logger.info(f"Waiting for index '{index_name}' to be ready...")
        while True:
            indices = list(collection.list_search_indexes(index_name))
            if len(indices) and indices[0].get("queryable") is True:
                logger.info(f"Index '{index_name}' is ready!")
                break
            time.sleep(5)

    def create_vector_index(
        self,
        collection_name: str,
        index_name: str,
        embedding_field: str,
        num_dimensions: int,
    ):
        """Create vector search index"""
        try:
            collection = self.db[collection_name]

            # Check if index already exists
            existing_indices = list(collection.list_search_indexes())
            if any(idx.get("name") == index_name for idx in existing_indices):
                logger.info(
                    f"Vector index '{index_name}' already exists on {collection_name}"
                )
                return

            # Define vector search index
            search_index_model = SearchIndexModel(
                definition={
                    "fields": [
                        {
                            "type": "vector",
                            "path": embedding_field,
                            "numDimensions": num_dimensions,
                            "similarity": "cosine",  # Using cosine similarity
                        }
                    ]
                },
                name=index_name,
                type="vectorSearch",
            )

            # Create the index
            result = collection.create_search_index(model=search_index_model)
            logger.info(
                f"Vector search index '{result}' is being created on {collection_name}..."
            )

            # Wait for index to be ready
            self.wait_for_index(collection, index_name)

        except Exception as e:
            logger.error(f"Failed to create vector index on {collection_name}: {e}")
            raise

    def create_fulltext_index(self, collection_name: str, index_name: str):
        """Create full-text search index"""
        try:
            collection = self.db[collection_name]

            # Check if index already exists
            existing_indices = list(collection.list_search_indexes())
            if any(idx.get("name") == index_name for idx in existing_indices):
                logger.info(
                    f"Full-text index '{index_name}' already exists on {collection_name}"
                )
                return

            # Define full-text search index with dynamic mapping
            search_index_model = SearchIndexModel(
                definition={
                    "mappings": {
                        "dynamic": False,
                    },
                },
                name=index_name,
            )

            # Create the index
            result = collection.create_search_index(model=search_index_model)
            logger.info(
                f"Full-text search index '{result}' is being created on {collection_name}..."
            )

            # Wait for index to be ready
            self.wait_for_index(collection, index_name)

        except Exception as e:
            logger.error(f"Failed to create full-text index on {collection_name}: {e}")
            raise

    def create_all_indexes(self):
        """Create all required indexes for both collections"""
        try:
            logger.info("=" * 60)
            logger.info("Creating indexes for Job Specialties collection...")
            logger.info("=" * 60)

            # Specialties Vector Index
            self.create_vector_index(
                collection_name=config.SPEC_COLLECTION,
                index_name=config.SPEC_VECTOR_INDEX,
                embedding_field="embedding",
                num_dimensions=config.EMBEDDING_DIMENSION,
            )

            # Specialties Full-text Index
            self.create_fulltext_index(
                collection_name=config.SPEC_COLLECTION,
                index_name=config.SPEC_FULLTEXT_INDEX,
            )

            logger.info("=" * 60)
            logger.info("Creating indexes for Job Aliases collection...")
            logger.info("=" * 60)

            # Aliases Vector Index
            self.create_vector_index(
                collection_name=config.ALIAS_COLLECTION,
                index_name=config.ALIAS_VECTOR_INDEX,
                embedding_field="embedding",
                num_dimensions=config.EMBEDDING_DIMENSION,
            )

            # Aliases Full-text Index
            self.create_fulltext_index(
                collection_name=config.ALIAS_COLLECTION,
                index_name=config.ALIAS_FULLTEXT_INDEX,
            )

            logger.info("=" * 60)
            logger.info("All indexes created successfully!")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            raise
        finally:
            if self.client:
                self.client.close()
                logger.info("MongoDB connection closed")


if __name__ == "__main__":
    # Create all indexes
    creator = IndexCreator(mongodb_uri=config.MONGODB_URI)
    creator.connect()
    creator.create_all_indexes()
