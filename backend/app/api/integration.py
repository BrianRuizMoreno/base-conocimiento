"""Integration router (public API for n8n/bots)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db

router = APIRouter()

# TODO: Implement integration endpoints
# POST /chat/{collection_id}
# POST /search/{collection_id}
# GET /collections
# GET /summary/{collection_id}
# POST /market-compare/{collection_id}
# POST /campaign/generate
# POST /campaign/content
