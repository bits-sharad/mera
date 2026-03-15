#!/usr/bin/env python3
"""
Extract text from Word documents via Mercer Document Processing API and export to Excel.

Usage:
    python batch_word_extract_to_excel.py -i "path/to/docs" -o "output.xlsx"

Setup:
    1. Copy .env.example to .env and fill in your Mercer API credentials
    2. pip install -r requirements.txt

Environment (required in .env):
    DOC_PROCESSING_API_KEY
    FETCH_TOKEN_USERNAME + FETCH_TOKEN_PASSWORD (to auto-fetch token)
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import os
import re
import unicodedata
from pathlib import Path

import httpx
import pandas as pd

# Load .env from script directory (pip install python-dotenv)
_script_dir = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv
    load_dotenv(_script_dir / ".env")
except ImportError:
    pass

# Override via .env if your environment uses different URLs
AUTH_URL = os.getenv(
    "AUTH_URL",
    "https://stg1.mmc-bedford-int-non-prod-ingress.mgti.mmc.com/authentication/v1/oauth2/token",
)
DOC_PROCESSING_BASE = os.getenv(
    "DOC_PROCESSING_API_BASE_URL",
    "https://stg1.mmc-dallas-int-non-prod-ingress.mgti.mmc.com/coreapi/document-processing/v1",
)
UPLOAD_URL = f"{DOC_PROCESSING_BASE.rstrip('/')}/documents/upload"
EXTRACT_URL = f"{DOC_PROCESSING_BASE.rstrip('/')}/documents/extract"

WORD_EXTENSIONS = {".doc", ".docx"}
MIME_TYPES = {
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def clean_extracted_text(text: str | None) -> str:
    """Remove URLs, HTML, control chars, normalize whitespace."""
    if not text or not isinstance(text, str):
        return ""
    text = re.sub(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", " ", text, flags=re.I)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)|\[[^\]]*\]\([^)]+\)", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200b-\u200f\u2028-\u202f\u2060-\u206f\ufffe\uffff]", "", text)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\t\n\r]+", " ", text)
    text = re.sub(r" +", " ", text)
    return text.strip()


async def fetch_token() -> str:
    """Fetch token via OAuth client credentials. Use AUTH_TOKEN if set."""
    token = os.getenv("AUTH_TOKEN", "").strip()
    if token:
        return token
    client_id = os.getenv("FETCH_TOKEN_USERNAME")
    client_secret = os.getenv("FETCH_TOKEN_PASSWORD")
    if not client_id or not client_secret:
        raise ValueError("Set FETCH_TOKEN_USERNAME + FETCH_TOKEN_PASSWORD in .env")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(AUTH_URL, auth=(client_id, client_secret), data={"grant_type": "client_credentials"})
        if r.status_code == 401:
            raise ValueError("Invalid FETCH_TOKEN_USERNAME or FETCH_TOKEN_PASSWORD.")
        if r.status_code == 404:
            raise ValueError(f"Auth URL not found (404): {AUTH_URL}. Set AUTH_URL in .env.")
        r.raise_for_status()
        return r.json()["access_token"]


async def upload_file(filename: str, content: bytes, mime: str, token: str, api_key: str) -> None:
    """Upload document to Mercer API."""
    body = {"filename": filename, "mime_type": mime, "content_b64": base64.b64encode(content).decode("utf-8")}
    headers = {"Authorization": f"Bearer {token}", "x-api-key": api_key}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(UPLOAD_URL, json=body, headers=headers)
        if r.status_code == 401:
            raise ValueError("Token invalid or expired. Check FETCH_TOKEN_USERNAME and FETCH_TOKEN_PASSWORD.")
        r.raise_for_status()


def _extract_docx_local(content: bytes) -> str:
    """Fallback: extract .docx locally when API unavailable."""
    try:
        from docx import Document
        import io
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)
    except ImportError:
        return "[ERROR] Install python-docx for local fallback: pip install python-docx"
    except Exception as e:
        return f"[ERROR] Local extract failed: {e}"


async def extract_text(filename: str, content: bytes, mime: str, token: str, api_key: str, api_unavailable: list) -> str:
    body = {"filename": filename, "mime_type": mime, "content_b64": base64.b64encode(content).decode("utf-8")}
    headers = {"Authorization": f"Bearer {token}", "x-api-key": api_key}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(EXTRACT_URL, json=body, headers=headers)
            r.raise_for_status()
            data = r.json()
        raw = data.get("text") or data.get("content") or data.get("extracted_text") or data.get("body") or ""
        if isinstance(raw, list):
            raw = " ".join(str(t) for t in raw)
        return clean_extracted_text(str(raw))
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise ValueError("Token invalid or expired. Check FETCH_TOKEN_USERNAME and FETCH_TOKEN_PASSWORD.") from e
        if e.response.status_code == 404:
            if filename.lower().endswith(".docx"):
                if not api_unavailable:
                    api_unavailable.append(True)
                    print("Mercer API unavailable (404), using local extraction for .docx files.")
                return clean_extracted_text(_extract_docx_local(content))
            return f"[ERROR] API 404 - .doc files need Mercer API. Check DOC_PROCESSING_API_BASE_URL in .env"
        raise


def _check_env() -> str:
    api_key = os.getenv("DOC_PROCESSING_API_KEY")
    token = os.getenv("AUTH_TOKEN", "").strip()
    username = os.getenv("FETCH_TOKEN_USERNAME")
    password = os.getenv("FETCH_TOKEN_PASSWORD")
    if not api_key:
        raise ValueError("Set DOC_PROCESSING_API_KEY in .env")
    if not token and (not username or not password):
        raise ValueError(
            "Set AUTH_TOKEN (direct token) or FETCH_TOKEN_USERNAME + FETCH_TOKEN_PASSWORD in .env"
        )
    return api_key


async def extract_and_save(input_dir: Path, output_path: Path, local_only: bool = False) -> None:
    token = ""
    api_key = ""
    if not local_only:
        api_key = _check_env()
        print("Fetching auth token...")
        token = await fetch_token()
        print("Token obtained. Uploading and extracting documents...")
    else:
        print("Using local extraction (.docx only)...")
    files = sorted(p for p in input_dir.iterdir() if p.suffix.lower() in WORD_EXTENSIONS)
    if not files:
        print(f"No .doc/.docx files in {input_dir}")
        return
    results = []
    api_unavailable = [] if not local_only else [True]
    for i, file_path in enumerate(files):
        try:
            content = file_path.read_bytes()
            mime = MIME_TYPES.get(file_path.suffix.lower(), "application/octet-stream")
            if local_only:
                if file_path.suffix.lower() == ".docx":
                    text = clean_extracted_text(_extract_docx_local(content))
                else:
                    text = "[ERROR] .doc requires Mercer API. Run without --local-only"
            else:
                try:
                    await upload_file(file_path.name, content, mime, token, api_key)
                except httpx.HTTPStatusError:
                    pass
                text = await extract_text(file_path.name, content, mime, token, api_key, api_unavailable)
            results.append((file_path.name, text))
            print(f"  [{i+1}/{len(files)}] {file_path.name}")
        except Exception as e:
            results.append((file_path.name, f"[ERROR] {str(e)}"))
            print(f"  [{i+1}/{len(files)}] {file_path.name} - {e}")
    df = pd.DataFrame(results, columns=["fileName", "extractedText"])
    df.to_excel(output_path, index=False, engine="openpyxl")
    print(f"Wrote {len(results)} rows to {output_path}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("-i", "--input-dir", type=Path, required=True, help="Folder with Word docs")
    p.add_argument("-o", "--output", type=Path, default=Path("extracted_output.xlsx"), help="Output Excel")
    p.add_argument("--local-only", action="store_true", help="Skip Mercer API, use local extraction (.docx only)")
    args = p.parse_args()
    if not args.input_dir.exists():
        print(f"Directory not found: {args.input_dir}")
        exit(1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(extract_and_save(args.input_dir, args.output, local_only=args.local_only))


if __name__ == "__main__":
    main()
