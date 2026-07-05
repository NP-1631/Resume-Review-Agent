"""
Unit tests for llm_service.py — prompt construction and JSON parsing.
The Groq API is fully mocked; no real API calls are made.
"""
from __future__ import annotations
import json
import pytest
from unittest.mock import MagicMock, patch

from tests.conftest import SAMPLE_REVIEW_RESULT


# ── Prompt Construction ────────────────────────────────────────────────────────

class TestBuildReviewPrompt:
    def test_prompt_contains_resume_text(self, sample_resume_text):
        from app.services.llm_service import build_review_prompt
        prompt = build_review_prompt(sample_resume_text)
        assert "Jane Smith" in prompt

    def test_prompt_contains_few_shot_example(self, sample_resume_text):
        from app.services.llm_service import build_review_prompt
        prompt = build_review_prompt(sample_resume_text)
        # The few-shot example is embedded in the prompt
        assert "John Doe" in prompt

    def test_prompt_instructs_json_only(self, sample_resume_text):
        from app.services.llm_service import build_review_prompt
        prompt = build_review_prompt(sample_resume_text)
        assert "JSON" in prompt.upper()

    def test_prompt_is_string(self, sample_resume_text):
        from app.services.llm_service import build_review_prompt
        result = build_review_prompt(sample_resume_text)
        assert isinstance(result, str)
        assert len(result) > 200


# ── JSON Extraction ───────────────────────────────────────────────────────────

class TestExtractJson:
    def test_extracts_clean_json(self):
        from app.services.llm_service import _extract_json
        raw = json.dumps(SAMPLE_REVIEW_RESULT)
        result = _extract_json(raw)
        assert result["overall_score"] == 82

    def test_strips_markdown_fences(self):
        from app.services.llm_service import _extract_json
        raw = f"```json\n{json.dumps(SAMPLE_REVIEW_RESULT)}\n```"
        result = _extract_json(raw)
        assert result["ats_compatibility"] == "High"

    def test_strips_plain_code_fences(self):
        from app.services.llm_service import _extract_json
        raw = f"```\n{json.dumps(SAMPLE_REVIEW_RESULT)}\n```"
        result = _extract_json(raw)
        assert "strengths" in result

    def test_handles_json_with_preamble(self):
        from app.services.llm_service import _extract_json
        raw = f"Here is the analysis:\n{json.dumps(SAMPLE_REVIEW_RESULT)}"
        result = _extract_json(raw)
        assert result["overall_score"] == 82

    def test_raises_on_no_json(self):
        from app.services.llm_service import _extract_json
        with pytest.raises(ValueError, match="No JSON object found"):
            _extract_json("This is just plain text with no JSON.")


# ── analyze_resume (mocked Groq) ─────────────────────────────────────────────

class TestAnalyzeResume:
    def _make_mock_completion(self, content: str):
        mock_choice = MagicMock()
        mock_choice.message.content = content
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        return mock_completion

    def test_returns_review_result(self, sample_resume_text):
        from app.services.llm_service import analyze_resume
        from app.models.schemas import ReviewResult

        mock_completion = self._make_mock_completion(json.dumps(SAMPLE_REVIEW_RESULT))

        with patch("app.services.llm_service.Groq") as MockGroq:
            MockGroq.return_value.chat.completions.create.return_value = mock_completion
            result = analyze_resume(sample_resume_text)

        assert isinstance(result, ReviewResult)
        assert result.overall_score == 82
        assert result.ats_compatibility == "High"
        assert len(result.strengths) >= 1
        assert len(result.weaknesses) >= 1
        assert len(result.missing_keywords) >= 1

    def test_returns_suggested_rewrites(self, sample_resume_text):
        from app.services.llm_service import analyze_resume

        mock_completion = self._make_mock_completion(json.dumps(SAMPLE_REVIEW_RESULT))

        with patch("app.services.llm_service.Groq") as MockGroq:
            MockGroq.return_value.chat.completions.create.return_value = mock_completion
            result = analyze_resume(sample_resume_text)

        assert len(result.suggested_rewrites) >= 1
        assert result.suggested_rewrites[0].original
        assert result.suggested_rewrites[0].improved

    def test_handles_markdown_fenced_response(self, sample_resume_text):
        from app.services.llm_service import analyze_resume

        fenced = f"```json\n{json.dumps(SAMPLE_REVIEW_RESULT)}\n```"
        mock_completion = self._make_mock_completion(fenced)

        with patch("app.services.llm_service.Groq") as MockGroq:
            MockGroq.return_value.chat.completions.create.return_value = mock_completion
            result = analyze_resume(sample_resume_text)

        assert result.overall_score == 82

    def test_uses_low_temperature(self, sample_resume_text):
        """Verify we use low temperature for consistent structured output."""
        from app.services.llm_service import analyze_resume

        mock_completion = self._make_mock_completion(json.dumps(SAMPLE_REVIEW_RESULT))

        with patch("app.services.llm_service.Groq") as MockGroq:
            mock_create = MockGroq.return_value.chat.completions.create
            mock_create.return_value = mock_completion
            analyze_resume(sample_resume_text)
            call_kwargs = mock_create.call_args[1]

        assert call_kwargs["temperature"] <= 0.3


# ── analyze_jd_match (mocked Groq) ───────────────────────────────────────────

class TestAnalyzeJdMatch:
    def test_returns_matched_and_missing_keywords(self, sample_resume_text, sample_jd):
        from app.services.llm_service import analyze_jd_match

        expected = {
            "explanation": "Strong match overall.",
            "matched_keywords": ["Python", "Docker", "Kubernetes"],
            "missing_keywords": ["gRPC"],
        }
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(expected)
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        with patch("app.services.llm_service.Groq") as MockGroq:
            MockGroq.return_value.chat.completions.create.return_value = mock_completion
            result = analyze_jd_match(sample_resume_text, sample_jd)

        assert "matched_keywords" in result
        assert "missing_keywords" in result
        assert "explanation" in result
        assert "Python" in result["matched_keywords"]
