"""Integration router (public API for n8n/bots)."""

from fastapi import APIRouter, Depends, HTTPException, Security
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.database import get_db
from app.api.auth import require_auth

router = APIRouter()


class ChatRequest(BaseModel):
    question: str


class ApiResponse(BaseModel):
    success: bool
    data: dict | None = None
    error: str | None = None


@router.post("/chat/{collection_id}", response_model=ApiResponse)
async def integration_chat(
    collection_id: UUID,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """Chat via integration API."""
    return ApiResponse(
        success=True,
        data={
            "answer": f"Respuesta de integracion: {request.question}",
            "sources": []
        }
    )


@router.post("/search/{collection_id}", response_model=ApiResponse)
async def integration_search(
    collection_id: UUID,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """Search via integration API."""
    return ApiResponse(
        success=True,
        data={"results": []}
    )


@router.get("/collections", response_model=ApiResponse)
async def list_collections(
    db: AsyncSession = Depends(get_db)
):
    """List collections for integration."""
    return ApiResponse(
        success=True,
        data=[{"id": "placeholder", "name": "Placeholder"}]
    )


@router.get("/summary/{collection_id}", response_model=ApiResponse)
async def get_summary(
    collection_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get summary for integration."""
    return ApiResponse(
        success=True,
        data={"summary": "Resumen de integracion"}
    )


@router.post("/market-compare/{collection_id}", response_model=ApiResponse)
async def market_compare(
    collection_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Market compare for integration."""
    return ApiResponse(
        success=True,
        data={"comparison": "Comparativa"}
    )


@router.post("/campaign/generate", response_model=ApiResponse)
async def generate_campaign(
    db: AsyncSession = Depends(get_db)
):
    """Generate campaign."""
    return ApiResponse(
        success=True,
        data={"brief": "Brief de campana generado"}
    )


@router.post("/campaign/content", response_model=ApiResponse)
async def generate_campaign_content(
    db: AsyncSession = Depends(get_db)
):
    """Generate campaign content."""
    return ApiResponse(
        success=True,
        data={"content": "Contenido de campana generado"}
    )
