from __future__ import annotations
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s"
)

file_handler = logging.FileHandler("migration.log", mode="a", encoding="utf-8")
file_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
logging.getLogger().addHandler(file_handler)


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


async def build_specialization_docs(df: pd.DataFrame) -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    rows = list(df.iterrows())
    batch_size = 200
    total = len(rows)
    logger.info(f"Embedding specializations: batch {total})")

    def flatten(lst):
        for item in lst:
            if isinstance(item, list):
                yield from flatten(item)
            else:
                yield item

    for i in range(0, total, batch_size):
        logger.info(
            f"Embedding specializations: batch {i // batch_size + 1} of {(total + batch_size - 1) // batch_size} ({i + 1}-{min(i + batch_size, total)} of {total})"
        )
        batch = rows[i : i + batch_size]
        meta = []
        spec_texts = []
        typical_titles_texts = []
        for _, r in batch:
            code = to_str_or_empty(r.get("specializationCode"))
            if not code:
                meta.append(None)
                spec_texts.append(None)
                typical_titles_texts.append(None)
                continue
            title = to_str_or_empty(r.get("specializationTitle"))
            industry = to_str_or_empty(r.get("industry"))
            subfamily_title = to_str_or_empty(r.get("subFamilyTitle"))
            nav = to_str_or_empty(r.get("navigationGroupTitle"))
            desc = to_str_or_empty(r.get("specializationDescription"))
            note = to_str_or_empty(r.get("specializationMatchNote"))
            exec_titles = to_str_or_empty(r.get("executiveTypicalTitles"))
            mgmt_titles = to_str_or_empty(r.get("managementTypicalTitles"))
            prof_titles = to_str_or_empty(r.get("professionalTypicalTitles"))
            para_titles = to_str_or_empty(r.get("paraProfessionalSupportTypicalTitles"))
            spec_text_for_embed = "\n".join(
                [
                    f"Specialization Title: {title}",
                    f"Industry: {industry}",
                    f"Sub Family Title: {subfamily_title}",
                    f"Navigation Group Title: {nav}",
                    f"Description: {desc}",
                    f"Match Note: {note}",
                ]
            )
            typical_titles_for_embed = "\n".join(
                [
                    f"Executive Typical Titles: {exec_titles}",
                    f"Management Typical Titles: {mgmt_titles}",
                    f"Professional Typical Titles: {prof_titles}",
                    f"Para-Professional / Support Typical Titles: {para_titles}",
                ]
            )
            meta.append(
                (
                    r,
                    code,
                    title,
                    industry,
                    subfamily_title,
                    nav,
                    desc,
                    note,
                    exec_titles,
                    mgmt_titles,
                    prof_titles,
                    para_titles,
                )
            )
            spec_texts.append(spec_text_for_embed)
            typical_titles_texts.append(typical_titles_for_embed)
        valid_idx = [j for j, m in enumerate(meta) if m is not None]
        if valid_idx:
            spec_embeds = await async_embed_texts([spec_texts[j] for j in valid_idx])
            typical_embeds = await async_embed_texts(
                [typical_titles_texts[j] for j in valid_idx]
            )
        else:
            spec_embeds = []
            typical_embeds = []
        embed_idx = 0
        for j, m in enumerate(meta):
            if m is None:
                continue
            (
                r,
                code,
                title,
                industry,
                subfamily_title,
                nav,
                desc,
                note,
                exec_titles,
                mgmt_titles,
                prof_titles,
                para_titles,
            ) = m
            docs.append(
                {
                    "_id": f"specialization:{code}",
                    "industry": industry,
                    "broadBasedGeneralSpecialization": to_str_or_empty(
                        r.get("broadBasedGeneralSpecialization")
                    ),
                    "digitalSpecialization": to_str_or_empty(
                        r.get("digitalSpecialization")
                    ),
                    "specializationCode": code,
                    "specializationTitle": title,
                    "subFamilyTitle": subfamily_title,
                    "navigationGroupTitle": nav,
                    "specializationDescription": desc,
                    "specializationMatchNote": note,
                    "specialtyFlags": to_str_or_empty(r.get("specialtyFlags")),
                    "executiveTypicalTitles": exec_titles,
                    "managementTypicalTitles": mgmt_titles,
                    "professionalTypicalTitles": prof_titles,
                    "paraProfessionalSupportTypicalTitles": para_titles,
                    "executiveType": to_str_or_empty(r.get("executiveType")),
                    "norm": {
                        "specializationTitle": norm_text(title),
                        "subFamilyTitle": norm_text(subfamily_title),
                        "navigationGroupTitle": norm_text(nav),
                        "industry": norm_text(industry),
                    },
                    "vectors": {
                        "specText": [float(x) for x in flatten(spec_embeds[embed_idx])],
                        "typicalTitles": [
                            float(x) for x in flatten(typical_embeds[embed_idx])
                        ],
                    },
                    "source": {"sheet": DEFAULT_SHEETS["specializationVsCareerLevel"]},
                }
            )
            embed_idx += 1
    return docs


