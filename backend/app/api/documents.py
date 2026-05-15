"""Documents router."""

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db

router = APIRouter()

# TODO: Implement endpoints
# POST /collections/{id}/upload - upload file
# GET /collections/{id}/documents - list documents
# DELETE /documents/{id} - delete document
# GET /documents/{id}/progress - upload progress
