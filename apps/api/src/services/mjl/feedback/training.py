from __future__ import annotations
from pymongo import MongoClient
import argparse
import math
from typing import Any, Dict, List, Tuple
import pandas as pd
from pymongo import UpdateOne
import os
import sys
from pathlib import Path


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


def get_mjl_job_title(mjl_code: str) -> str:
    """
    Fetch MJL job title from job_catalog collection by mjl_code.
    """
    client = MongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_database]
    doc = db.jobCatalog.find_one({"jobCode": mjl_code})
    if doc:
        return doc.get("jobTitle", "")
    return ""


import pandas as pd
from typing import List, Dict, Any, Optional
from src.services.mmc_jobs import JobService
from src.services.mjl.feedback.learn import record_feedback
import logging

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s"
)

file_handler = logging.FileHandler("migration.log", mode="a", encoding="utf-8")
file_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
logging.getLogger().addHandler(file_handler)
logger = logging.getLogger(__name__)


def import_training_excel(
    excel_path: str,
    project_id: str,
    sheet_name: str = "",
    job_title_col: str = "Job Title",
    job_desc_col: str = "Full Job Description",
    mjl_code_col: str = "MJL Match 2024",
    notes_col: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Import training data from Excel, insert jobs, then feedback.
    Excel columns: company_job_title, company_job_description, mjl_code, mjl_job_title, [notes]
    """
    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=1)
    jobs_data = []
    feedback_data = []
    # Delete previous jobs for the project
    job_service = JobService()
    # Delete related matchResults and feedback for deleted job IDs
    client = job_service.client
    db = client[job_service.mongodb_database]
    # Find all job IDs that were deleted
    deleted_job_ids = [
        doc["_id"] for doc in db.Jobs.find({"project_id": project_id}, {"_id": 1})
    ]
    match_del = db.matchResults.delete_many({"companyJobId": {"$in": deleted_job_ids}})
    feedback_del = db.feedback.delete_many({"company_job_id": {"$in": deleted_job_ids}})
    deleted = job_service.collection.delete_many({"project_id": project_id})
    logger.info(
        f"Deleted {deleted.deleted_count} previous jobs for project {project_id}"
    )
    logger.info(
        f"Deleted {match_del.deleted_count} matchResults and {feedback_del.deleted_count} feedback for project {project_id}"
    )
    total_rows = len(df)
    for idx, row in enumerate(df.iterrows()):
        i, row = row
        job_title = str(row.get(job_title_col, "")).strip()
        job_desc = str(row.get(job_desc_col, "")).strip()
        mjl_code = str(row.get(mjl_code_col, "")).strip()
        notes = str(row.get(notes_col, "")).strip() if notes_col else ""
        logger.info(
            f"Processing row {idx + 1}/{total_rows}: job_title='{job_title}', mjl_code='{mjl_code}'"
        )
        if not job_title or not job_desc or not mjl_code:
            logger.warning(
                f"Skipping row {idx + 1} with missing required fields: {row}"
            )
            continue
        try:
            mjl_job_title = get_mjl_job_title(mjl_code)
            jobs_data.append(
                {
                    "project_id": project_id,
                    "job_title": job_title,
                    "job_description": job_desc,
                    "mjl_code": mjl_code,
                    "mjl_title": mjl_job_title,
                }
            )
            feedback_data.append(
                {
                    "job_title": job_title,
                    "mjl_code": mjl_code,
                    "notes": notes,
                }
            )
        except Exception as e:
            logger.error(f"Error processing row {idx + 1}: {e}")
            continue
    # Insert jobs
    job_service = JobService()
    result = job_service.bulk_insert(jobs_data, project_id=project_id)
    inserted_ids = result.get("inserted_ids", [])
    # Insert matchResults and feedback
    client = job_service.client
    db = client[job_service.mongodb_database]
    feedback_results = []
    for idx, fid in enumerate(inserted_ids):
        fb = feedback_data[idx]
        # Insert into matchResults
        try:
            match_doc = {
                "companyJobId": fid,
                "mjlCode": fb["mjl_code"],
                "jobTitle": jobs_data[idx]["job_title"],
                "mjlTitle": jobs_data[idx]["mjl_title"],
                "createdAt": pd.Timestamp.now(),
                "bestMatch": {
                    "jobCode": fb["mjl_code"],
                    "confidence": 1.0,
                },
            }
            db.matchResults.insert_one(match_doc)
        except Exception as e:
            logger.error(f"MatchResult insert failed for job {fid}: {e}")
        # Insert feedback
        try:
            feedback_result = record_feedback(
                company_job_id=fid, correct_job_code=fb["mjl_code"], notes=fb["notes"]
            )
            feedback_results.append(feedback_result)
        except Exception as e:
            logger.error(f"Feedback insert failed for job {fid}: {e}")
            feedback_results.append({"ok": False, "error": str(e), "job_id": fid})
    return {
        "jobs_inserted": len(inserted_ids),
        "feedback_inserted": len(feedback_results),
        "feedback_results": feedback_results,
    }


from pymongo import MongoClient
from src.utils.text_utils import (
    norm_text,
    to_str_or_empty,
    create_embedding as embed_text,
)
from src.core.config import settings


def main():
    return
    print(
        import_training_excel(
            excel_path="data/Job Matching Train Data - 800 Examples.xlsx",
            project_id="695e95d59d133e35691c7a4a",
            sheet_name="Matching Test Data",
            job_title_col="Job Title",
            job_desc_col="Full Job Description",
            mjl_code_col="MJL Match 2024",
        )
    )


if __name__ == "__main__":
    main()
