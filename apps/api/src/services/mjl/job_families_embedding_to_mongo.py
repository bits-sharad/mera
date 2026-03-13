from __future__ import annotations


import asyncio
import logging

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s"
)

file_handler = logging.FileHandler("migration.log", mode="a", encoding="utf-8")
file_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
logging.getLogger().addHandler(file_handler)


def embed_and_save_subfamily_descriptions():
    db = get_db()
    families = list(db.families.find({}, {"_id": 1, "familyCode": 1, "familyTitle": 1, "familyDescription": 1}))
    logger.info(f"Found {len(families)} families to embed.")

    updates = []
    for fam in families:
        subfamilies = list(db.subfamilies.find({"familyCode": fam["familyCode"]}, {"_id": 1, "familyCode": 1}))
        for subfam in subfamilies:
            desc = fam.get("familyTitle", "") + fam.get("familyDescription", "")
            if not desc:
                continue
            embedding = embed_text(desc)
            # Flatten if needed
            flat_embedding = [
                float(x)
                for sublist in embedding
                for x in (sublist if isinstance(sublist, list) else [sublist])
            ]
            updates.append(
                UpdateOne(
                    {"_id": subfam["_id"]},
                    {"$set": {"vectors.subFamilyDescription": flat_embedding}},
                )
            )
    if updates:
        result = db.subfamilies.bulk_write(updates, ordered=False)
        logger.info(f"Updated {result.modified_count} subfamilies with embeddings.")
    else:
        logger.info("No subfamily descriptions to embed.")


async def async_embed_texts(texts, max_concurrent=100):
    semaphore = asyncio.Semaphore(max_concurrent)

    async def embed_with_semaphore(t):
        async with semaphore:
            if asyncio.iscoroutinefunction(embed_text):
                return await embed_text(t)
            else:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, embed_text, t)

    return await asyncio.gather(*[embed_with_semaphore(t) for t in texts])


import argparse
import math
from typing import Any, Dict, List, Tuple
import pandas as pd
from pymongo import UpdateOne
import os
import sys
from pathlib import Path


# --- Ensure environment variables are loaded before importing settings ---
def load_environment():
    """Load the appropriate .env file based on APP_ENV variable. Searches api directory for .env files."""
    # Find the api directory (two levels up from this script)
    api_dir = Path(__file__).parent.parent.parent
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

from pymongo import MongoClient
from src.utils.text_utils import (
    norm_text,
    to_str_or_empty,
    create_embedding as embed_text,
)
from src.core.config import settings

# Dummy/fallback implementations for settings, get_db, norm_text, to_str_or_empty, embed_text
logger = logging.getLogger(__name__)


def get_db():
    mongodb_uri = getattr(settings, "mongodb_uri", None)
    mongodb_database = getattr(settings, "mongodb_database", None)
    if not mongodb_uri or not mongodb_database:
        logger.error(
            f"MongoDB URI or database name missing. URI: {mongodb_uri}, DB: {mongodb_database}"
        )
        raise RuntimeError(
            "MongoDB URI or database name missing in settings. Check your .env file and Settings class."
        )
    try:
        client = MongoClient(mongodb_uri)
        db = client[mongodb_database]
        logger.info(f"JobService connected to MongoDB: {db.name}")
        return db
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


# -----------------------------
# Column header mappings (exact from screenshots)
# -----------------------------

FAM_SUBFAM_COLS = {
    "YEAR OVER YEAR STATUS": "yearOverYearStatus",
    "Family Code": "familyCode",
    "Family Title": "familyTitle",
    "Family Description": "familyDescription",
    "Sub-family Code": "subFamilyCode",
    "Sub-family Title": "subFamilyTitle",
    "Sub-family Description": "subFamilyDescription",
}


def bulk_upsert(
    col, docs: List[Dict[str, Any]], key_fields: List[str], batch_size: int = 10
) -> int:
    logger.info(f"bulk_upsert: received {len(docs)} docs for {col.name}")
    if len(docs) == 0:
        logger.error(f"bulk_upsert: No documents to upsert for {col.name}. Aborting.")
        raise ValueError(
            f"bulk_upsert: No documents to upsert for {col.name}. Aborting."
        )
    ops = []
    written = 0
    for d in docs:
        filt = {k: d.get(k) for k in key_fields if d.get(k) not in (None, "")}
        if not filt:
            filt = {"_id": d["_id"]}
        ops.append(UpdateOne(filt, {"$set": d}, upsert=True))
        if len(ops) >= batch_size:
            res = col.bulk_write(ops, ordered=False)
            written += res.upserted_count + res.modified_count
            logger.info(
                f"bulk_upsert: {res.upserted_count} upserted, {res.modified_count} modified in {col.name}"
            )
            ops = []
    if ops:
        res = col.bulk_write(ops, ordered=False)
        written += res.upserted_count + res.modified_count
        logger.info(
            f"bulk_upsert: {res.upserted_count} upserted, {res.modified_count} modified in {col.name}"
        )
    logger.info(f"bulk_upsert: total {written} written to {col.name}")
    return written


def main():
    config = {
        "xlsx": os.getenv("MERCER_XLSX", "data/2026-Mercer-Job-Library-Catalog.xlsx"),
        "job_catalog_sheet": os.getenv("MERCER_JOB_CATALOG_SHEET", "Job Catalog"),
        "career_sheet": os.getenv("MERCER_CAREER_SHEET", "Career Streams & Levels"),
        "spec_sheet": os.getenv("MERCER_SPEC_SHEET", "Specialization vs. Career Level"),
        "family_sheet": os.getenv("MERCER_FAMILY_SHEET", "Family & Sub-Family Summary"),
    }

    db = get_db()

    # Clear all relevant collections before insert

    embed_and_save_subfamily_descriptions()
    print("Migration completed successfully.")


if __name__ == "__main__":
    main()
