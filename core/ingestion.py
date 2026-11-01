"""
Vault-ZeroBaran — Ingestion & Chunking Layer.

Responsibilities:
  * Extract raw text from PDF / DOCX / XLSX / TXT / CSV / MD files.
  * Track page numbers and source filename for every chunk.
  * Split text into semantically-coherent chunks (with overlap).
  * Return a list of `Chunk` objects ready for embedding.

100% free libraries: PyMuPDF, python-docx, openpyxl, pandas, chardet,
langchain-text-splitters.
"""
from __future__ import annotations

import os
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import fitz  # PyMuPDF
from docx import Document as DocxDocument
from loguru import logger
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import settings


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class Chunk:
    """One semantic unit of a document."""
    chunk_id: str           # stable hash
    text: str
    source_file: str
    page: int               # 1-indexed; 0 for non-paginated files
    section: str = ""       # optional heading / sheet name
    token_count: int = 0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source_file": self.source_file,
            "page": self.page,
            "section": self.section,
            "token_count": self.token_count,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Per-format extractors
# ---------------------------------------------------------------------------
def _extract_pdf(path: Path) -> list[tuple[str, int]]:
    """Return list of (page_text, page_number) tuples."""
    out: list[tuple[str, int]] = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc, start=1):
            txt = page.get_text("text") or ""
            if txt.strip():
                out.append((txt.strip(), i))
    return out


def _extract_docx(path: Path) -> list[tuple[str, int]]:
    """A DOCX has no real pages — we treat paragraphs as one logical page=1."""
    doc = DocxDocument(str(path))
    parts: list[str] = []
    for para in doc.paragraphs:
        if para.text.strip():
            parts.append(para.text.strip())
    # Tables
    for tbl in doc.tables:
        for row in tbl.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return [("\n".join(parts), 1)] if parts else []


def _extract_xlsx(path: Path) -> list[tuple[str, int]]:
    import openpyxl
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    out: list[tuple[str, int]] = []
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        rows_text = []
        for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
            cells = [str(c) for c in row if c is not None]
            if cells:
                rows_text.append(" | ".join(cells))
            if i > 5000:  # safety cap
                break
        if rows_text:
            out.append(("\n".join(rows_text), 1))
    return out


def _extract_csv(path: Path) -> list[tuple[str, int]]:
    import pandas as pd
    df = pd.read_csv(path)
    return [(df.to_csv(index=False), 1)]


def _extract_txt(path: Path) -> list[tuple[str, int]]:
    import chardet
    raw = path.read_bytes()
    enc = chardet.detect(raw).get("encoding") or "utf-8"
    try:
        text = raw.decode(enc, errors="replace")
    except Exception:
        text = raw.decode("utf-8", errors="replace")
    return [(text, 1)] if text.strip() else []


_EXTRACTORS = {
    ".pdf":  _extract_pdf,
    ".docx": _extract_docx,
    ".xlsx": _extract_xlsx,
    ".csv":  _extract_csv,
    ".txt":  _extract_txt,
    ".md":   _extract_txt,
    ".py":   _extract_txt,
    ".js":   _extract_txt,
    ".json": _extract_txt,
}


# ---------------------------------------------------------------------------
# Chunker
# ---------------------------------------------------------------------------
def _make_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.vault_chunk_size,
        chunk_overlap=settings.vault_chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def _stable_id(source: str, page: int, idx: int, text: str) -> str:
    h = hashlib.sha1(f"{source}|{page}|{idx}|{text[:80]}".encode("utf-8")).hexdigest()
    return h[:16]


def _approx_tokens(text: str) -> int:
    """Rough token estimate: 1 token ≈ 4 chars (good enough for budgeting)."""
    return max(1, len(text) // 4)


def ingest_file(path: str | Path) -> list[Chunk]:
    """
    Parse a single file into a list of semantic chunks.

    Args:
        path: file path (PDF/DOCX/XLSX/CSV/TXT/MD/PY/JS/JSON).
    Returns:
        List of Chunk objects.
    """
    p = Path(path)
    if not p.exists():
        logger.warning(f"File not found: {p}")
        return []

    ext = p.suffix.lower()
    extractor = _EXTRACTORS.get(ext)
    if extractor is None:
        logger.warning(f"Unsupported format '{ext}' for {p.name}")
        return []

    try:
        pages = extractor(p)
    except Exception as e:
        logger.error(f"Failed to extract {p.name}: {e}")
        return []

    splitter = _make_splitter()
    chunks: list[Chunk] = []
    source_name = p.name

    for text, page_no in pages:
        if not text or not text.strip():
            continue
        pieces = splitter.split_text(text)
        for i, piece in enumerate(pieces):
            piece = piece.strip()
            if len(piece) < 20:
                continue
            chunks.append(Chunk(
                chunk_id=_stable_id(source_name, page_no, i, piece),
                text=piece,
                source_file=source_name,
                page=page_no,
                section="",
                token_count=_approx_tokens(piece),
                metadata={
                    "absolute_path": str(p.resolve()),
                    "extension": ext,
                    "size_bytes": p.stat().st_size,
                },
            ))

    logger.info(f"Ingested '{source_name}': {len(chunks)} chunks across {len(pages)} page(s).")
    return chunks


def ingest_folder(folder: str | Path,
                  extensions: Iterable[str] | None = None) -> list[Chunk]:
    """
    Walk a folder recursively and ingest every supported file.
    """
    f = Path(folder)
    if not f.exists():
        logger.error(f"Folder does not exist: {f}")
        return []

    valid_exts = {e.lower() for e in (extensions or _EXTRACTORS.keys())}
    all_chunks: list[Chunk] = []

    for root, _, files in os.walk(f):
        for name in files:
            if Path(name).suffix.lower() in valid_exts:
                all_chunks.extend(ingest_file(Path(root) / name))

    logger.info(f"Total chunks from '{f}': {len(all_chunks)}")
    return all_chunks
