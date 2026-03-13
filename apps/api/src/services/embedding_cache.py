"""Embedding caching layer to avoid re-computing embeddings for unchanged files."""

import hashlib
import json
import os
from typing import Any

from src.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingCache:
    """Cache embeddings based on file hash to avoid redundant computations."""

    def __init__(self, cache_dir: str = ".embedding_cache"):
        """Initialize cache.

        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def get_file_hash(self, file_path: str) -> str:
        """Compute SHA256 hash of file.

        Args:
            file_path: Path to the file

        Returns:
            Hex hash of file contents
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read in chunks to handle large files efficiently
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def get_cache_key(self, file_path: str, index_name: str, db_name: str) -> str:
        """Generate cache key from file path and metadata.

        Args:
            file_path: Path to source file
            index_name: MongoDB index name
            db_name: MongoDB database name

        Returns:
            Cache key filename
        """
        file_hash = self.get_file_hash(file_path)
        key = f"{index_name}_{db_name}_{file_hash}.json"
        return os.path.join(self.cache_dir, key)

    def has_cached_embeddings(
        self, file_path: str, index_name: str, db_name: str
    ) -> bool:
        """Check if embeddings are cached for this file.

        Args:
            file_path: Path to source file
            index_name: MongoDB index name
            db_name: MongoDB database name

        Returns:
            True if cache exists and is valid
        """
        cache_path = self.get_cache_key(file_path, index_name, db_name)
        return os.path.exists(cache_path)

    def load_cached_embeddings(
        self, file_path: str, index_name: str, db_name: str
    ) -> dict[str, Any] | None:
        """Load embeddings from cache.

        Args:
            file_path: Path to source file
            index_name: MongoDB index name
            db_name: MongoDB database name

        Returns:
            Cached data dict or None if not found
        """
        cache_path = self.get_cache_key(file_path, index_name, db_name)

        try:
            if os.path.exists(cache_path):
                with open(cache_path, "r") as f:
                    data = json.load(f)
                    logger.info(f"Loaded cached embeddings from {cache_path}")
                    return data
        except Exception as e:
            logger.warning(f"Failed to load cache from {cache_path}: {str(e)}")

        return None

    def save_cached_embeddings(
        self,
        file_path: str,
        index_name: str,
        db_name: str,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None:
        """Save embeddings to cache.

        Args:
            file_path: Path to source file
            index_name: MongoDB index name
            db_name: MongoDB database name
            chunks: List of text chunks
            embeddings: List of embedding vectors
        """
        cache_path = self.get_cache_key(file_path, index_name, db_name)

        try:
            cache_data = {
                "file_path": file_path,
                "index_name": index_name,
                "db_name": db_name,
                "chunks": chunks,
                "embeddings": embeddings,
            }

            with open(cache_path, "w") as f:
                json.dump(cache_data, f)

            logger.info(f"Cached embeddings to {cache_path}")
        except Exception as e:
            logger.warning(f"Failed to save embeddings cache: {str(e)}")

    def clear_cache(self, file_path: str | None = None) -> None:
        """Clear cache files.

        Args:
            file_path: Specific file to clear cache for, or None to clear all
        """
        try:
            if file_path:
                # Clear only cache for specific file
                for index_name in [
                    "mercer_ipe_factors"
                ]:  # Add other index names as needed
                    for db_name in ["job_architecture"]:  # Add other db names as needed
                        cache_path = self.get_cache_key(file_path, index_name, db_name)
                        if os.path.exists(cache_path):
                            os.remove(cache_path)
                            logger.info(f"Cleared cache: {cache_path}")
            else:
                # Clear entire cache directory
                import shutil

                if os.path.exists(self.cache_dir):
                    shutil.rmtree(self.cache_dir)
                    os.makedirs(self.cache_dir, exist_ok=True)
                    logger.info(f"Cleared entire cache directory: {self.cache_dir}")
        except Exception as e:
            logger.warning(f"Failed to clear cache: {str(e)}")
