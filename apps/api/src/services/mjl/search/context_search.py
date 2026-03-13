from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from rapidfuzz import fuzz
import logging
from src.core.audit import AuditTrail
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from src.utils.text_utils import (
    norm_text,
    to_str_or_empty,
    create_embedding as embed_text,
)
from src.core.config import settings
import numpy as np
import asyncio
from src.services.mjl.match_result import MatchResultService
from bson import ObjectId


# Configure logging to file
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("context_search.log")
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
file_handler.setFormatter(formatter)
if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    logger.addHandler(file_handler)


async def get_db():
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
        client = AsyncIOMotorClient(mongodb_uri)
        db = client[mongodb_database]
        logger.info(f"JobService connected to MongoDB: {db.name}")
        return db
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


@dataclass
class SearchInput:
    project_id: str
    job_id: str
    job_title: str
    job_description: str
    industry: Optional[List[str]] = None  # Now a list of str
    company: Optional[str] = None
    typical_titles: Optional[str] = None
    job_family: Optional[str] = None


async def _build_input_text(inp: SearchInput) -> str:
    parts = [
        #f"Job Title: {inp.job_title}",
        f"Job Family: {inp.job_family}" if inp.job_family else "",
        f"Job Description: {inp.job_description}",
    ]
    if inp.typical_titles:
        parts.append(f"Typical Titles: {inp.typical_titles}")
    return "\n".join(parts)


async def _apply_subfamily_boost(
    candidate: dict, best_subfamilies_matches: list[dict]
) -> dict:
    """Boost a single candidate if its subFamilyCode matches best_subfamilies_matches, with boost decaying by rank/order."""
    if not best_subfamilies_matches:
        return candidate
    sub_code = candidate.get("subFamilyCode")
    for rank, m in enumerate(best_subfamilies_matches):
        if sub_code == m.get("subFamilyCode"):
            # Higher boost for better rank (first = 1.0, second = 0.5, third = 0.25, etc.)
            rank_factor = 1.0 / (rank + 1)
            boost = 0.10 * m["score"] * rank_factor  # Tunable factor
            candidate.setdefault("signals", {})["subFamilyBoost"] = boost
            candidate["score"] += boost
            break
    return candidate


async def _fuzzy_title_boost(
    input_title: str, candidate_title: str, candidate_typical_titles: str
) -> float:
    it = norm_text(input_title)
    ct = norm_text(candidate_title)
    tt = norm_text(candidate_typical_titles)
    score = max(
        fuzz.token_set_ratio(it, ct),
        fuzz.token_set_ratio(it, tt),
    )
    # map 0..100 => 0..0.15 boost
    return (score / 100.0) * 0.15


async def _industry_boost(inp_industry: Optional[List[str]], cand_industry: str) -> float:
    if not inp_industry or (isinstance(inp_industry, list) and not inp_industry):
        return 0.0
    b = norm_text(cand_industry)
    if not b:
        return 0.0
    for a_raw in inp_industry:
        a = norm_text(a_raw)
        if not a:
            continue
        if a == b:
            return 0.08
        if a in b or b in a:
            return 0.04
    return -0.02


