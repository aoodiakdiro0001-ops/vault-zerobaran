"""
Vault-ZeroBaran — Vector Database Layer (Supabase + pgvector).

Operations:
  * ensure_schema()      — create the `documents` table + pgvector index.
  * store_chunks()       — insert chunks + embeddings.
  * similarity_search()  — top-K cosine search for a query vector.
  * list_documents()     — show indexed files.
  * delete_document()    — remove a file's chunks by name.

Uses Supabase HTTP API when possible; falls back to direct psycopg2
for batch inserts and pgvector <-> operations.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from loguru import logger

from config.settings import settings
from core.ingestion import Chunk
from core.embeddings import embed_texts, embed_query, EMBEDDING_DIM


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
-- Enable pgvector extension (Supabase dashboard → Database → Extensions)
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents / chunks table
CREATE TABLE IF NOT EXISTS vault_chunks (
    id            BIGSERIAL PRIMARY KEY,
    chunk_id      TEXT UNIQUE,
    source_file   TEXT NOT NULL,
    page          INT NOT NULL DEFAULT 0,
    section       TEXT DEFAULT '',
    content       TEXT NOT NULL,
    token_count   INT DEFAULT 0,
    metadata      JSONB DEFAULT '{{}}'::jsonb,
    embedding     vector({dim}),
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- Index for fast similarity search (HNSW)
CREATE INDEX IF NOT EXISTS vault_chunks_embedding_idx
    ON vault_chunks USING hnsw (embedding vector_cosine_ops);

-- Index for fast file-name lookups
CREATE INDEX IF NOT EXISTS vault_chunks_source_file_idx
    ON vault_chunks (source_file);

-- Metadata index
CREATE INDEX IF NOT EXISTS vault_chunks_metadata_gin_idx
    ON vault_chunks USING gin (metadata jsonb_path_ops);
""".format(dim=EMBEDDING_DIM)


# ---------------------------------------------------------------------------
# Lazy clients
# ---------------------------------------------------------------------------
_supabase_client = None
_pg_conn = None


def _get_supabase():
    global _supabase_client
    if _supabase_client is None:
        if not settings.has_supabase:
            raise RuntimeError("Supabase not configured. Set SUPABASE_URL & SUPABASE_KEY.")
        from supabase import create_client
        _supabase_client = create_client(settings.supabase_url, settings.supabase_key)
    return _supabase_client


def _get_pg():
    """Direct psycopg2 connection — needed for `vector` type inserts."""
    global _pg_conn
    if _pg_conn is None:
        if not settings.supabase_db_url or "your_" in settings.supabase_db_url:
            raise RuntimeError(
                "SUPABASE_DB_URL not configured. Set the direct Postgres connection string."
            )
        import psycopg2
        _pg_conn = psycopg2.connect(settings.supabase_db_url)
    return _pg_conn


def ensure_schema() -> None:
    """Create the SQL schema if it doesn't exist (idempotent)."""
    conn = _get_pg()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)
    logger.success("Schema ensured: vault_chunks table + pgvector HNSW index ready.")


# ---------------------------------------------------------------------------
# Insert
# ---------------------------------------------------------------------------
def store_chunks(chunks: Sequence[Chunk]) -> int:
    """
    Embed and store a list of chunks. Returns the number actually inserted.
    """
    if not chunks:
        return 0

    logger.info(f"Embedding {len(chunks)} chunks via Gemini...")
    vectors = embed_texts([c.text for c in chunks])

    conn = _get_pg()
    conn.autocommit = False
    inserted = 0
    try:
        with conn.cursor() as cur:
            for ch, vec in zip(chunks, vectors):
                vec_str = "[" + ",".join(f"{x:.7f}" for x in vec) + "]"
                cur.execute(
                    """
                    INSERT INTO vault_chunks
                        (chunk_id, source_file, page, section, content,
                         token_count, metadata, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (chunk_id) DO UPDATE
                        SET content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            token_count = EXCLUDED.token_count,
                            metadata = EXCLUDED.metadata
                    """,
                    (
                        ch.chunk_id,
                        ch.source_file,
                        ch.page,
                        ch.section,
                        ch.text,
                        ch.token_count,
                        __import__("json").dumps(ch.metadata),
                        vec_str,
                    ),
                )
                inserted += 1
        conn.commit()
        logger.success(f"Stored {inserted}/{len(chunks)} chunks in Supabase.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Insert failed: {e}")
        raise
    return inserted


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
def similarity_search(query_text: str, top_k: int | None = None) -> list[dict]:
    """
    Top-K cosine similarity search.

    Returns list of dicts: {source_file, page, section, content, score, metadata}.
    """
    k = top_k or settings.vault_top_k
    qvec = embed_query(query_text)
    vec_str = "[" + ",".join(f"{x:.7f}" for x in qvec.tolist()) + "]"

    conn = _get_pg()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT source_file, page, section, content, metadata,
                   1 - (embedding <=> %s::vector) AS score
            FROM vault_chunks
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (vec_str, vec_str, k),
        )
        rows = cur.fetchall()

    results = []
    for r in rows:
        results.append({
            "source_file": r[0],
            "page":        r[1],
            "section":     r[2],
            "content":     r[3],
            "metadata":    r[4] if isinstance(r[4], dict) else {},
            "score":       float(r[5]) if r[5] is not None else 0.0,
        })
    logger.info(f"Retrieved {len(results)} chunks for query (top_k={k}).")
    return results


# ---------------------------------------------------------------------------
# Admin helpers
# ---------------------------------------------------------------------------
def list_documents() -> list[dict]:
    """Aggregate file-level stats from the table."""
    conn = _get_pg()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("""
            SELECT source_file,
                   COUNT(*)              AS chunks,
                   SUM(token_count)      AS tokens,
                   MIN(page)             AS first_page,
                   MAX(page)             AS last_page,
                   MAX(created_at)       AS last_indexed
            FROM vault_chunks
            GROUP BY source_file
            ORDER BY source_file
        """)
        rows = cur.fetchall()
    return [
        {
            "source_file":  r[0],
            "chunks":       r[1],
            "tokens":       r[2] or 0,
            "first_page":   r[3] or 0,
            "last_page":    r[4] or 0,
            "last_indexed": r[5].isoformat() if r[5] else None,
        }
        for r in rows
    ]


def delete_document(source_file: str) -> int:
    conn = _get_pg()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("DELETE FROM vault_chunks WHERE source_file = %s", (source_file,))
        deleted = cur.rowcount
    logger.info(f"Deleted {deleted} chunks for '{source_file}'.")
    return deleted


def total_chunks() -> int:
    conn = _get_pg()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM vault_chunks")
        return cur.fetchone()[0] or 0
