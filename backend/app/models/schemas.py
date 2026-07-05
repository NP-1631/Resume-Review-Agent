"""
Pydantic v2 models for all API request/response shapes.
Python 3.9 compatible — uses Optional[X] instead of X | None.
"""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ─── Upload ──────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    resume_id: str
    filename: str
    char_count: int
    message: str = "Resume uploaded and parsed successfully."


# ─── Review ──────────────────────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    resume_id: str
    user_id: Optional[str] = None


class SuggestedRewrite(BaseModel):
    original: str
    improved: str


class ReviewResult(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    ats_compatibility: str          # "High" | "Medium" | "Low"
    strengths: List[str]
    weaknesses: List[str]
    missing_keywords: List[str]
    suggested_rewrites: List[SuggestedRewrite]


class ReviewResponse(BaseModel):
    review_id: str
    resume_id: str
    result: ReviewResult
    created_at: datetime


# ─── Match ───────────────────────────────────────────────────────────────────

class MatchRequest(BaseModel):
    resume_id: str
    job_description: str
    user_id: Optional[str] = None


class MatchResponse(BaseModel):
    match_id: str
    resume_id: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    match_percentage: float = Field(ge=0.0, le=100.0)
    explanation: str
    matched_keywords: List[str]
    missing_keywords: List[str]


# ─── History ─────────────────────────────────────────────────────────────────

class ReviewSummary(BaseModel):
    review_id: str
    resume_id: str
    overall_score: int
    ats_compatibility: str
    created_at: datetime


class HistoryResponse(BaseModel):
    user_id: str
    reviews: List[ReviewSummary]
