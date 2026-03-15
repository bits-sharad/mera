#!/usr/bin/env python3
"""
Extract text from Word documents via Mercer Document Processing API and export to Excel.

Usage:
    python batch_word_extract_to_excel.py -i "path/to/docs" -o "output.xlsx"

Setup:
    1. Copy .env.example to .env and fill in your Mercer API credentials
    2. pip install -r requirements.txt

Environment (required in .env or shell):
    DOC_PROCESSING_API_KEY
    FETCH_TOKEN_USERNAME
    FETCH_TOKEN_PASSWORD
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

AUTH_URL = "https://stg1.mmc-bedford-int-non-prod-ingress.mgti.mmc.com/authentication/v1/oauth2/token"
EXTRACT_URL = "https://stg1.mmc-dallas-int-non-prod-ingress.mgti.mmc.com/coreapi/document-processing/v1/documents/extract"

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
    client_id = os.getenv("FETCH_TOKEN_USERNAME")
    client_secret = os.getenv("FETCH_TOKEN_PASSWORD")
    if not client_id or not client_secret:
        raise ValueError("Set FETCH_TOKEN_USERNAME and FETCH_TOKEN_PASSWORD")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(AUTH_URL, auth=(client_id, client_secret), data={"grant_type": "client_credentials"})
        r.raise_for_status()
        return r.json()["access_token"]


async def extract_text(filename: str, content: bytes, mime: str, token: str, api_key: str) -> str:
    body = {"filename": filename, "mime_type": mime, "content_b64": base64.b64encode(content).decode("utf-8")}
    headers = {"Authorization": f"Bearer {token}", "x-api-key": api_key}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(EXTRACT_URL, json=body, headers=headers)
        r.raise_for_status()
        data = r.json()
    raw = data.get("text") or data.get("content") or data.get("extracted_text") or data.get("body") or ""
    if isinstance(raw, list):
        raw = " ".join(str(t) for t in raw)
    return clean_extracted_text(str(raw))


def _check_env() -> str:
    api_key = os.getenv("DOC_PROCESSING_API_KEY")
    username = os.getenv("FETCH_TOKEN_USERNAME")
    password = os.getenv("FETCH_TOKEN_PASSWORD")
    missing = []
    if not api_key:
        missing.append("DOC_PROCESSING_API_KEY")
    if not username:
        missing.append("FETCH_TOKEN_USERNAME")
    if not password:
        missing.append("FETCH_TOKEN_PASSWORD")
    if missing:
        env_file = _script_dir / ".env"
        raise ValueError(
            f"Missing: {', '.join(missing)}. "
            f"Create {env_file} from .env.example and add your Mercer API credentials."
        )
    return api_key


async def extract_and_save(input_dir: Path, output_path: Path) -> None:
    api_key = _check_env()
    token = await fetch_token()
    files = sorted(p for p in input_dir.iterdir() if p.suffix.lower() in WORD_EXTENSIONS)
    if not files:
        print(f"No .doc/.docx files in {input_dir}")
        return
    results = []
    for file_path in files:
        try:
            content = file_path.read_bytes()
            mime = MIME_TYPES.get(file_path.suffix.lower(), "application/octet-stream")
            text = await extract_text(file_path.name, content, mime, token, api_key)
            results.append((file_path.name, text))
        except Exception as e:
            results.append((file_path.name, f"[ERROR] {str(e)}"))
    df = pd.DataFrame(results, columns=["fileName", "extractedText"])
    df.to_excel(output_path, index=False, engine="openpyxl")
    print(f"Wrote {len(results)} rows to {output_path}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("-i", "--input-dir", type=Path, required=True, help="Folder with Word docs")
    p.add_argument("-o", "--output", type=Path, default=Path("extracted_output.xlsx"), help="Output Excel")
    args = p.parse_args()
    if not args.input_dir.exists():
        print(f"Directory not found: {args.input_dir}")
        exit(1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(extract_and_save(args.input_dir, args.output))


if __name__ == "__main__":
    main()
