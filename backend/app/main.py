"""
FastAPI application entry point.
Registers all routers, configures CORS, serves the frontend as static files,
and adds health-check endpoint.
"""
from __future__ import annotations
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.routes import upload, review, match, history
from app.db.mongo_client import close_client

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown — close MongoDB connection
    await close_client()


app = FastAPI(
    title="Resume Review Agent",
    description=(
        "AI-powered resume analysis: upload a resume (PDF/DOCX), "
        "get structured LLM feedback, and match against a job description."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────────────────────────
allowed_origins_raw = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:5500,http://localhost:5500,null",
)
allowed_origins = [o.strip() for o in allowed_origins_raw.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(upload.router)
app.include_router(review.router)
app.include_router(match.router)
app.include_router(history.router)


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health_check():
    return {
        "status": "ok",
        "service": "Resume Review Agent API",
        "version": "1.0.0",
    }


# ─── Frontend (static files) ─────────────────────────────────────────────────
# Resolve the frontend directory relative to this file's location:
# backend/app/main.py → ../../frontend
_FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

if _FRONTEND_DIR.exists():
    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(str(_FRONTEND_DIR / "index.html"))

    # Mount at root LAST so API routes take priority.
    # This serves style.css, script.js, etc. at their relative paths.
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR)), name="frontend")