async def build_job_catalog_docs(df: pd.DataFrame, col) -> None:
    def flatten(lst):
        for item in lst:
            if isinstance(item, list):
                yield from flatten(item)
            else:
                yield item

    rows = list(df.iterrows())
    batch_size = 400
    total = len(rows)
    for i in range(0, total, batch_size):
        logger.info(
            f"Embedding job catalog: batch {i // batch_size + 1} of {(total + batch_size - 1) // batch_size} ({i + 1}-{min(i + batch_size, total)} of {total})"
        )
        batch = rows[i : i + batch_size]
        meta = []
        job_texts = []
        typical_titles_texts = []
        for _, r in batch:
            job_code = to_str_or_empty(r.get("jobCode"))
            if not job_code:
                meta.append(None)
                job_texts.append(None)
                typical_titles_texts.append(None)
                continue
            job_title = to_str_or_empty(r.get("jobTitle"))
            typical_titles = to_str_or_empty(r.get("typicalTitles"))
            industry = to_str_or_empty(r.get("industry"))
            family_code = to_str_or_empty(r.get("familyCode"))
            sub_code = to_str_or_empty(r.get("subFamilyCode"))
            spec_code = to_str_or_empty(r.get("specializationCode"))
            family_id = f"family:{family_code}" if family_code else None
            subfamily_id = (
                f"subfamily:{family_code}-{sub_code}"
                if family_code and sub_code
                else None
            )
            spec_id = f"specialization:{spec_code}" if spec_code else None
            job_text_for_embed = "\n".join(
                [
                    f"Job Title: {job_title}",
                    f"Typical Titles: {typical_titles}",
                    f"Specialization Title: {to_str_or_empty(r.get('specializationTitle'))}",
                    f"Sub Family Title: {to_str_or_empty(r.get('subFamilyTitle'))}",
                    f"Family Title: {to_str_or_empty(r.get('familyTitle'))}",
                    f"Career Stream Title: {to_str_or_empty(r.get('careerStreamTitle'))}",
                    f"Career Level Title: {to_str_or_empty(r.get('careerLevelTitle'))}",
                    f"Industry: {industry}",
                ]
            )
            meta.append(
                (
                    r,
                    job_code,
                    job_title,
                    typical_titles,
                    industry,
                    family_code,
                    sub_code,
                    spec_code,
                    family_id,
                    subfamily_id,
                    spec_id,
                )
            )
            job_texts.append(job_text_for_embed)
            typical_titles_texts.append(typical_titles)
        valid_idx = [j for j, m in enumerate(meta) if m is not None]
        if valid_idx:
            job_embeds = await async_embed_texts([job_texts[j] for j in valid_idx])
            typical_embeds = await async_embed_texts(
                [typical_titles_texts[j] for j in valid_idx]
            )
        else:
            job_embeds = []
            typical_embeds = []
        embed_idx = 0
        batch_docs = []
        for j, m in enumerate(meta):
            if m is None:
                continue
            (
                r,
                job_code,
                job_title,
                typical_titles,
                industry,
                family_code,
                sub_code,
                spec_code,
                family_id,
                subfamily_id,
                spec_id,
            ) = m
            batch_docs.append(
                {
                    "_id": f"job:{job_code}",
                    "jobYearOverYearChangeStatus": to_str_or_empty(
                        r.get("jobYearOverYearChangeStatus")
                    ),
                    "industry": industry,
                    "broadBasedGeneralSpecialization": to_str_or_empty(
                        r.get("broadBasedGeneralSpecialization")
                    ),
                    "digitalSpecialization": to_str_or_empty(
                        r.get("digitalSpecialization")
                    ),
                    "jobCode": job_code,
                    "jobTitle": job_title,
                    "typicalTitles": typical_titles,
                    "familyCode": family_code,
                    "familyTitle": to_str_or_empty(r.get("familyTitle")),
                    "subFamilyCode": sub_code,
                    "subFamilyTitle": to_str_or_empty(r.get("subFamilyTitle")),
                    "navigationGroupTitle": to_str_or_empty(
                        r.get("navigationGroupTitle")
                    ),
                    "specializationCode": spec_code,
                    "specializationTitle": to_str_or_empty(
                        r.get("specializationTitle")
                    ),
                    "executiveType": to_str_or_empty(r.get("executiveType")),
                    "careerStreamTitle": to_str_or_empty(r.get("careerStreamTitle")),
                    "careerLevelTitle": to_str_or_empty(r.get("careerLevelTitle")),
                    "specialtyFlags": to_str_or_empty(r.get("specialtyFlags")),
                    "join": {
                        "familyId": family_id,
                        "subFamilyId": subfamily_id,
                        "specializationId": spec_id,
                    },
                    "norm": {
                        "jobTitle": norm_text(job_title),
                        "industry": norm_text(industry),
                        "familyTitle": norm_text(to_str_or_empty(r.get("familyTitle"))),
                        "subFamilyTitle": norm_text(
                            to_str_or_empty(r.get("subFamilyTitle"))
                        ),
                        "specializationTitle": norm_text(
                            to_str_or_empty(r.get("specializationTitle"))
                        ),
                        "careerStreamTitle": norm_text(
                            to_str_or_empty(r.get("careerStreamTitle"))
                        ),
                        "careerLevelTitle": norm_text(
                            to_str_or_empty(r.get("careerLevelTitle"))
                        ),
                    },
                    "vectors": {
                        "jobText": [float(x) for x in flatten(job_embeds[embed_idx])],
                        "jobTypicalTitles": [
                            float(x) for x in flatten(typical_embeds[embed_idx])
                        ],
                    },
                    "source": {"sheet": DEFAULT_SHEETS["jobCatalog"]},
                }
            )
            embed_idx += 1
        if batch_docs:
            logger.info(
                f"jobCatalog batch {i // batch_size + 1}: {len(batch_docs)} docs to upsert"
            )
            logger.debug(
                f"First doc in batch: {batch_docs[0] if batch_docs else 'EMPTY'}"
            )
            try:
                bulk_upsert(col, batch_docs, ["jobCode"])
            except Exception as e:
                logger.error(
                    f"bulk_upsert for jobCatalog failed on batch {i // batch_size + 1}: {e}"
                )
    return None


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
JOB_CATALOG_COLS = {
    "Job Year over Year Change Status": "jobYearOverYearChangeStatus",
    "Industry": "industry",
    "Broad-Based-General Specialization": "broadBasedGeneralSpecialization",
    "Digital Specialization": "digitalSpecialization",
    "Job Code": "jobCode",
    "Job Title": "jobTitle",
    "Typical Titles": "typicalTitles",
    "Family Code": "familyCode",
    "Family Title": "familyTitle",
    "Sub Family Code": "subFamilyCode",
    "Sub Family Title": "subFamilyTitle",
    "Navigation Group Title": "navigationGroupTitle",
    "Specialization Code": "specializationCode",
    "Specialization Title": "specializationTitle",
    "Executive Type": "executiveType",
    "Career Stream Title": "careerStreamTitle",
    "Career Level Title": "careerLevelTitle",
    "Specialty Flags": "specialtyFlags",
}

