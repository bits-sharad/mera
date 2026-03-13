import argparse
import json
import logging
import os
import sys
from typing import Dict, List, Any
import pandas as pd
from pymongo import MongoClient, UpdateOne
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv
from pathlib import Path


from src.core.config import settings

logger = logging.getLogger(__name__)


COLUMN_MAP = {
    # Family
    "family code": "family_code",
    "family title": "family_title",
    "family description": "family_description",
    # Sub-family
    "sub family code": "sub_family_code",
    "sub family title": "sub_family_title",
    "sub family description": "sub_family_description",
}


REQUIRED_FIELDS = [
    "family_code",
    "family_title",
    "family_description",
    "sub_family_code",
    "sub_family_title",
    "sub_family_description",
]


# -------- Helpers --------


def _infer_engine(path: str) -> str:
    ext = os.path.splitext(path.lower())[1]
    if ext == ".xlsx":
        return "openpyxl"
    elif ext == ".xls":
        return "xlrd"
    else:
        return None


def read_excel(path: str, sheet: str | int | None = None) -> pd.DataFrame:
    engine = _infer_engine(path)
    if engine is None:
        raise ValueError(f"Unsupported file type for '{path}'. Expected .xlsx or .xls")

    df = pd.read_excel(path, sheet_name=sheet, engine=engine)
    if isinstance(df, dict):
        if df:
            df = next(iter(df.values()))
        else:
            raise ValueError(f"No sheets found in Excel file: {path}")

    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"Expected DataFrame but got {type(df).__name__}")

    normalized = {}

    for col in df.columns:
        key = str(col).strip().lower()
        key = key.replace("-", " ").replace("_", " ")
        key = " ".join(key.split())  # collapse multiple spaces
        normalized[col] = COLUMN_MAP.get(key, None)

    df = df.rename(columns={k: v for k, v in normalized.items() if v is not None})

    missing = [c for c in REQUIRED_FIELDS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing expected columns in Excel: {missing}\n"
            f"Found columns: {list(df.columns)}"
        )

    # Trim strings and coerce to str for codes
    for col in REQUIRED_FIELDS:
        df[col] = df[col].astype(str).str.strip()

    # Drop completely empty rows on these required fields
    df = df.dropna(subset=["family_code", "sub_family_code"])
    return df


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


