"""Collections router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db

router = APIRouter()

# TODO: Implement CRUD endpoints
# GET / - list collections
# POST / - create collection
# GET /{id} - get collection
# DELETE /{id} - delete collection