SPEC_COLS = {
    "Industry": "industry",
    "Broad-Based-General Specialization": "broadBasedGeneralSpecialization",
    "Digital Specialization": "digitalSpecialization",
    "Specialization Code": "specializationCode",
    "Specialization Title": "specializationTitle",
    "Sub Family Title": "subFamilyTitle",
    "Navigation Group Title": "navigationGroupTitle",
    "Specialization Description": "specializationDescription",
    "Specialization Match Note": "specializationMatchNote",
    "Specialty Flags": "specialtyFlags",
    "Executive Typical Titles": "executiveTypicalTitles",
    "Management Typical Titles": "managementTypicalTitles",
    "Professional Typical Titles": "professionalTypicalTitles",
    "Para-Professional / Support Typical Title": "paraProfessionalSupportTypicalTitles",
    "Executive Type": "executiveType",
}

FAM_SUBFAM_COLS = {
    "YEAR OVER YEAR STATUS": "yearOverYearStatus",
    "Family Code": "familyCode",
    "Family Title": "familyTitle",
    "Family Description": "familyDescription",
    "Sub-family Code": "subFamilyCode",
    "Sub-family Title": "subFamilyTitle",
    "Sub-family Description": "subFamilyDescription",
}

CAREER_COLS = {
    "Career Stream Name": "careerStreamName",
    "Career Stream Description": "careerStreamDescription",
    "Career Level Name": "careerLevelName",
    "Career Level Description": "careerLevelDescription",
}

