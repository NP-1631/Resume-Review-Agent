"""
POST /review — Send resume text to LLM, store and return structured feedback.
"""
from __future__ import annotations
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.db.mongo_client import get_resumes_collection, get_reviews_collection
from app.models.schemas import ReviewRequest, ReviewResponse
from app.services.llm_service import analyze_resume

router = APIRouter(tags=["review"])


@router.post("/review", response_model=ReviewResponse)
async def review_resume(body: ReviewRequest):
    """
    Analyze a previously uploaded resume with the LLM.
    Returns score, strengths, weaknesses, keywords, and rewrite suggestions.
    """
    # Fetch resume text from MongoDB
    resumes = get_resumes_collection()
    try:
        oid = ObjectId(body.resume_id)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid resume_id format.")

    resume_doc = await resumes.find_one({"_id": oid})
    if not resume_doc:
        raise HTTPException(status_code=404, detail="Resume not found.")

    resume_text: str = resume_doc["raw_text"]

    # Call LLM
    try:
        result = analyze_resume(resume_text)
    except KeyError:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY is not configured. Please set it in your .env file.",
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    # Store review
    reviews = get_reviews_collection()
    created_at = datetime.now(timezone.utc)
    review_doc = {
        "resume_id": body.resume_id,
        "user_id": body.user_id or resume_doc.get("user_id", "anonymous"),
        "result": result.model_dump(),
        "created_at": created_at,
    }
    insert_result = await reviews.insert_one(review_doc)
    review_id = str(insert_result.inserted_id)

    return ReviewResponse(
        review_id=review_id,
        resume_id=body.resume_id,
        result=result,
        created_at=created_at,
    )
