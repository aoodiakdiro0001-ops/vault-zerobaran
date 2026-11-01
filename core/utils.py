"""
Vault-ZeroBaran — Common utilities.

Helpers for saving uploaded files, building a project banner, formatting
durations, and computing simple statistics over an ingest run.
"""
from __future__ import annotations

import os
import time
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Iterable

from config.settings import settings
from core.ingestion import Chunk


def save_upload(src_path: str | Path, filename: str | None = None) -> Path:
    """
    Move/copy an uploaded file into the Vault data directory.
    Returns the destination path.
    """
    src = Path(src_path)
    name = filename or src.name
    dest_dir = settings.data_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name
    # Avoid clobbering: append timestamp suffix if file already exists
    if dest.exists():
        stem, ext = os.path.splitext(name)
        dest = dest_dir / f"{stem}_{int(time.time())}{ext}"
    shutil.copy2(src, dest) if src.exists() else None
    return dest


def file_md5(path: str | Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def banner() -> str:
    """ASCII banner shown on startup."""
    return r"""
 __     __              ______              _____
 \ \   / /_ _ ___ _   _|  ___|__  _ __ ___ |  ___|
  \ \ / / _` / __| | | | |_ / _ \| '__/ _ \| |_
   \ V / (_| \__ \ |_| |  _| (_) | | |  __/| |
    \_/ \__,_|___/\__, \_|  \___/|_|  \___||_|   ·Zero·Baran
                  |___/
        Self-Knowledge Brain  •  100% Free Tech Stack
"""


def timestamp_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def ingest_summary(chunks: Iterable[Chunk]) -> dict:
    chunks = list(chunks)
    by_file: dict[str, int] = {}
    total_tokens = 0
    for c in chunks:
        by_file[c.source_file] = by_file.get(c.source_file, 0) + 1
        total_tokens += c.token_count
    return {
        "total_chunks": len(chunks),
        "total_files": len(by_file),
        "total_tokens": total_tokens,
        "per_file": by_file,
        "timestamp": timestamp_now(),
    }
