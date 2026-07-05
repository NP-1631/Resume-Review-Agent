"""
Unit tests for embedding_service.py — embedding generation and cosine similarity.
fastembed model is mocked to avoid downloading anything.
"""
from __future__ import annotations
import math
import numpy as np
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from tests.conftest import SAMPLE_EMBEDDING


# ── Embedding Generation ──────────────────────────────────────────────────────

class TestGenerateEmbedding:
    def test_returns_list_of_floats(self, sample_resume_text):
        """generate_embedding returns a list of floats."""
        mock_model = MagicMock()
        mock_model.embed.return_value = iter([np.array(SAMPLE_EMBEDDING)])

        with patch("app.services.embedding_service._get_model", return_value=mock_model):
            from app.services.embedding_service import generate_embedding
            result = generate_embedding(sample_resume_text)

        assert isinstance(result, list)
        assert all(isinstance(v, float) for v in result)

    def test_embedding_has_correct_dimensions(self, sample_resume_text):
        """Embedding vector has 384 dimensions."""
        mock_model = MagicMock()
        mock_model.embed.return_value = iter([np.array(SAMPLE_EMBEDDING)])

        with patch("app.services.embedding_service._get_model", return_value=mock_model):
            from app.services.embedding_service import generate_embedding
            result = generate_embedding(sample_resume_text)

        assert len(result) == 384

    def test_model_called_with_text_list(self, sample_resume_text):
        """fastembed model.embed is called with a list containing the input text."""
        mock_model = MagicMock()
        mock_model.embed.return_value = iter([np.array(SAMPLE_EMBEDDING)])

        with patch("app.services.embedding_service._get_model", return_value=mock_model):
            from app.services.embedding_service import generate_embedding
            generate_embedding(sample_resume_text)

        mock_model.embed.assert_called_once_with([sample_resume_text])


# ── Cosine Similarity ─────────────────────────────────────────────────────────

class TestComputeSimilarity:
    @pytest.mark.asyncio
    async def test_identical_vectors_give_score_1(self):
        """Two identical vectors have cosine similarity of 1.0."""
        from app.services.embedding_service import compute_similarity
        vec = [0.5] * 384
        result = await compute_similarity(vec, vec)
        assert abs(result - 1.0) < 1e-6

    @pytest.mark.asyncio
    async def test_orthogonal_vectors_give_score_0(self):
        """Orthogonal vectors have cosine similarity near 0."""
        from app.services.embedding_service import compute_similarity
        vec_a = [1.0] + [0.0] * 383
        vec_b = [0.0, 1.0] + [0.0] * 382
        result = await compute_similarity(vec_a, vec_b)
        assert abs(result) < 1e-6

    @pytest.mark.asyncio
    async def test_zero_vector_returns_0(self):
        """Zero vector edge case returns 0.0."""
        from app.services.embedding_service import compute_similarity
        zero = [0.0] * 384
        normal = [0.1] * 384
        result = await compute_similarity(zero, normal)
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_similarity_is_between_0_and_1(self, sample_embedding):
        """Similarity score is always in [0, 1]."""
        from app.services.embedding_service import compute_similarity
        # Slightly different vectors
        vec_b = [v + 0.01 for v in sample_embedding]
        result = await compute_similarity(sample_embedding, vec_b)
        assert 0.0 <= result <= 1.0

    @pytest.mark.asyncio
    async def test_symmetry(self, sample_embedding):
        """sim(a, b) == sim(b, a)."""
        from app.services.embedding_service import compute_similarity
        vec_b = [v * 1.5 for v in sample_embedding]
        r1 = await compute_similarity(sample_embedding, vec_b)
        r2 = await compute_similarity(vec_b, sample_embedding)
        assert abs(r1 - r2) < 1e-10


# ── Vector Search ─────────────────────────────────────────────────────────────

class TestVectorSearch:
    @pytest.mark.asyncio
    async def test_returns_empty_list_on_error(self, fake_embeddings_collection, sample_embedding):
        """Falls back to empty list if Atlas vector search is unavailable."""
        from app.services.embedding_service import vector_search_similar_resumes

        # Force the collection to raise (simulating no Atlas index)
        bad_collection = MagicMock()
        bad_collection.aggregate.side_effect = Exception("Atlas not configured")

        result = await vector_search_similar_resumes(bad_collection, sample_embedding)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_results_from_aggregation(self, sample_embedding):
        """Returns results from a successful $vectorSearch aggregation."""
        from app.services.embedding_service import vector_search_similar_resumes

        expected = [{"resume_id": "abc123", "score": 0.91}]
        mock_col = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=expected)
        mock_col.aggregate.return_value = mock_cursor

        result = await vector_search_similar_resumes(mock_col, sample_embedding, limit=5)
        assert result == expected
        mock_col.aggregate.assert_called_once()
