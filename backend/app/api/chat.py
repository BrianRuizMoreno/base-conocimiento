"""Chat router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db

router = APIRouter()

# TODO: Implement chat endpoint
# POST /collections/{id}/chat
