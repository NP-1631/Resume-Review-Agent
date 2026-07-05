"""
POST /upload — Accept a PDF or DOCX resume, extract text, store in MongoDB.
"""
from __future__ import annotations
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.db.mongo_client import get_resumes_collection
from app.models.schemas import UploadResponse
from app.services.pdf_parser import extract_text, validate_resume_text

router = APIRouter(tags=["upload"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload", response_model=UploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    user_id: str = Form(default="anonymous"),
):
    """
    Upload a PDF or DOCX resume.
    - Extracts raw text
    - Stores document in MongoDB `resumes` collection
    - Returns resume_id for use in /review and /match
    """
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10 MB.")

    try:
        text = extract_text(file.filename or "resume.pdf", content)
        validate_resume_text(text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    doc = {
        "user_id": user_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "raw_text": text,
        "char_count": len(text),
        "uploaded_at": datetime.now(timezone.utc),
    }

    collection = get_resumes_collection()
    result = await collection.insert_one(doc)
    resume_id = str(result.inserted_id)

    return UploadResponse(
        resume_id=resume_id,
        filename=file.filename or "unknown",
        char_count=len(text),
    )
