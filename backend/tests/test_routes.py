"""
End-to-end route tests using FastAPI TestClient.
All external services (MongoDB, Groq, fastembed) are mocked via conftest fixtures.
No real API keys or database connections needed.
"""
from __future__ import annotations
import io
import pytest


# ── Health Check ──────────────────────────────────────────────────────────────

class TestHealthCheck:
    def test_health_returns_ok(self, test_client):
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "Resume Review Agent" in data["service"]

    def test_health_returns_version(self, test_client):
        response = test_client.get("/")
        assert "version" in response.json()


# ── Upload Route ──────────────────────────────────────────────────────────────

class TestUploadRoute:
    def _make_pdf_upload(self, text: str, filename="resume.pdf"):
        """Create a minimal PDF-like file for upload."""
        # We mock pdfplumber so the content doesn't matter
        return io.BytesIO(b"mock-pdf-content"), filename

    def test_upload_pdf_success(self, test_client, sample_resume_text):
        from unittest.mock import patch
        with patch("app.routes.upload.extract_text", return_value=sample_resume_text):
            with patch("app.routes.upload.validate_resume_text"):
                response = test_client.post(
                    "/upload",
                    files={"file": ("resume.pdf", b"mock-pdf-content", "application/pdf")},
                    data={"user_id": "test_user"},
                )

        assert response.status_code == 200
        data = response.json()
        assert "resume_id" in data
        assert data["filename"] == "resume.pdf"
        assert data["char_count"] > 0

    def test_upload_docx_success(self, test_client, sample_resume_text):
        from unittest.mock import patch
        with patch("app.routes.upload.extract_text", return_value=sample_resume_text):
            with patch("app.routes.upload.validate_resume_text"):
                response = test_client.post(
                    "/upload",
                    files={"file": ("resume.docx", b"mock-docx-content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
                    data={"user_id": "test_user"},
                )

        assert response.status_code == 200
        assert "resume_id" in response.json()

    def test_upload_returns_message(self, test_client, sample_resume_text):
        from unittest.mock import patch
        with patch("app.routes.upload.extract_text", return_value=sample_resume_text):
            with patch("app.routes.upload.validate_resume_text"):
                response = test_client.post(
                    "/upload",
                    files={"file": ("resume.pdf", b"mock-pdf-content", "application/pdf")},
                )

        data = response.json()
        assert "message" in data
        assert "successfully" in data["message"].lower()

    def test_upload_too_large_returns_413(self, test_client):
        from unittest.mock import patch
        # Create a file larger than 10MB
        big_content = b"x" * (11 * 1024 * 1024)
        response = test_client.post(
            "/upload",
            files={"file": ("resume.pdf", big_content, "application/pdf")},
        )
        assert response.status_code == 413

    def test_upload_unsupported_format_returns_422(self, test_client):
        from unittest.mock import patch
        with patch("app.routes.upload.extract_text", side_effect=ValueError("Unsupported file format '.txt'")):
            response = test_client.post(
                "/upload",
                files={"file": ("resume.txt", b"hello world", "text/plain")},
            )
        assert response.status_code == 422

    def test_upload_empty_file_returns_422(self, test_client):
        from unittest.mock import patch
        with patch("app.routes.upload.extract_text", return_value=""):
            with patch("app.routes.upload.validate_resume_text",
                       side_effect=ValueError("empty or unreadable")):
                response = test_client.post(
                    "/upload",
                    files={"file": ("resume.pdf", b"", "application/pdf")},
                )
        assert response.status_code == 422

    def test_upload_without_file_returns_422(self, test_client):
        response = test_client.post("/upload", data={"user_id": "test"})
        assert response.status_code == 422


# ── Review Route ──────────────────────────────────────────────────────────────

class TestReviewRoute:
    VALID_RESUME_ID = "507f1f77bcf86cd799439011"

    def test_review_returns_200(self, test_client):
        response = test_client.post(
            "/review",
            json={"resume_id": self.VALID_RESUME_ID, "user_id": "test_user"},
        )
        assert response.status_code == 200

    def test_review_response_has_required_fields(self, test_client):
        response = test_client.post(
            "/review",
            json={"resume_id": self.VALID_RESUME_ID},
        )
        data = response.json()
        assert "review_id" in data
        assert "resume_id" in data
        assert "result" in data
        assert "created_at" in data

    def test_review_result_has_score(self, test_client):
        response = test_client.post(
            "/review",
            json={"resume_id": self.VALID_RESUME_ID},
        )
        result = response.json()["result"]
        assert "overall_score" in result
        assert 0 <= result["overall_score"] <= 100

    def test_review_result_has_ats_compatibility(self, test_client):
        response = test_client.post(
            "/review",
            json={"resume_id": self.VALID_RESUME_ID},
        )
        result = response.json()["result"]
        assert result["ats_compatibility"] in ("High", "Medium", "Low")

    def test_review_result_has_lists(self, test_client):
        response = test_client.post(
            "/review",
            json={"resume_id": self.VALID_RESUME_ID},
        )
        result = response.json()["result"]
        assert isinstance(result["strengths"], list)
        assert isinstance(result["weaknesses"], list)
        assert isinstance(result["missing_keywords"], list)
        assert isinstance(result["suggested_rewrites"], list)

    def test_review_invalid_id_returns_422(self, test_client):
        response = test_client.post(
            "/review",
            json={"resume_id": "not-a-valid-id"},
        )
        assert response.status_code == 422

    def test_review_missing_resume_id_returns_422(self, test_client):
        response = test_client.post("/review", json={})
        assert response.status_code == 422


# ── Match Route ───────────────────────────────────────────────────────────────

class TestMatchRoute:
    VALID_RESUME_ID = "507f1f77bcf86cd799439011"

    def test_match_returns_200(self, test_client, sample_jd):
        response = test_client.post(
            "/match",
            json={"resume_id": self.VALID_RESUME_ID, "job_description": sample_jd},
        )
        assert response.status_code == 200

    def test_match_response_fields(self, test_client, sample_jd):
        response = test_client.post(
            "/match",
            json={"resume_id": self.VALID_RESUME_ID, "job_description": sample_jd},
        )
        data = response.json()
        assert "match_id" in data
        assert "resume_id" in data
        assert "similarity_score" in data
        assert "match_percentage" in data
        assert "explanation" in data
        assert "matched_keywords" in data
        assert "missing_keywords" in data

    def test_match_percentage_in_valid_range(self, test_client, sample_jd):
        response = test_client.post(
            "/match",
            json={"resume_id": self.VALID_RESUME_ID, "job_description": sample_jd},
        )
        pct = response.json()["match_percentage"]
        assert 0.0 <= pct <= 100.0

    def test_match_similarity_in_valid_range(self, test_client, sample_jd):
        response = test_client.post(
            "/match",
            json={"resume_id": self.VALID_RESUME_ID, "job_description": sample_jd},
        )
        score = response.json()["similarity_score"]
        assert 0.0 <= score <= 1.0

    def test_match_invalid_resume_id(self, test_client):
        response = test_client.post(
            "/match",
            json={"resume_id": "bad-id", "job_description": "some JD"},
        )
        assert response.status_code == 422

    def test_match_missing_jd_returns_422(self, test_client):
        response = test_client.post(
            "/match",
            json={"resume_id": self.VALID_RESUME_ID},
        )
        assert response.status_code == 422


# ── History Routes ────────────────────────────────────────────────────────────

class TestHistoryRoutes:
    VALID_REVIEW_ID = "507f1f77bcf86cd799439022"

    def test_get_review_by_id_returns_200(self, test_client):
        response = test_client.get(f"/reviews/{self.VALID_REVIEW_ID}")
        assert response.status_code == 200

    def test_get_review_by_id_has_fields(self, test_client):
        response = test_client.get(f"/reviews/{self.VALID_REVIEW_ID}")
        data = response.json()
        assert "review_id" in data
        assert "result" in data

    def test_get_review_invalid_id_returns_422(self, test_client):
        response = test_client.get("/reviews/not-valid-id")
        assert response.status_code == 422

    def test_get_user_history_returns_200(self, test_client):
        response = test_client.get("/reviews/history/test_user")
        assert response.status_code == 200

    def test_get_user_history_has_fields(self, test_client):
        response = test_client.get("/reviews/history/test_user")
        data = response.json()
        assert "user_id" in data
        assert "reviews" in data
        assert isinstance(data["reviews"], list)
