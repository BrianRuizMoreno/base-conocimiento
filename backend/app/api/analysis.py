"""Analysis router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db

router = APIRouter()

# TODO: Implement analysis endpoints
# GET /collections/{id}/summary
# GET /collections/{id}/analysis
# POST /collections/{id}/market-compare
