#!/usr/bin/env python3
"""
Extract text from Word documents via Mercer API and export to Excel.

Usage:
    python scripts/batch_word_extract_to_excel.py -i "path/to/docs" -o "output.xlsx"
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

_api_dir = Path(__file__).resolve().parent.parent
if str(_api_dir) not in sys.path:
    sys.path.insert(0, str(_api_dir))
os.environ.setdefault("APP_ENV", "dev")

import pandas as pd
from src.clients.doc_processing_api import DocumentProcessingAPIClient
from src.utility.helper import clean_extracted_text

WORD_EXTENSIONS = {".doc", ".docx"}
MIME_TYPES = {
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


async def extract_and_save(input_dir: Path, output_path: Path) -> None:
    doc_client = DocumentProcessingAPIClient()
    files = sorted(p for p in input_dir.iterdir() if p.suffix.lower() in WORD_EXTENSIONS)

    if not files:
        print(f"No .doc/.docx files in {input_dir}")
        return

    results = []
    for file_path in files:
        try:
            content = file_path.read_bytes()
            mime = MIME_TYPES.get(file_path.suffix.lower(), "application/octet-stream")
            r = await doc_client.extract(file_path.name, content, mime_type=mime)
            raw = r.get("text") or r.get("content") or r.get("extracted_text") or r.get("body") or ""
            if isinstance(raw, list):
                raw = " ".join(str(t) for t in raw)
            text = clean_extracted_text(str(raw))
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
        sys.exit(1)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    asyncio.run(extract_and_save(args.input_dir, args.output))


if __name__ == "__main__":
    main()
