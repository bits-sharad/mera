#!/usr/bin/env python3
"""
Extract text from Word documents using Python libraries and export to Excel.

Extraction: python-docx (paragraphs, tables, headers, footers) + docx2txt for .doc
Preprocessing: remove URLs, HTML, control chars, normalize whitespace.

Usage:
    python batch_word_extract_to_excel.py -i "path/to/docs" -o "output.xlsx"
"""
from __future__ import annotations

import argparse
import io
import os
import re
import tempfile
import unicodedata
from pathlib import Path

import pandas as pd

WORD_EXTENSIONS = {".doc", ".docx"}


def preprocess_text(text: str | None) -> str:
    """Clean and preprocess: remove URLs, HTML, control chars, normalize whitespace."""
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


def _extract_docx(content: bytes) -> str:
    """Extract all text from .docx: paragraphs, tables, headers, footers."""
    from docx import Document
    doc = Document(io.BytesIO(content))
    parts = []
    for p in doc.paragraphs:
        if p.text.strip():
            parts.append(p.text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    parts.append(cell.text)
    for section in doc.sections:
        for header in (section.header, section.first_page_header):
            if header:
                for p in header.paragraphs:
                    if p.text.strip():
                        parts.append(p.text)
        for footer in (section.footer, section.first_page_footer):
            if footer:
                for p in footer.paragraphs:
                    if p.text.strip():
                        parts.append(p.text)
    return "\n".join(parts) if parts else ""


def _extract_doc(content: bytes) -> str:
    """Extract from .doc using docx2txt."""
    with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as f:
        f.write(content)
        path = f.name
    try:
        import docx2txt
        return docx2txt.process(path) or ""
    finally:
        os.unlink(path)


def extract_text(content: bytes, filename: str) -> str:
    """Extract text using Python libraries."""
    ext = Path(filename).suffix.lower()
    try:
        if ext == ".docx":
            raw = _extract_docx(content)
        elif ext == ".doc":
            raw = _extract_doc(content)
        else:
            return ""
        return preprocess_text(raw)
    except ImportError as e:
        return f"[ERROR] Install python-docx and docx2txt: pip install python-docx docx2txt"
    except Exception as e:
        return f"[ERROR] Extraction failed: {e}"


def extract_and_save(input_dir: Path, output_path: Path) -> None:
    files = sorted(p for p in input_dir.iterdir() if p.suffix.lower() in WORD_EXTENSIONS)
    if not files:
        print(f"No .doc/.docx files in {input_dir}")
        return
    print(f"Extracting and preprocessing {len(files)} file(s)...")
    results = []
    for i, file_path in enumerate(files):
        content = file_path.read_bytes()
        text = extract_text(content, file_path.name)
        results.append((file_path.name, text))
        print(f"  [{i+1}/{len(files)}] {file_path.name}")
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
    extract_and_save(args.input_dir, args.output)


if __name__ == "__main__":
    main()
