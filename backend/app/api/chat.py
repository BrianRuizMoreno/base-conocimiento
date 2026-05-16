"""Chat router."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.database import get_db
from app.api.auth import require_auth

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    temperature: float = 0.2
    top_p: float = 0.6


class ApiResponse(BaseModel):
    success: bool
    data: dict | None = None
    error: str | None = None


@router.post("/collections/{collection_id}/chat", response_model=ApiResponse)
async def chat(
    collection_id: UUID,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Chat with a collection."""
    return ApiResponse(
        success=True,
        data={
            "answer": f"Esta es una respuesta de prueba para: {request.question}",
            "sources": [],
            "related_media": [],
            "model": "gemini-2.0-flash",
            "tokens_used": 150
        }
    )
