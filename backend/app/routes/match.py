"""
POST /match — Generate embeddings for resume + JD, compute similarity, return match score.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.db.mongo_client import (
    get_embeddings_collection,
    get_resumes_collection,
)
from app.models.schemas import MatchRequest, MatchResponse
from app.services.embedding_service import (
    compute_similarity,
    generate_embedding,
    vector_search_similar_resumes,
)
from app.services.llm_service import analyze_jd_match

router = APIRouter(tags=["match"])


@router.post("/match", response_model=MatchResponse)
async def match_resume_to_jd(body: MatchRequest):
    """
    Compare a resume against a job description.
    1. Generate embeddings for both texts.
    2. Compute cosine similarity.
    3. Ask LLM to identify matched/missing keywords.
    4. Store embeddings in MongoDB for future vector search.
    """
    # Fetch resume text
    resumes = get_resumes_collection()
    try:
        oid = ObjectId(body.resume_id)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid resume_id format.")

    resume_doc = await resumes.find_one({"_id": oid})
    if not resume_doc:
        raise HTTPException(status_code=404, detail="Resume not found.")

    resume_text: str = resume_doc["raw_text"]

    # Generate embeddings
    try:
        resume_embedding = generate_embedding(resume_text)
        jd_embedding = generate_embedding(body.job_description)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Embedding error: {exc}")

    # Compute cosine similarity
    similarity = await compute_similarity(resume_embedding, jd_embedding)
    match_percentage = round(similarity * 100, 2)

    # LLM keyword analysis
    try:
        llm_data = analyze_jd_match(resume_text, body.job_description)
    except Exception:
        llm_data = {
            "explanation": "LLM analysis unavailable (check GROQ_API_KEY).",
            "matched_keywords": [],
            "missing_keywords": [],
        }

    # Store embeddings
    embeddings_col = get_embeddings_collection()
    match_id = str(uuid.uuid4())
    embedding_doc = {
        "match_id": match_id,
        "resume_id": body.resume_id,
        "user_id": body.user_id or resume_doc.get("user_id", "anonymous"),
        "embedding": resume_embedding,
        "jd_embedding": jd_embedding,
        "similarity_score": similarity,
        "created_at": datetime.now(timezone.utc),
    }
    await embeddings_col.insert_one(embedding_doc)

    return MatchResponse(
        match_id=match_id,
        resume_id=body.resume_id,
        similarity_score=round(similarity, 4),
        match_percentage=match_percentage,
        explanation=llm_data.get("explanation", ""),
        matched_keywords=llm_data.get("matched_keywords", []),
        missing_keywords=llm_data.get("missing_keywords", []),
    )
