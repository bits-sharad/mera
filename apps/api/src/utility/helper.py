import re
import unicodedata

import pandas as pd
from difflib import SequenceMatcher
from typing import Any, List, Tuple, Union

from bson import ObjectId

# URL pattern (http, https, www)
_URL_PATTERN = re.compile(
    r"https?://[^\s<>\"']+|www\.[^\s<>\"']+",
    re.IGNORECASE,
)
# Markdown/image link patterns: ![alt](url), [text](url)
_IMAGE_LINK_PATTERN = re.compile(
    r"!\[[^\]]*\]\([^)]+\)|\[[^\]]*\]\([^)]+\)",
    re.IGNORECASE,
)
# HTML tags
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
# Control characters and other unwanted Unicode
_CONTROL_AND_SPECIAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200b-\u200f\u2028-\u202f\u2060-\u206f\ufffe\uffff]")


def clean_extracted_text(text: str | None) -> str:
    """Clean extracted text by removing unwanted characters, URLs, image links, etc.

    Removes:
    - URLs (http, https, www)
    - Markdown/image links (![alt](url), [text](url))
    - HTML tags
    - Control characters and special Unicode
    - Excessive newlines, tabs, and whitespace
    """
    if not text or not isinstance(text, str):
        return ""

    # Remove URLs
    text = _URL_PATTERN.sub(" ", text)
    # Remove markdown/image links
    text = _IMAGE_LINK_PATTERN.sub(" ", text)
    # Remove HTML tags
    text = _HTML_TAG_PATTERN.sub(" ", text)
    # Remove control and special Unicode characters
    text = _CONTROL_AND_SPECIAL.sub("", text)
    # Normalize Unicode (e.g. replace fancy quotes with standard)
    text = unicodedata.normalize("NFKC", text)
    # Replace tabs and newlines with single space
    text = re.sub(r"[\t\n\r]+", " ", text)
    # Collapse multiple spaces
    text = re.sub(r" +", " ", text)
    return text.strip()


def fix_headers_in_dataframe(
    df: pd.DataFrame,
    preview_rows: int = 10,
    detect_multirow: bool = True,
    normalize: bool = True,
    inplace: bool = False,
) -> Tuple[pd.DataFrame, Union[int, List[int]]]:
    if not inplace:
        df = df.copy()

    # 1) Build a preview (top N rows)
    preview = df.head(preview_rows)
    if preview.empty:
        # Nothing to detect; return as-is
        return df, 0

    def row_metrics(row):
        vals = ["" if pd.isna(v) else str(v).strip() for v in row]
        total = len(vals) or 1
        non_empty = sum(bool(v) for v in vals)
        non_empty_ratio = non_empty / total
        text_like = sum(any(c.isalpha() for c in v) for v in vals) / total
        unique_ratio = len(set([v for v in vals if v])) / (non_empty or 1)
        numeric_like = sum(v.replace(".", "", 1).isdigit() for v in vals) / total
        avg_len = (sum(len(v) for v in vals) / total) if total else 0
        return {
            "vals": vals,
            "non_empty_ratio": non_empty_ratio,
            "text_like": text_like,
            "unique_ratio": unique_ratio,
            "numeric_like": numeric_like,
            "avg_len": avg_len,
        }

    stats = preview.apply(row_metrics, axis=1).tolist()

    # 2) Score rows as potential headers
    def header_score(s):
        score = (
            0.55 * s["non_empty_ratio"]
            + 0.25 * s["text_like"]
            + 0.15 * s["unique_ratio"]
            - 0.10 * s["numeric_like"]
        )

        # small penalty for very long tokens (often content, not headers)
        if s["avg_len"] > 30:
            score -= 0.05
        return score

    scores = [header_score(s) for s in stats]
    best = int(pd.Series(scores).idxmax())
    # 3) Optional: detect two-level header if the next row is similarly header-like
    header = best
    if detect_multirow and best + 1 < len(stats):
        next_score = scores[best + 1]
        if (
            next_score > 0
            and abs(next_score - scores[best]) < 0.05
            and stats[best]["text_like"] > 0.4
            and stats[best + 1]["text_like"] > 0.4
        ):
            header = [best, best + 1]

    # 4) Apply header(s) and drop them from the data
    if isinstance(header, int):
        # Single-level header
        new_cols = stats[header]["vals"]
        df.columns = new_cols
        df = df.iloc[header + 1 :].reset_index(drop=True)
    else:
        # Two-level header: combine row best and best+1
        top = stats[header[0]]["vals"]
        below = stats[header[1]]["vals"]
        # Flatten by joining non-empty parts
        merged = []
        for a, b in zip(top, below):
            a = a.strip() if a else ""
            b = b.strip() if b else ""
            if a and b:
                merged.append(f"{a} {b}".strip())
            else:
                merged.append((a or b).strip())
        df.columns = merged
        df = df.iloc[header[1] + 1 :].reset_index(drop=True)

    # 5) Normalize final column names
    if normalize:
        df.columns = (
            pd.Series(df.columns)
            .astype(str)
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
        )
    return df