DEFAULT_SHEETS = {
    "jobCatalog": "Job Catalog",
    "careerStreamsLevels": "Career Streams & Levels",
    "specializationVsCareerLevel": "Specialization vs. Career Level",
    "familySubFamilySummary": "Family & Sub-Family Summary",
}


def load_sheet(xlsx_path: str, sheet_name: str) -> pd.DataFrame:
    df = pd.read_excel(xlsx_path, sheet_name=sheet_name, engine="openpyxl", header=7)
    return df.dropna(how="all")


def rename_columns(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    keep = [c for c in mapping.keys() if c in df.columns]
    df2 = df[keep].copy()
    return df2.rename(columns=mapping)


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

    safe_create_index(db.families, [("familyCode", 1)], unique=True)
    safe_create_index(
        db.subfamilies, [("familyCode", 1), ("subFamilyCode", 1)], unique=True
    )
    safe_create_index(db.subfamilies, [("norm.subFamilyTitle", 1)])

    safe_create_index(db.careerStreams, [("careerStreamName", 1)], unique=True)
    safe_create_index(db.careerLevels, [("careerLevelName", 1)], unique=True)
    safe_create_index(db.careerLevels, [("careerStreamName", 1)])

    safe_create_index(db.specializations, [("specializationCode", 1)], unique=True)
    safe_create_index(db.specializations, [("industry", 1)])
    safe_create_index(db.specializations, [("norm.subFamilyTitle", 1)])

    safe_create_index(db.jobCatalog, [("jobCode", 1)], unique=True)
    safe_create_index(db.jobCatalog, [("industry", 1)])
    safe_create_index(db.jobCatalog, [("specializationCode", 1)])
    safe_create_index(db.jobCatalog, [("familyCode", 1), ("subFamilyCode", 1)])
    safe_create_index(
        db.jobCatalog, [("careerStreamTitle", 1), ("careerLevelTitle", 1)]
    )


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


def build_family_docs(
    df: pd.DataFrame,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    families: Dict[str, Dict[str, Any]] = {}
    subfamilies: List[Dict[str, Any]] = []

    for _, r in df.iterrows():
        family_code = to_str_or_empty(r.get("familyCode"))
        if not family_code:
            continue

        if family_code not in families:
            family_title = to_str_or_empty(r.get("familyTitle"))
            families[family_code] = {
                "_id": f"family:{family_code}",
                "yearOverYearStatus": to_str_or_empty(r.get("yearOverYearStatus")),
                "familyCode": family_code,
                "familyTitle": family_title,
                "familyDescription": to_str_or_empty(r.get("familyDescription")),
                "norm": {"familyTitle": norm_text(family_title)},
                "source": {"sheet": DEFAULT_SHEETS["familySubFamilySummary"]},
            }

        sub_code = to_str_or_empty(r.get("subFamilyCode"))
        sub_title = to_str_or_empty(r.get("subFamilyTitle"))
        if sub_code or sub_title:
            subfamilies.append(
                {
                    "_id": f"subfamily:{family_code}-{sub_code or norm_text(sub_title)}",
                    "yearOverYearStatus": to_str_or_empty(r.get("yearOverYearStatus")),
                    "familyCode": family_code,
                    "subFamilyCode": sub_code,
                    "subFamilyTitle": sub_title,
                    "subFamilyDescription": to_str_or_empty(
                        r.get("subFamilyDescription")
                    ),
                    "norm": {"subFamilyTitle": norm_text(sub_title)},
                    "source": {"sheet": DEFAULT_SHEETS["familySubFamilySummary"]},
                }
            )

    return list(families.values()), subfamilies


def build_career_docs(
    df: pd.DataFrame,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    streams: Dict[str, Dict[str, Any]] = {}
    levels: List[Dict[str, Any]] = []

    for _, r in df.iterrows():
        stream_name = to_str_or_empty(r.get("careerStreamName"))
        level_name = to_str_or_empty(r.get("careerLevelName"))

        if stream_name and stream_name not in streams:
            streams[stream_name] = {
                "_id": f"careerStream:{stream_name}",
                "careerStreamName": stream_name,
                "careerStreamDescription": to_str_or_empty(
                    r.get("careerStreamDescription")
                ),
                "norm": {"careerStreamName": norm_text(stream_name)},
                "source": {"sheet": DEFAULT_SHEETS["careerStreamsLevels"]},
            }

        if level_name:
            levels.append(
                {
                    "_id": f"careerLevel:{level_name}",
                    "careerStreamName": stream_name,
                    "careerLevelName": level_name,
                    "careerLevelDescription": to_str_or_empty(
                        r.get("careerLevelDescription")
                    ),
                    "norm": {"careerLevelName": norm_text(level_name)},
                    "source": {"sheet": DEFAULT_SHEETS["careerStreamsLevels"]},
                }
            )

    return list(streams.values()), levels


def main():
    return
    config = {
        "xlsx": os.getenv("MERCER_XLSX", "data/2026-Mercer-Job-Library-Catalog.xlsx"),
        "job_catalog_sheet": os.getenv("MERCER_JOB_CATALOG_SHEET", "Job Catalog"),
        "career_sheet": os.getenv("MERCER_CAREER_SHEET", "Career Streams & Levels"),
        "spec_sheet": os.getenv("MERCER_SPEC_SHEET", "Specialization vs. Career Level"),
        "family_sheet": os.getenv("MERCER_FAMILY_SHEET", "Family & Sub-Family Summary"),
    }

    db = get_db()
    ensure_indexes(db)

    # Clear all relevant collections before insert
    logger.info(
        "Clearing collections: families, subfamilies, careerStreams, careerLevels, specializations, jobCatalog"
    )
    # db.families.delete_many({})
    # db.subfamilies.delete_many({})
    # db.careerStreams.delete_many({})
    # db.careerLevels.delete_many({})
    # db.specializations.delete_many({})
    # db.jobCatalog.delete_many({})

    # Family/Subfamily
    # fam_df = rename_columns(load_sheet(config["xlsx"], config["family_sheet"]), FAM_SUBFAM_COLS)
    # families, subfamilies = build_family_docs(fam_df)
    # bulk_upsert(db.families, families, ["familyCode"])
    # bulk_upsert(db.subfamilies, subfamilies, ["familyCode", "subFamilyCode"])

    # Career streams/levels
    # car_df = rename_columns(load_sheet(config["xlsx"], config["career_sheet"]), CAREER_COLS)
    # streams, levels = build_career_docs(car_df)
    # bulk_upsert(db.careerStreams, streams, ["careerStreamName"])
    # bulk_upsert(db.careerLevels, levels, ["careerLevelName"])

    # Specializations
    # print("Processing specializations...")
    # spec_df = rename_columns(load_sheet(config["xlsx"], config["spec_sheet"]), SPEC_COLS)
    # spec_docs = asyncio.run(build_specialization_docs(spec_df))
    # try:
    #    bulk_upsert(db.specializations, spec_docs, ["specializationCode"])
    # except Exception as e:
    #    logger.error(f"bulk_upsert for specializations failed: {e}")
    #    raise

    # Job catalog
    print("Processing job catalog...")
    job_df = rename_columns(
        load_sheet(config["xlsx"], config["job_catalog_sheet"]), JOB_CATALOG_COLS
    )
    asyncio.run(build_job_catalog_docs(job_df, db.jobCatalog))

    print("Migration completed successfully.")


if __name__ == "__main__":
    main()
