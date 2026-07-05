"""
PDF and DOCX text extraction utilities.
"""
from __future__ import annotations
import io
from pathlib import Path


def extract_text_from_pdf(content: bytes) -> str:
    """Extract plain text from PDF bytes using pdfplumber."""
    import pdfplumber

    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text.strip())
    return "\n\n".join(text_parts)


def extract_text_from_docx(content: bytes) -> str:
    """Extract plain text from DOCX bytes using python-docx."""
    from docx import Document

    doc = Document(io.BytesIO(content))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def extract_text(filename: str, content: bytes) -> str:
    """
    Dispatch to the correct parser based on file extension.
    Raises ValueError for unsupported formats.
    """
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(content)
    elif suffix in (".docx", ".doc"):
        return extract_text_from_docx(content)
    else:
        raise ValueError(
            f"Unsupported file format '{suffix}'. Please upload a PDF or DOCX file."
        )


def validate_resume_text(text: str, min_chars: int = 100) -> None:
    """Raise ValueError if the extracted text is too short to be a real resume."""
    if len(text.strip()) < min_chars:
        raise ValueError(
            "The uploaded file appears to be empty or unreadable. "
            "Please upload a valid PDF or DOCX resume."
        )