def _detect_column_match(
    column_name: str, keywords: list[str], threshold: float = 0.6
) -> bool:
    """Check if column name matches any keyword (fuzzy match)."""
    col_lower = column_name.lower().strip()
    for keyword in keywords:
        keyword_lower = keyword.lower().strip()
        similarity = SequenceMatcher(None, col_lower, keyword_lower).ratio()
        if (
            similarity >= threshold
            or keyword_lower in col_lower
            or col_lower in keyword_lower
        ):
            return True
    return False


def detect_excel_job_columns(df: pd.DataFrame) -> dict[str, str | None]:
    """Detect job title, job code, and job description columns in a DataFrame."""
    columns = df.columns.tolist()
    result = {
        "job_title_column": None,
        "job_code_column": None,
        "job_description_column": None,
    }
    job_title_keywords = [
        "job title", "position", "title", "job_title",
        "position_title", "job name", "typical titles",
    ]
    job_code_keywords = ["job code", "code", "job_code", "position_code"]
    job_desc_keywords = [
        "job description", "description", "job_desc", "job_description",
        "duties", "responsibilities",
    ]
    for col in columns:
        if _detect_column_match(col, job_title_keywords):
            result["job_title_column"] = col
        if _detect_column_match(col, job_code_keywords):
            result["job_code_column"] = col
        if _detect_column_match(col, job_desc_keywords):
            result["job_description_column"] = col
    return result


def extract_jobs_from_dataframe(
    df: pd.DataFrame,
    project_id: str,
    job_title_column: str | None = None,
    job_code_column: str | None = None,
    job_description_column: str | None = None,
) -> list[dict[str, Any]]:
    """Extract job records from DataFrame for bulk insert."""
    if job_title_column is None or job_description_column is None:
        detected = detect_excel_job_columns(df)
        job_title_column = job_title_column or detected["job_title_column"]
        job_code_column = job_code_column or detected["job_code_column"]
        job_description_column = job_description_column or detected["job_description_column"]

    if not job_title_column or not job_description_column:
        return []

    jobs_data = []
    for idx, row in df.iterrows():
        job = {"project_id": project_id}
        if job_code_column and job_code_column in df.columns and pd.notna(row.get(job_code_column)):
            job["job_code"] = clean_extracted_text(str(row[job_code_column]))
        if job_title_column in df.columns and pd.notna(row.get(job_title_column)):
            job["job_title"] = clean_extracted_text(str(row[job_title_column]))
        if job_description_column in df.columns and pd.notna(row.get(job_description_column)):
            job["job_description"] = clean_extracted_text(str(row[job_description_column]))
        else:
            job["job_description"] = ""
        if job.get("job_title"):
            jobs_data.append(job)
    return jobs_data


def _serialize_mongo_doc(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if doc is None:
        return None
    serialized = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            serialized[key] = str(value)
        elif isinstance(value, dict):
            serialized[key] = _serialize_mongo_doc(value)
        elif isinstance(value, list):
            serialized[key] = [
                _serialize_mongo_doc(item)
                if isinstance(item, dict)
                else (str(item) if isinstance(item, ObjectId) else item)
                for item in value
            ]
        else:
            serialized[key] = value
    return serialized
