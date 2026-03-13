from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
import logging
from bson import ObjectId
from pymongo import MongoClient
from src.utils.text_utils import (
    norm_text,
    to_str_or_empty,
    create_embedding as embed_text,
)
from src.core.config import settings

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


def record_feedback(
    company_job_id: str,
    correct_job_code: str,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    db = get_db()
    mr = db.matchResults.find_one({"companyJobId": ObjectId(company_job_id)})
    cj = db.Jobs.find_one({"_id": ObjectId(company_job_id)})
    if not cj:
        raise ValueError(f"Jobs not found: {company_job_id}")

    doc = {
        "companyJobId": str(company_job_id),
        "correctJobCode": correct_job_code,
        "notes": notes or "",
        "createdAt": datetime.now(),
    }
    db.feedback.insert_one(doc)

    # also store as training example for kNN boosting (per company)
    input_text = "\n".join(
        [
            f"Job Title: {cj.get('jobTitle', '')}",
            f"Job Description: {cj.get('jobDescription', '')}",
            f"Industry: {cj.get('industry', '')}",
            f"Typical Titles: {cj.get('typicalTitles', '')}",
        ]
    )
    vec = embed_text(input_text)
    # Flatten vec if nested and cast to float
    flat_vec = [
        float(x)
        for sublist in vec
        for x in (sublist if isinstance(sublist, list) else [sublist])
    ]
    ex = {
        "company": cj.get("company") or "",
        "companyJobId": company_job_id,
        "correctJobCode": correct_job_code,
        "inputText": input_text,
        "vectors": {"inputText": flat_vec},
        "createdAt": datetime.now(),
    }
    db.trainingExamples.insert_one(ex)

    return {
        "ok": True,
        "feedbackId": str(doc.get("_id", "")),
        "trainingExampleSaved": True,
    }
