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

# Mandatory/Required fields from Data Attributes (Job Solutions)
MANDATORY_FIELDS = [
    "Organization Name",
    "Job Code",
    "Position title",
    "Leadership Competency Category",
    "Current Compensation Grade",
    "Comments/Notes",
    "Typically Reports to",
    "Employee ID",
    "Manager ID",
    "Direct report counts",
    "People Management Flag",
    "Job Level",
    "Minimum Experience",
    "Pay grade",
    "Department",
    "Job Title (from Source Job Description)",
    "Job Description",
    "Base Salary",
    "Job Location",
]


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


def _cell_text(cell) -> str:
    """Recursively get all text from a cell, including nested tables."""
    parts = [p.text for p in cell.paragraphs if p.text.strip()]
    for nested_table in getattr(cell, "tables", []):
        parts.append(_table_text(nested_table))
    return "\n".join(parts)


def _table_text(table) -> str:
    """Recursively get all text from a table, including nested tables."""
    parts = []
    for row in table.rows:
        for cell in row.cells:
            text = _cell_text(cell)
            if text.strip():
                parts.append(text)
    return "\n".join(parts)


def _extract_docx(content: bytes) -> str:
    """Extract all text from .docx: paragraphs, tables (including nested), headers, footers."""
    from docx import Document
    doc = Document(io.BytesIO(content))
    parts = []
    for p in doc.paragraphs:
        if p.text.strip():
            parts.append(p.text)
    for table in doc.tables:
        parts.append(_table_text(table))
    for section in doc.sections:
        for header in (section.header, section.first_page_header):
            if header:
                for p in header.paragraphs:
                    if p.text.strip():
                        parts.append(p.text)
                for t in header.tables:
                    parts.append(_table_text(t))
        for footer in (section.footer, section.first_page_footer):
            if footer:
                for p in footer.paragraphs:
                    if p.text.strip():
                        parts.append(p.text)
                for t in footer.tables:
                    parts.append(_table_text(t))
    return "\n".join(parts) if parts else ""


def _extract_with_docx2txt(content: bytes, ext: str) -> str:
    """Extract using docx2txt - parses raw XML, gets tables and all content."""
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        f.write(content)
        path = f.name
    try:
        import docx2txt
        return docx2txt.process(path) or ""
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _extract_docx_raw_xml(content: bytes) -> str:
    """Extract all text from docx by parsing XML - catches text in shapes, content controls, etc."""
    import zipfile
    import xml.etree.ElementTree as ET
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    texts = []
    with zipfile.ZipFile(io.BytesIO(content), "r") as z:
        for name in z.namelist():
            if "word/" in name and name.endswith(".xml"):
                try:
                    tree = ET.parse(z.open(name))
                    for el in tree.getroot().iter(f"{{{ns}}}t"):
                        if el.text:
                            texts.append(el.text)
                        if el.tail:
                            texts.append(el.tail)
                except ET.ParseError:
                    pass
    return "".join(texts)


def extract_text(content: bytes, filename: str) -> str:
    """Extract text using Python libraries. Tries docx2txt first (comprehensive), fallback to python-docx."""
    ext = Path(filename).suffix.lower()
    try:
        if ext == ".docx":
            raw = _extract_with_docx2txt(content, ".docx")
            docx_text = _extract_docx(content)
            if len(docx_text) > len(raw):
                raw = docx_text
            xml_text = _extract_docx_raw_xml(content)
            if len(xml_text) > len(raw):
                raw = xml_text
        elif ext == ".doc":
            try:
                raw = _extract_with_docx2txt(content, ".doc")
            except Exception:
                raw = "[ERROR] .doc extraction failed. Try converting to .docx."
        else:
            return ""
        return preprocess_text(raw)
    except ImportError as e:
        return f"[ERROR] Install python-docx and docx2txt: pip install python-docx docx2txt"
    except Exception as e:
        return f"[ERROR] Extraction failed: {e}"


def _is_field_label(line: str) -> bool:
    return any(line.lower().startswith(f.lower()) for f in MANDATORY_FIELDS)


def parse_fields(text: str) -> dict[str, str]:
    """Extract field values from preprocessed text. Handles 'Field: value', 'Field - value', table rows."""
    text = text or ""
    result = {f: "" for f in MANDATORY_FIELDS}
    lines = [ln.strip() for ln in text.replace("\r", "\n").split("\n") if ln.strip()]
    for i, line in enumerate(lines):
        for field in MANDATORY_FIELDS:
            if result[field]:
                continue
            if not line.lower().startswith(field.lower()):
                continue
            for sep in (":", "-"):
                if sep in line:
                    val = line.split(sep, 1)[1].strip()
                    max_len = 8000 if field == "Job Description" else 1000
                    result[field] = val[:max_len]
                    break
            if not result[field] and i + 1 < len(lines) and not _is_field_label(lines[i + 1]):
                result[field] = lines[i + 1][:1000]
            break
    for field in MANDATORY_FIELDS:
        if result[field]:
            continue
        escaped = re.escape(field)
        m = re.search(rf"{escaped}\s*[:\-]\s*(.+?)(?=\n\s*[A-Z]|\n\n|$)", text, re.DOTALL | re.I)
        if m:
            val = re.sub(r"\s+", " ", m.group(1).strip())
            max_len = 8000 if field == "Job Description" else 1000
            result[field] = val[:max_len]
    return result


def extract_and_save(input_dir: Path, output_path: Path) -> None:
    files = sorted(p for p in input_dir.iterdir() if p.suffix.lower() in WORD_EXTENSIONS)
    if not files:
        print(f"No .doc/.docx files in {input_dir}")
        return
    print(f"Extracting and preprocessing {len(files)} file(s)...")
    rows = []
    for i, file_path in enumerate(files):
        content = file_path.read_bytes()
        text = extract_text(content, file_path.name)
        fields = parse_fields(text)
        row = {"fileName": file_path.name, "extractedText": text}
        row.update(fields)
        rows.append(row)
        print(f"  [{i+1}/{len(files)}] {file_path.name}")
    df = pd.DataFrame(rows)
    key_cols = ["fileName", "Organization Name", "Job Code", "Position title", "Job Title (from Source Job Description)", "Job Description", "Base Salary", "Job Location"]
    rest = [c for c in MANDATORY_FIELDS if c not in key_cols[1:]]
    col_order = key_cols + rest + ["extractedText"]
    df = df[[c for c in col_order if c in df.columns]]
    df.to_excel(output_path, index=False, engine="openpyxl")
    print(f"Wrote {len(rows)} rows to {output_path}")


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
