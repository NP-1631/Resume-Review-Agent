"""
Shared pytest fixtures for all tests.
All external services (MongoDB, Groq, fastembed) are fully mocked here.
"""
from __future__ import annotations
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Add backend root to path so imports work ──────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Set dummy env vars so services don't crash on import ────────────────────
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")


# ── Sample Data ───────────────────────────────────────────────────────────────

SAMPLE_RESUME_TEXT = (Path(__file__).parent / "sample_resume.txt").read_text(encoding="utf-8")

SAMPLE_JD = """
We are looking for a Senior Python Engineer to join our backend team.
Requirements:
- 5+ years of Python experience
- FastAPI or Django REST Framework
- PostgreSQL, Redis
- Docker, Kubernetes
- CI/CD, GitHub Actions
- Experience with microservices and distributed systems
"""

SAMPLE_REVIEW_RESULT = {
    "overall_score": 82,
    "ats_compatibility": "High",
    "strengths": [
        "Strong quantifiable achievements throughout",
        "Excellent technical skill breadth covering both backend and infrastructure",
    ],
    "weaknesses": [
        "No mention of system design interview preparation",
        "Could add more detail on team leadership approach",
    ],
    "missing_keywords": ["GraphQL", "gRPC", "Prometheus"],
    "suggested_rewrites": [
        {
            "original": "Mentored 4 junior engineers",
            "improved": "Mentored 4 junior engineers through structured 1:1s and code reviews, resulting in 3 promotions within 18 months and a 25% reduction in team bug rate",
        }
    ],
}

SAMPLE_EMBEDDING = [0.01] * 384  # 384-dim dummy embedding


@pytest.fixture
def sample_resume_text() -> str:
    return SAMPLE_RESUME_TEXT


@pytest.fixture
def sample_jd() -> str:
    return SAMPLE_JD


@pytest.fixture
def sample_review_result() -> dict:
    return SAMPLE_REVIEW_RESULT


@pytest.fixture
def sample_embedding() -> list[float]:
    return SAMPLE_EMBEDDING


# ── MongoDB Mock ──────────────────────────────────────────────────────────────

class FakeInsertResult:
    def __init__(self, inserted_id="507f1f77bcf86cd799439011"):
        self.inserted_id = inserted_id


class FakeCollection:
    """Minimal async MongoDB collection mock."""

    def __init__(self, docs=None):
        self._docs = docs or {}

    def insert_one(self, doc):
        result = FakeInsertResult()
        self._docs[str(result.inserted_id)] = doc
        future = AsyncMock(return_value=result)
        return future()

    def find_one(self, query):
        # Return the first stored doc or None
        if self._docs:
            doc = next(iter(self._docs.values()))
            return AsyncMock(return_value=doc)()
        return AsyncMock(return_value=None)()

    def find(self, *args, **kwargs):
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.to_list = AsyncMock(return_value=list(self._docs.values()))
        return cursor

    def aggregate(self, pipeline):
        cursor = MagicMock()
        cursor.to_list = AsyncMock(return_value=[])
        return cursor


@pytest.fixture
def fake_resumes_collection():
    col = FakeCollection()
    # Pre-seed with a resume doc
    from bson import ObjectId
    oid = ObjectId("507f1f77bcf86cd799439011")
    col._docs[str(oid)] = {
        "_id": oid,
        "user_id": "test_user",
        "filename": "resume.pdf",
        "content_type": "application/pdf",
        "raw_text": SAMPLE_RESUME_TEXT,
        "char_count": len(SAMPLE_RESUME_TEXT),
        "uploaded_at": datetime.now(timezone.utc),
    }
    return col


@pytest.fixture
def fake_reviews_collection():
    col = FakeCollection()
    from bson import ObjectId
    oid = ObjectId("507f1f77bcf86cd799439022")
    col._docs[str(oid)] = {
        "_id": oid,
        "resume_id": "507f1f77bcf86cd799439011",
        "user_id": "test_user",
        "result": SAMPLE_REVIEW_RESULT,
        "created_at": datetime.now(timezone.utc),
    }
    return col


@pytest.fixture
def fake_embeddings_collection():
    return FakeCollection()


# ── FastAPI TestClient ────────────────────────────────────────────────────────

@pytest.fixture
def test_client(fake_resumes_collection, fake_reviews_collection, fake_embeddings_collection):
    """
    FastAPI TestClient with all external services mocked.
    MongoDB and Groq are replaced so no real credentials are needed.
    """
    from fastapi.testclient import TestClient

    with (
        patch("app.db.mongo_client.get_resumes_collection", return_value=fake_resumes_collection),
        patch("app.db.mongo_client.get_reviews_collection", return_value=fake_reviews_collection),
        patch("app.db.mongo_client.get_embeddings_collection", return_value=fake_embeddings_collection),
        patch("app.routes.upload.get_resumes_collection", return_value=fake_resumes_collection),
        # Patch at the import site (where the name lives in the route module)
        patch("app.routes.review.get_resumes_collection", return_value=fake_resumes_collection),
        patch("app.routes.review.get_reviews_collection", return_value=fake_reviews_collection),
        patch("app.routes.review.analyze_resume") as mock_review,
        patch("app.routes.match.get_resumes_collection", return_value=fake_resumes_collection),
        patch("app.routes.match.get_embeddings_collection", return_value=fake_embeddings_collection),
        patch("app.routes.match.analyze_jd_match") as mock_jd,
        patch("app.routes.match.generate_embedding", return_value=SAMPLE_EMBEDDING),
        patch("app.routes.match.compute_similarity", new_callable=AsyncMock, return_value=0.82),
        patch("app.routes.history.get_reviews_collection", return_value=fake_reviews_collection),
    ):
        mock_review.return_value = _build_review_result()
        mock_jd.return_value = {
            "explanation": "Strong match — candidate has 7 of 8 required skills.",
            "matched_keywords": ["Python", "Docker", "Kubernetes", "PostgreSQL", "microservices"],
            "missing_keywords": ["gRPC", "GraphQL"],
        }

        from app.main import app
        client = TestClient(app)
        yield client


def _build_review_result():
    from app.models.schemas import ReviewResult, SuggestedRewrite
    return ReviewResult(
        overall_score=SAMPLE_REVIEW_RESULT["overall_score"],
        ats_compatibility=SAMPLE_REVIEW_RESULT["ats_compatibility"],
        strengths=SAMPLE_REVIEW_RESULT["strengths"],
        weaknesses=SAMPLE_REVIEW_RESULT["weaknesses"],
        missing_keywords=SAMPLE_REVIEW_RESULT["missing_keywords"],
        suggested_rewrites=[
            SuggestedRewrite(**r) for r in SAMPLE_REVIEW_RESULT["suggested_rewrites"]
        ],
    )
