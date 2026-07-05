"""
MongoDB connection via Motor (async PyMongo driver).
Collections: resumes, reviews, embeddings
"""
import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

_client: Optional[AsyncIOMotorClient] = None


def get_client() -> AsyncIOMotorClient:  # type: ignore[return]
    global _client
    if _client is None:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        _client = AsyncIOMotorClient(
            mongo_uri,
            serverSelectionTimeoutMS=30000,  # 30s for Atlas cold-start
            connectTimeoutMS=10000,
        )
    return _client


def get_db():
    db_name = os.getenv("DB_NAME", "resume_review_agent")
    return get_client()[db_name]


def get_resumes_collection():
    return get_db()["resumes"]


def get_reviews_collection():
    return get_db()["reviews"]


def get_embeddings_collection():
    return get_db()["embeddings"]


async def close_client():
    global _client
    if _client:
        _client.close()
        _client = None
