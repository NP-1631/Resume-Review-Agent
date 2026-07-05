"""
Embedding service using fastembed (local model, no extra API key needed).
Model: BAAI/bge-small-en-v1.5 — 384 dimensions, runs locally on CPU.
"""
from __future__ import annotations
import os
from functools import lru_cache
from typing import Any, List

from fastembed import TextEmbedding


# ─── Embedding Model (singleton) ─────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_model() -> TextEmbedding:
    """Load fastembed model once and cache it."""
    return TextEmbedding(model_name="BAAI/bge-small-en-v1.5")


def generate_embedding(text: str) -> List[float]:
    """Generate a 384-dimensional embedding for the given text."""
    model = _get_model()
    # fastembed returns a generator of numpy arrays
    embeddings = list(model.embed([text]))
    return embeddings[0].tolist()  # type: ignore[return-value]


# ─── Vector Search ────────────────────────────────────────────────────────────

async def compute_similarity(
    resume_embedding: List[float],
    jd_embedding: List[float],
) -> float:
    """
    Compute cosine similarity between two embedding vectors.
    Returns a float in [0, 1].
    """
    import numpy as np

    a = np.array(resume_embedding)
    b = np.array(jd_embedding)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    # Clip to [0, 1] to handle floating-point precision errors
    return float(min(1.0, max(0.0, np.dot(a, b) / (norm_a * norm_b))))


async def vector_search_similar_resumes(
    collection: Any,
    query_embedding: List[float],
    limit: int = 5,
) -> List[dict]:
    """
    Run MongoDB Atlas $vectorSearch to find similar resumes.
    Requires a vector search index named 'resume_embedding_index'.
    Falls back to empty list if Atlas Vector Search is not configured.
    """
    try:
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "resume_embedding_index",
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": limit * 10,
                    "limit": limit,
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "resume_id": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]
        cursor = collection.aggregate(pipeline)
        return await cursor.to_list(length=limit)
    except Exception:
        return []
