"""
GET /reviews/{review_id}      — fetch a single review
GET /reviews/history/{user_id} — fetch all reviews for a user
"""
from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.db.mongo_client import get_reviews_collection
from app.models.schemas import HistoryResponse, ReviewResponse, ReviewSummary

router = APIRouter(tags=["history"])


@router.get("/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: str):
    """Retrieve a single review by its ID."""
    reviews = get_reviews_collection()
    try:
        oid = ObjectId(review_id)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid review_id format.")

    doc = await reviews.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Review not found.")

    return ReviewResponse(
        review_id=str(doc["_id"]),
        resume_id=doc["resume_id"],
        result=doc["result"],
        created_at=doc["created_at"],
    )


@router.get("/reviews/history/{user_id}", response_model=HistoryResponse)
async def get_review_history(user_id: str):
    """Retrieve all reviews for a user, sorted newest first."""
    reviews = get_reviews_collection()
    cursor = reviews.find(
        {"user_id": user_id},
        {"_id": 1, "resume_id": 1, "result.overall_score": 1,
         "result.ats_compatibility": 1, "created_at": 1},
    ).sort("created_at", -1).limit(50)

    docs = await cursor.to_list(length=50)
    summaries = [
        ReviewSummary(
            review_id=str(d["_id"]),
            resume_id=d["resume_id"],
            overall_score=d["result"]["overall_score"],
            ats_compatibility=d["result"]["ats_compatibility"],
            created_at=d["created_at"],
        )
        for d in docs
    ]

    return HistoryResponse(user_id=user_id, reviews=summaries)
