"""
Unit tests for pdf_parser.py — text extraction from PDF and DOCX.
All tests use in-memory file bytes, no disk access needed.
"""
from __future__ import annotations
import io
import pytest
from unittest.mock import MagicMock, patch


# ── PDF Extraction ────────────────────────────────────────────────────────────

class TestExtractTextFromPdf:
    def test_extracts_text_from_pdf(self, sample_resume_text):
        """PDF extraction returns non-empty string with expected content."""
        # Create a mock pdfplumber page that returns our sample text
        mock_page = MagicMock()
        mock_page.extract_text.return_value = sample_resume_text

        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page]

        with patch("pdfplumber.open", return_value=mock_pdf):
            from app.services.pdf_parser import extract_text_from_pdf
            result = extract_text_from_pdf(b"fake-pdf-bytes")

        assert isinstance(result, str)
        assert len(result) > 100
        assert "Jane Smith" in result

    def test_handles_empty_pdf(self):
        """Empty pages return empty string."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = None

        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page]

        with patch("pdfplumber.open", return_value=mock_pdf):
            from app.services.pdf_parser import extract_text_from_pdf
            result = extract_text_from_pdf(b"empty-pdf")

        assert result == ""

    def test_multi_page_pdf_joins_pages(self, sample_resume_text):
        """Multiple pages are joined with double newlines."""
        page1 = MagicMock()
        page1.extract_text.return_value = "Page one text"
        page2 = MagicMock()
        page2.extract_text.return_value = "Page two text"

        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [page1, page2]

        with patch("pdfplumber.open", return_value=mock_pdf):
            from app.services.pdf_parser import extract_text_from_pdf
            result = extract_text_from_pdf(b"fake-pdf-bytes")

        assert "Page one text" in result
        assert "Page two text" in result
        assert "\n\n" in result


# ── DOCX Extraction ───────────────────────────────────────────────────────────

class TestExtractTextFromDocx:
    def test_extracts_paragraphs_from_docx(self, sample_resume_text):
        """DOCX extraction returns joined paragraphs."""
        mock_para_1 = MagicMock()
        mock_para_1.text = "Jane Smith"
        mock_para_2 = MagicMock()
        mock_para_2.text = "Senior Software Engineer"
        mock_para_empty = MagicMock()
        mock_para_empty.text = "   "

        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para_1, mock_para_2, mock_para_empty]

        with patch("docx.Document", return_value=mock_doc):
            from app.services.pdf_parser import extract_text_from_docx
            result = extract_text_from_docx(b"fake-docx-bytes")

        assert "Jane Smith" in result
        assert "Senior Software Engineer" in result
        # Empty paragraph should be skipped
        assert result.count("   ") == 0


# ── Dispatch ──────────────────────────────────────────────────────────────────

class TestExtractTextDispatch:
    def test_dispatches_pdf(self):
        """extract_text dispatches .pdf to PDF extractor."""
        with patch("app.services.pdf_parser.extract_text_from_pdf", return_value="pdf text") as mock:
            from app.services.pdf_parser import extract_text
            result = extract_text("resume.pdf", b"bytes")
        mock.assert_called_once_with(b"bytes")
        assert result == "pdf text"

    def test_dispatches_docx(self):
        """extract_text dispatches .docx to DOCX extractor."""
        with patch("app.services.pdf_parser.extract_text_from_docx", return_value="docx text") as mock:
            from app.services.pdf_parser import extract_text
            result = extract_text("resume.docx", b"bytes")
        mock.assert_called_once_with(b"bytes")
        assert result == "docx text"

    def test_dispatches_doc(self):
        """extract_text dispatches .doc to DOCX extractor."""
        with patch("app.services.pdf_parser.extract_text_from_docx", return_value="doc text") as mock:
            from app.services.pdf_parser import extract_text
            result = extract_text("resume.doc", b"bytes")
        mock.assert_called_once_with(b"bytes")

    def test_raises_for_unsupported_format(self):
        """Unsupported format raises ValueError."""
        from app.services.pdf_parser import extract_text
        with pytest.raises(ValueError, match="Unsupported file format"):
            extract_text("resume.txt", b"bytes")

    def test_raises_for_png(self):
        """Image file raises ValueError."""
        from app.services.pdf_parser import extract_text
        with pytest.raises(ValueError, match="Unsupported file format"):
            extract_text("photo.png", b"bytes")


# ── Validation ────────────────────────────────────────────────────────────────

class TestValidateResumeText:
    def test_valid_text_passes(self, sample_resume_text):
        from app.services.pdf_parser import validate_resume_text
        validate_resume_text(sample_resume_text)  # should not raise

    def test_empty_text_raises(self):
        from app.services.pdf_parser import validate_resume_text
        with pytest.raises(ValueError, match="empty or unreadable"):
            validate_resume_text("")

    def test_short_text_raises(self):
        from app.services.pdf_parser import validate_resume_text
        with pytest.raises(ValueError, match="empty or unreadable"):
            validate_resume_text("Hi")

    def test_whitespace_only_raises(self):
        from app.services.pdf_parser import validate_resume_text
        with pytest.raises(ValueError, match="empty or unreadable"):
            validate_resume_text("   \n\t   ")
