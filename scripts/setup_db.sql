-- ============================================================
--  Vault-ZeroBaran — Supabase / pgvector Schema Setup
--  Run this in: Supabase Dashboard → SQL Editor → New Query
-- ============================================================

-- 1) Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2) Drop old table if you want a clean reset (comment out if not needed)
-- DROP TABLE IF EXISTS vault_chunks CASCADE;

-- 3) Main table
CREATE TABLE IF NOT EXISTS vault_chunks (
    id            BIGSERIAL PRIMARY KEY,
    chunk_id      TEXT UNIQUE,
    source_file   TEXT NOT NULL,
    page          INT NOT NULL DEFAULT 0,
    section       TEXT DEFAULT '',
    content       TEXT NOT NULL,
    token_count   INT DEFAULT 0,
    metadata      JSONB DEFAULT '{}'::jsonb,
    embedding     vector(768),
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- 4) HNSW index for fast cosine similarity search
CREATE INDEX IF NOT EXISTS vault_chunks_embedding_idx
    ON vault_chunks USING hnsw (embedding vector_cosine_ops);

-- 5) B-tree index for fast file lookups
CREATE INDEX IF NOT EXISTS vault_chunks_source_file_idx
    ON vault_chunks (source_file);

-- 6) GIN index for metadata queries
CREATE INDEX IF NOT EXISTS vault_chunks_metadata_gin_idx
    ON vault_chunks USING gin (metadata jsonb_path_ops);

-- 7) Helpful view: file-level statistics
CREATE OR REPLACE VIEW vault_documents AS
SELECT
    source_file,
    COUNT(*)            AS chunks,
    SUM(token_count)    AS tokens,
    MIN(page)           AS first_page,
    MAX(page)           AS last_page,
    MIN(created_at)     AS first_indexed,
    MAX(created_at)     AS last_indexed
FROM vault_chunks
GROUP BY source_file
ORDER BY source_file;

-- 8) Row Level Security (optional — recommended if Supabase is shared)
-- ALTER TABLE vault_chunks ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "allow_all_for_owner" ON vault_chunks
--     FOR ALL USING (true) WITH CHECK (true);

-- 9) Quick verification
SELECT 'Vault-ZeroBaran schema ready ✓' AS status;
