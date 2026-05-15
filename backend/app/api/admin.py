"""Admin router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db

router = APIRouter()

# TODO: Implement admin endpoints
# GET /metrics?period=24h|7d|30d|all
# GET /tokens
# GET /executions
# GET /errors
# GET /server
