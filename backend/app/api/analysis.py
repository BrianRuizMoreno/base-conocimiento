"""Analysis router."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.database import get_db
from app.api.auth import require_auth

router = APIRouter()


class ApiResponse(BaseModel):
    success: bool
    data: dict | None = None
    error: str | None = None


@router.get("/collections/{collection_id}/summary", response_model=ApiResponse)
async def get_summary(
    collection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Get collection summary."""
    return ApiResponse(
        success=True,
        data={
            "summary": "Resumen automatico de la coleccion (placeholder)",
            "key_entities": [],
            "topics": []
        }
    )


@router.get("/collections/{collection_id}/analysis", response_model=ApiResponse)
async def get_analysis(
    collection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Get predictive analysis."""
    return ApiResponse(
        success=True,
        data={
            "metrics": {},
            "trends": [],
            "predictions": []
        }
    )


@router.post("/collections/{collection_id}/market-compare", response_model=ApiResponse)
async def market_compare(
    collection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Compare with market."""
    return ApiResponse(
        success=True,
        data={
            "comparison": "Comparativa de mercado (placeholder)",
            "sources": []
        }
    )