async def _apply_feedback_boost(
    company: Optional[str], input_vec: List[float], candidates: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Boost candidates if similar labeled examples exist."""

    db = await get_db()
    # Find top 5 similar training examples for this company
    # Requires Atlas Vector Search index on trainingExamples.vectors.inputText
    try:
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "trainingExamplesVector",
                    "path": "vectors.inputText",
                    "queryVector": input_vec,
                    "numCandidates": 100,
                    "limit": 5,
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "correctJobCode": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]
        cursor = db.trainingExamples.aggregate(pipeline)
        ex = await cursor.to_list(length=3)
    except Exception:
        return candidates  # no vector available or index missing

    boosts = {}
    for e in ex:
        code = e.get("correctJobCode")
        if not code:
            continue
        boosts[code] = max(boosts.get(code, 0.0), float(e.get("score", 0.0)))

    # Convert similarity into a small positive boost
    for c in candidates:
        code = c.get("jobCode")
        if code in boosts:
            c["signals"]["feedbackBoost"] = 0.12 * boosts[code]
            c["score"] += c["signals"]["feedbackBoost"]
    return candidates


def cosine_similarity(a, b):
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)
    if a.shape != b.shape or a.size == 0:
        return -1.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


async def find_best_subfamily(flat_qvec, k: int = 1):
    """Find the subFamilyCode of the subfamily whose embedding is most similar to flat_qvec using Atlas vector search."""
    try:
        db = await get_db()
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "subfamilyVectorIndex",
                    "path": "vectors.subFamilyDescription",
                    "queryVector": flat_qvec,
                    "numCandidates": 100,
                    "limit": k,
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "familyCode": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]
        cursor = db.subfamilies.aggregate(pipeline)
        result = await cursor.to_list()
        if result:
            best_matches = [
                {
                     "score": float(r.get("score", 0.0)),
                    "familyCode": r.get("familyCode"),
                }
                for r in result
            ]
            return best_matches
        else:
            return []
    except Exception as e:
        logger.error(f"Atlas vector search failed in find_best_subfamily: {e}")
        return []


async def retrieve_and_rank(inp: SearchInput, k: int = 20) -> Dict[str, Any]:
    """Async context-aware retrieval over jobCatalog with graph expansion."""
    input_text = await _build_input_text(inp)
    logger.info(f"Input Job Title: {inp.job_title}")
    logger.info(f"Input Job Description: {inp.job_description}")
    logger.info(f"Input industry: {inp.industry}")
    qvec = embed_text(input_text)
    # Flatten qvec if nested
    flat_qvec = [
        float(x)
        for sublist in qvec
        for x in (sublist if isinstance(sublist, list) else [sublist])
    ]

    # Find best matching subfamily by vector similarity
    best_subfamilies_matches = await find_best_subfamily(flat_qvec)

    candidates: List[Dict[str, Any]] = []
    try:
        db = await get_db()
        vs_filter = {}


#        if inp.industry:
#            if isinstance(inp.industry, list):
#                vs_filter["industry"] = {"$in": inp.industry}
#            else:
#                vs_filter["industry"] = inp.industry
        if best_subfamilies_matches:
            # Filter on both familyCode and subFamilyCode together
            vs_filter["$or"] = [
                {"familyCode": m["familyCode"]}
                for m in best_subfamilies_matches
                if isinstance(m.get("familyCode"), (str, int, float))
                and m.get("familyCode")
            ]
            for m in best_subfamilies_matches:
                logger.info(f"familycode:{m['familyCode']} subfamilycode:{m['subFamilyCode']} ")

        pipeline = [
            {
                "$vectorSearch": {
                    "index": "jobCatalogVector",
                    "path": "vectors.jobText",
                    "queryVector": flat_qvec,
                    "numCandidates": 200,
                    "limit": k,
                    **({"filter": vs_filter} if vs_filter else {}),
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "jobCode": 1,
                    "jobTitle": 1,
                    "typicalTitles": 1,
                    "industry": 1,
                    "familyCode": 1,
                    "familyTitle": 1,
                    "subFamilyCode": 1,
                    "subFamilyTitle": 1,
                    "specializationCode": 1,
                    "specializationTitle": 1,
                    "careerStreamTitle": 1,
                    "careerLevelTitle": 1,
                    "executiveType": 1,
                    "specialtyFlags": 1,
                    "join": 1,
                    "vectorScore": {"$meta": "vectorSearchScore"},
                }
            },
        ]
        cursor = db.jobCatalog.aggregate(pipeline)
        raw = await cursor.to_list()

        for r in raw:
            r["score"] = float(r.get("vectorScore", 0.0))
            r["signals"] = {"vectorJobText": r["score"]}
            candidates.append(r)
    except Exception as e:
        logger.error(f"Vector search failed in retrieve_and_rank: {e}")
        # fallback: text search over jobTitle + typicalTitles
        query = {"$text": {"$search": inp.job_title}}
        proj = {"score": {"$meta": "textScore"}, "_id": 0}
        raw = list(
            db.jobCatalog.find(query, proj)
            .sort([("score", {"$meta": "textScore"})])
            .limit(k)
        )
        for r in raw:
            r["score"] = float(r.get("score", 0.0)) / 10.0
            r["signals"] = {"textScore": r["score"]}
            candidates.append(r)

            # 2) Heuristic boosts
    for c in candidates:
        c["signals"]["fuzzyTitleBoost"] = await _fuzzy_title_boost(
            inp.job_title, c.get("jobTitle", ""), c.get("typicalTitles", "")
        )
        c["signals"]["industryBoost"] = await _industry_boost(
            inp.industry if isinstance(inp.industry, list) else [inp.industry] if inp.industry else [], c.get("industry", "")
        )
        c["score"] += c["signals"]["fuzzyTitleBoost"] + c["signals"]["industryBoost"]
        # Normalize score to 1-100 percent (inclusive)
        # Clamp to [1, 100]
        c["score_percent"] = max(1, min(100, round(c["score"] * 100)))

    # 3) Feedback learning boost (optional)
    candidates = await _apply_feedback_boost(inp.company, qvec, candidates)

    # 3b) Subfamily similarity boost (per candidate, order-sensitive)
    candidates = [
        await _apply_subfamily_boost(c, best_subfamilies_matches) for c in candidates
    ]

    # 4) Sort
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # 5) Graph expansion (family/subfamily/specialization descriptions)
    top = candidates[: min(3, len(candidates))]
    expanded = []
    match_result = []
    i = 0
    for c in top:
        expanded.append(
            {
                "candidate": c,
                # "family": fam,
                # "subfamily": sub,
                # "specialization": spec,
            }
        )
        m = {
            "project_id": inp.project_id,
            "job_id": inp.job_id,
            "companyJobId": inp.job_id,
            "bestMatch": {
                "jobCode": c.get("jobCode"),
                "confidence": float(c.get("score_percent", 0.0)),
            },
            "jobTitle": inp.job_title,
            "mjlTitle": c.get("jobTitle"),
            "mjlCode": c.get("jobCode"),
            "explaination": "explain 1",
            "is_best": i == 0,
            "createdAt": datetime.now(),
        }
        i += 1
        match_result.append(m)

    best = candidates[0] if candidates else None
    MatchResultService().bulk_insert_match_results(match_result)
    # Only jobCode, jobTitle, score_percent for topCandidates
    best_candidates_minimal = {
        "jobCode": best.get("jobCode"),
        "jobTitle": best.get("jobTitle"),
        "score_percent": best.get("score_percent"),
    }

    top_candidates_minimal = [
        {
            "jobCode": c.get("jobCode"),
            "jobTitle": c.get("jobTitle"),
            "score_percent": c.get("score_percent"),
        }
        for c in top
    ]
    return {
        "input": inp.__dict__,
        "best": best_candidates_minimal,
        "topCandidates": top_candidates_minimal,
        "expandedTop": expanded,
        "bestSubFamily": best_subfamilies_matches,
    }


def vector_index_exists(db, collection_name, index_name):
    """Check if a vector index exists on the given collection."""
    try:
        indexes = db[collection_name].list_indexes()
        for idx in indexes:
            if idx.get("name") == index_name:
                print(
                    f"[INFO] Vector index '{index_name}' exists on '{collection_name}'."
                )
                return True
        print(
            f"[WARNING] Vector index '{index_name}' does NOT exist on '{collection_name}'."
        )
        return False
    except Exception as e:
        print(f"[ERROR] Could not check indexes: {e}")
        return False


if __name__ == "__main__":
    # No top-level await allowed; if you want to test async functions, use an event loop like below:
    # import asyncio
    # asyncio.run(your_async_function())
    pass
