#!/usr/bin/env python3
"""
Vault-ZeroBaran — CLI: Ingest a folder of documents.

Usage:
    # Initialize Supabase schema
    python scripts/ingest_folder.py --init-db

    # Ingest a single file
    python scripts/ingest_folder.py --file /path/to/contract.pdf

    # Ingest a whole folder (recursive)
    python scripts/ingest_folder.py --folder /path/to/docs

    # Ingest the default ./data/uploads folder
    python scripts/ingest_folder.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Project root importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loguru import logger

from config.settings import settings
from core.utils import banner, ingest_summary
from core.ingestion import ingest_file, ingest_folder
from core.vector_db import ensure_schema, store_chunks, total_chunks


def cmd_init_db() -> int:
    print(banner())
    logger.info("Initializing Supabase schema...")
    try:
        ensure_schema()
        logger.success("✅ Schema ready. Run `scripts/setup_db.sql` in Supabase SQL editor too, for safety.")
        return 0
    except Exception as e:
        logger.error(f"Failed: {e}")
        return 1


def cmd_ingest_file(path: str) -> int:
    print(banner())
    logger.info(f"Ingesting single file: {path}")
    chunks = ingest_file(path)
    if not chunks:
        logger.error("No chunks extracted. Aborting.")
        return 1
    summary = ingest_summary(chunks)
    logger.info(f"Extracted {summary['total_chunks']} chunks "
                f"from {summary['total_files']} file(s), "
                f"~{summary['total_tokens']} tokens.")
    try:
        stored = store_chunks(chunks)
        logger.success(f"✅ Stored {stored} chunks in Supabase.")
        logger.info(f"Vault now holds {total_chunks()} chunks total.")
        return 0
    except Exception as e:
        logger.error(f"Storage failed: {e}")
        return 2


def cmd_ingest_folder(folder: str) -> int:
    print(banner())
    logger.info(f"Ingesting folder recursively: {folder}")
    chunks = ingest_folder(folder)
    if not chunks:
        logger.warning("No chunks extracted from the folder.")
        return 1
    summary = ingest_summary(chunks)
    logger.info(f"Total: {summary['total_chunks']} chunks across "
                f"{summary['total_files']} file(s), "
                f"~{summary['total_tokens']} tokens.")
    logger.info("Per-file breakdown:")
    for fname, n in summary["per_file"].items():
        logger.info(f"  • {fname}: {n} chunks")

    try:
        stored = store_chunks(chunks)
        logger.success(f"✅ Stored {stored} chunks in Supabase.")
        logger.info(f"Vault now holds {total_chunks()} chunks total.")
        return 0
    except Exception as e:
        logger.error(f"Storage failed: {e}")
        return 2


def main() -> int:
    p = argparse.ArgumentParser(
        description="Vault-ZeroBaran — Folder/File Ingestion CLI"
    )
    p.add_argument("--init-db", action="store_true",
                   help="Create the Supabase pgvector schema.")
    p.add_argument("--file", metavar="PATH",
                   help="Ingest a single file.")
    p.add_argument("--folder", metavar="DIR",
                   help="Ingest a folder recursively.")
    args = p.parse_args()

    if args.init_db:
        return cmd_init_db()
    if args.file:
        return cmd_ingest_file(args.file)
    if args.folder:
        return cmd_ingest_folder(args.folder)

    # Default: ingest the configured data dir
    folder = str(settings.data_dir)
    logger.info(f"No target provided — using default data dir: {folder}")
    return cmd_ingest_folder(folder)


if __name__ == "__main__":
    sys.exit(main())
