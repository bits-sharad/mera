from pymongo import MongoClient


import pandas as pd
from pymongo import UpdateOne
import os
import sys
from pathlib import Path
import logging


def load_environment():
    """Load the appropriate .env file based on APP_ENV variable. Searches api directory for .env files."""
    # Find the api directory (two levels up from this script)
    api_dir = Path(__file__).parent.parent.parent.parent
    app_env = os.getenv("APP_ENV", "dev").lower().strip()
    env_mapping = {
        "local": "development",
        "dev": "development",
        "development": "development",
        "stage": "stage",
        "staging": "stage",
        "prod": "production",
        "production": "production",
    }
    full_env_name = env_mapping.get(app_env, "development")
    env_file = api_dir / f".env.{full_env_name}"
    if env_file.exists():
        print(f"[INFO] Loading environment config from {env_file}")
        from dotenv import load_dotenv

        load_dotenv(env_file, override=True)
        print(f"[INFO] Successfully loaded {env_file}")
    else:
        default_env_file = api_dir / ".env"
        if default_env_file.exists():
            print(f"[WARNING] {env_file} not found. Falling back to {default_env_file}")
            print(f"[INFO] Loading default environment config from {default_env_file}")
            from dotenv import load_dotenv

            load_dotenv(default_env_file, override=True)
            print(f"[INFO] Successfully loaded {default_env_file}")
        else:
            print(
                f"[ERROR] No .env file found. Looked for: {env_file} or {default_env_file}"
            )


# Always load environment before importing settings
os.environ.setdefault("APP_ENV", "local")
if os.getenv("APP_ENV", "local").lower().strip() in [
    "local",
    "dev",
    "development",
    "stage",
    "staging",
    "prod",
    "production",
]:
    load_environment()


from src.core.config import settings

# Replace DIMS with the actual number of dimensions for your vectors
VECTOR_DIMS = 3072  # Example: 384, update as needed

client = MongoClient(settings.mongodb_uri)
db = client[settings.mongodb_database]

# This uses the Atlas vector index creation command (not a standard PyMongo index)
# For Atlas, you must use the Atlas UI or the Atlas Admin API for vector indexes.
# Here is a template for the Atlas Admin API payload:

vector_index = {
    "name": "jobCatalogVector",
    "collectionName": "jobCatalog",
    "database": settings.mongodb_database,
    "type": "vectorSearch",
    "fields": [
        {
            "type": "vector",
            "path": "vectors.jobText",
            "numDimensions": VECTOR_DIMS,
            "similarity": "cosine",
        },
        {
            "type": "vector",
            "path": "vectors.jobTypicalTitles",
            "numDimensions": VECTOR_DIMS,
            "similarity": "cosine",
        },
        {"type": "filter", "path": "industry"},
        {"type": "filter", "path": "careerStreamTitle"},
        {"type": "filter", "path": "careerLevelTitle"},
        {"type": "filter", "path": "familyCode"},
        {"type": "filter", "path": "subFamilyCode"},
        {"type": "filter", "path": "specializationCode"},
    ],
}


import json

# --- Specializations Vector Index ---
specializations_vector_index = {
    "name": "specializationsVectorIndex",
    "collectionName": "specializations",
    "database": settings.mongodb_database,
    "type": "vectorSearch",
    "fields": [
        {
            "type": "vector",
            "path": "vectors.specializationText",
            "numDimensions": VECTOR_DIMS,
            "similarity": "cosine",
        },
        {"type": "filter", "path": "familyCode"},
        {"type": "filter", "path": "subFamilyCode"},
        {"type": "filter", "path": "specializationCode"},
    ],
}


# --- Training Examples Vector Index ---
training_examples_vector_index = {
    "name": "trainingExamplesVectorIndex",
    "collectionName": "trainingExamples",
    "database": settings.mongodb_database,
    "type": "vectorSearch",
    "fields": [
        {
            "type": "vector",
            "path": "vectors.inputText",
            "numDimensions": VECTOR_DIMS,
            "similarity": "cosine",
        },
        {"type": "filter", "path": "company"},
    ],
}


# For a standard text index (for fallback text search):
db.jobCatalog.create_index([("jobTitle", "text"), ("typicalTitles", "text")])
print("Created text index on jobTitle and typicalTitles.")


logger = logging.getLogger(__name__)


def ensure_indexes(db):
    def safe_create_index(collection, *args, **kwargs):
        try:
            collection.create_index(*args, **kwargs)
        except Exception as e:
            if "IndexOptionsConflict" in str(e) or "already exists" in str(e):
                logger.warning(f"Index creation skipped: {e}")
            else:
                logger.error(f"Index creation error: {e}")
                raise

    # Text index for jobCatalog (for $text search fallback)
    safe_create_index(db.jobCatalog, [("jobTitle", "text"), ("typicalTitles", "text")])
    logger.info(
        "Ensured text index on jobCatalog.jobTitle and jobCatalog.typicalTitles."
    )

    # Text index for specializations (if needed for text search)
    # Uncomment if you want text search on specializationTitle or other fields
    # safe_create_index(db.specializations, [("specializationTitle", "text")])

    # Standard filter indexes for specializations (for query performance)
    safe_create_index(
        db.specializations,
        [("familyCode", 1), ("subFamilyCode", 1), ("specializationCode", 1)],
    )
    logger.info(
        "Ensured filter indexes on specializations.familyCode, subFamilyCode, specializationCode."
    )

    # Standard filter index for trainingExamples (for company filter)
    safe_create_index(db.trainingExamples, [("company", 1)])
    logger.info("Ensured filter index on trainingExamples.company.")

    # Standard filter indexes for jobCatalog (for query performance on filter fields)
    safe_create_index(
        db.jobCatalog,
        [
            ("industry", 1),
            ("careerStreamTitle", 1),
            ("careerLevelTitle", 1),
            ("familyCode", 1),
            ("subFamilyCode", 1),
            ("specializationCode", 1),
        ],
    )
    logger.info(
        "Ensured filter indexes on jobCatalog filter fields: industry, careerStreamTitle, careerLevelTitle, familyCode, subFamilyCode, specializationCode."
    )

    # Add other standard MongoDB indexes here as needed
    # Note: Atlas vector indexes must be created via Atlas UI or Admin API, not PyMongo


ensure_indexes(db)