class JobFamilyService:
    """Service for managing Job Family taxonomy in MongoDB"""

    def __init__(
        self,
        mongodb_uri: str = None,
        mongodb_database: str = None,
        collection_name: str = None,
    ):
        """Initialize job family service with MongoDB connection"""
        self.mongodb_uri = mongodb_uri or settings.mongodb_uri
        self.mongodb_database = mongodb_database or settings.mongodb_database
        self.collection_name = collection_name or settings.job_families_collection
        self.client = MongoClient(self.mongodb_uri)
        self.db = self.client[self.mongodb_database]
        self.collection = self.db[self.collection_name]
        logger.info(
            f"JobFamilyService connected to MongoDB: {self.db.name}.{self.collection_name}"
        )

    def ensure_indexes(self):
        """Create indexes to prevent duplicates and speed up lookups."""
        try:
            self.collection.create_index(
                [("family_code", 1), ("sub_family_code", 1)],
                unique=True,
                name="uniq_family_subfamily",
            )
            self.collection.create_index([("family_code", 1)], name="idx_family_code")
            self.collection.create_index(
                [("sub_family_code", 1)], name="idx_sub_family_code"
            )
            logger.info("Indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            raise

    def find_by_family_code(self, code: str) -> List[Dict]:
        """Find documents by Family Code"""
        try:
            cursor = self.collection.find({"family_code": code}).sort(
                [("sub_family_code", 1)]
            )
            results = [_serialize_mongo_doc(doc) for doc in cursor]
            logger.info(f"Found {len(results)} documents for family_code: {code}")
            return results
        except Exception as e:
            logger.error(f"Error finding family code {code}: {e}")
            raise

    def find_by_sub_family_code(self, sub_code: str) -> List[Dict]:
        """Find documents by Sub-family Code"""
        try:
            cursor = self.collection.find({"sub_family_code": sub_code}).sort(
                [("family_code", 1)]
            )
            results = [_serialize_mongo_doc(doc) for doc in cursor]
            logger.info(
                f"Found {len(results)} documents for sub_family_code: {sub_code}"
            )
            return results
        except Exception as e:
            logger.error(f"Error finding sub-family code {sub_code}: {e}")
            raise

    def bulk_upsert(self, operations: List[UpdateOne]) -> Dict[str, int]:
        """Execute bulk upsert operations"""
        try:
            if not operations:
                return {"matched": 0, "modified": 0, "upserted": 0, "count": 0}

            result = self.collection.bulk_write(operations, ordered=False)
            summary = {
                "matched": result.matched_count,
                "modified": result.modified_count,
                "upserted": len(result.upserted_ids),
                "count": self.collection.count_documents({}),
            }
            logger.info(f"Bulk upsert completed: {summary}")
            return summary
        except Exception as e:
            logger.error(f"Error during bulk upsert: {e}")
            raise

    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("JobFamilyService MongoDB connection closed")


def df_to_operations(df: pd.DataFrame) -> List[UpdateOne]:
    """
    Convert DataFrame rows to bulk upsert operations.
    """
    ops: List[UpdateOne] = []
    for _, row in df.iterrows():
        doc = {
            "family_code": row["family_code"],
            "family_title": row["family_title"],
            "family_description": row["family_description"],
            "sub_family_code": row["sub_family_code"],
            "sub_family_title": row["sub_family_title"],
            "sub_family_description": row["sub_family_description"],
        }
        # Upsert keyed by (family_code, sub_family_code)
        ops.append(
            UpdateOne(
                {
                    "family_code": doc["family_code"],
                    "sub_family_code": doc["sub_family_code"],
                },
                {"$set": doc},
                upsert=True,
            )
        )

    return ops


def load_to_mongo(
    excel_path: str,
    mongo_uri: str = None,
    db_name: str = None,
    coll_name: str = None,
    sheet: str | int | None = None,
) -> Dict[str, int]:
    """
    Read Excel and bulk upsert into MongoDB.
    Returns a summary.
    """

    df = read_excel(excel_path, sheet=sheet)
    df = df.fillna(method="ffill")

    service = JobFamilyService(
        mongodb_uri=mongo_uri, mongodb_database=db_name, collection_name=coll_name
    )
    try:
        # Delete all records from the collection before loading
        deleted = service.collection.delete_many({})
        logger.info(f"Deleted {deleted.deleted_count} records from {coll_name}")

        service.ensure_indexes()
        ops = df_to_operations(df)
        summary = service.bulk_upsert(ops)
        summary["deleted_count"] = deleted.deleted_count
        return summary
    finally:
        service.close()


# -------- CLI --------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Load Job Family/Sub-family data from Excel into MongoDB and query it."
    )
    p.add_argument(
        "--uri",
        default=os.getenv("MONGODB_URI", ""),
        help="MongoDB connection URI (default: env MONGODB_URI )",
    )
    p.add_argument("--db", default="hr", help="Database name (default: hr)")
    p.add_argument(
        "--collection",
        default="job_families",
        help="Collection name (default: job_families)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # load command

    p_load = sub.add_parser("load", help="Load Excel into MongoDB (upsert).")

    p_load.add_argument("excel", help="Path to the Excel file (.xlsx or .xls)")

    p_load.add_argument(
        "--sheet",
        help="Worksheet name or index (optional). If omitted, uses the first sheet.",
    )

    # find-family

    p_ff = sub.add_parser("find-family", help="Find documents by Family Code.")

    p_ff.add_argument("code", help="Family Code to search (e.g., GMA, FIN)")

    # find-subfamily

    p_sf = sub.add_parser("find-subfamily", help="Find documents by Sub-family Code.")

    p_sf.add_argument("code", help="Sub-family Code to search (e.g., 01, 02, 05)")

    return p


def load_environment():
    """Load the appropriate .env file based on APP_ENV variable.

    Priority:
    1. .env.{environment} file (e.g., .env.development, .env.stage, .env.production)
    2. .env file (default)

    Supported environments:
    - development (dev, dev)
    - stage (stage, staging)
    - production (prod, production)
    """

    # .env files are in the api directory (same as main.py)
    api_dir = Path(__file__).parent

    # First try to get APP_ENV from environment or system
    app_env = os.getenv("APP_ENV", "dev").lower().strip()

    # Map short names to full environment names
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

    # Try to load environment-specific .env file
    env_file = api_dir / f".env.{full_env_name}"
    if env_file.exists():
        print(f"[INFO] Loading environment config from {env_file}")
        load_dotenv(env_file, override=True)
        print(f"[INFO] Successfully loaded {env_file}")
    else:
        # Fall back to default .env file
        default_env_file = api_dir / ".env"
        if default_env_file.exists():
            print(f"[WARNING] {env_file} not found. Falling back to {default_env_file}")
            print(f"[INFO] Loading default environment config from {default_env_file}")
            load_dotenv(default_env_file, override=True)
            print(f"[INFO] Successfully loaded {default_env_file}")
        else:
            print(
                f"[ERROR] No .env file found. Looked for: {env_file} or {default_env_file}"
            )


def main(argv=None):
    os.environ.setdefault("APP_ENV", "local")
    if os.getenv("APP_ENV", "local").lower().strip() in ["local"]:
        load_environment()

    summary = load_to_mongo(
        excel_path="data/job_families.xlsx",
        db_name="jobmatchingmodelpocDev",
        coll_name="job_families",
    )

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    print("start exporting job families taxonomy utility...")
    main()
