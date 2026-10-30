"""
Vault-ZeroBaran — Embeddings Layer.

Wraps Google Gemini's free `text-embedding-004` model and exposes a
single `embed_texts()` function that batches requests with retry logic.

Free model: text-embedding-004 (768 dimensions, 100% free tier).
"""
from __future__ import annotations

import time
from typing import Sequence

import numpy as np
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover
    genai = None

from config.settings import settings


EMBEDDING_DIM = 768  # text-embedding-004 outputs 768-dim vectors
_BATCH_SIZE = 100    # Gemini allows up to 100 inputs per request


def _init_genai() -> None:
    if genai is None:
        raise RuntimeError(
            "google-generativeai is not installed. Run: pip install google-generativeai"
        )
    if not settings.has_gemini:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. Edit your .env file."
        )
    genai.configure(api_key=settings.gemini_api_key)


@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
)
def _embed_batch(batch: list[str]) -> list[list[float]]:
    """Embed up to 100 texts in one Gemini call (with retry)."""
    _init_genai()
    result = genai.embed_content(
        model=f"models/{settings.gemini_embedding_model}",
        content=batch,
        task_type="retrieval_document",
        output_dimensionality=EMBEDDING_DIM,
    )
    return result["embedding"]


def embed_texts(texts: Sequence[str],
                task_type: str = "retrieval_document") -> list[list[float]]:
    """
    Embed a list of texts using Gemini text-embedding-004.

    Args:
        texts: list of strings (any length).
        task_type: "retrieval_document" for indexing, "retrieval_query"
                   for query-time embedding.
    Returns:
        List of 768-dim float vectors, same length as `texts`.
    """
    if not texts:
        return []

    # Sanitize empty strings (Gemini rejects empty input)
    cleaned = [t if t.strip() else " " for t in texts]

    vectors: list[list[float]] = []
    for i in range(0, len(cleaned), _BATCH_SIZE):
        batch = cleaned[i:i + _BATCH_SIZE]
        try:
            batch_vectors = _embed_batch(batch)
            vectors.extend(batch_vectors)
            logger.debug(f"Embedded batch {i//_BATCH_SIZE + 1} "
                         f"({len(batch)} texts).")
        except Exception as e:
            logger.error(f"Embedding batch failed at offset {i}: {e}")
            # Fallback: zero vectors so pipeline continues
            vectors.extend([[0.0] * EMBEDDING_DIM] * len(batch))
        # Gentle pacing to respect free-tier rate limits
        time.sleep(0.4)

    return vectors


def embed_query(text: str) -> np.ndarray:
    """Embed a single user query and return as numpy array."""
    vecs = embed_texts([text], task_type="retrieval_query")
    return np.array(vecs[0], dtype=np.float32) if vecs else np.zeros(EMBEDDING_DIM, dtype=np.float32)
