"""Collections router."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from uuid import UUID

from app.db.database import get_db
from app.db.models import Collection
from app.api.auth import require_auth

router = APIRouter()


class CollectionCreate(BaseModel):
    name: str
    description: str | None = None


class CollectionResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    created_at: str

    class Config:
        from_attributes = True


class ApiResponse(BaseModel):
    success: bool
    data: list | dict | None = None
    error: str | None = None


@router.get("", response_model=ApiResponse)
async def list_collections(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """List all collections."""
    result = await db.execute(select(Collection))
    collections = result.scalars().all()
    return ApiResponse(
        success=True,
        data=[{"id": str(c.id), "name": c.name, "description": c.description, "created_at": c.created_at.isoformat()} for c in collections]
    )


@router.post("", response_model=ApiResponse)
async def create_collection(
    request: CollectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Create a new collection."""
    collection = Collection(
        name=request.name,
        description=request.description,
        owner_id=current_user.id if current_user else None
    )
    db.add(collection)
    await db.commit()
    await db.refresh(collection)
    return ApiResponse(
        success=True,
        data={"id": str(collection.id), "name": collection.name}
    )


@router.get("/{collection_id}", response_model=ApiResponse)
async def get_collection(
    collection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Get a specific collection."""
    result = await db.execute(select(Collection).where(Collection.id == collection_id))
    collection = result.scalar_one_or_none()
    
    if not collection:
        return ApiResponse(success=False, error="Collection not found")
    
    return ApiResponse(
        success=True,
        data={
            "id": str(collection.id),
            "name": collection.name,
            "description": collection.description,
            "created_at": collection.created_at.isoformat()
        }
    )


@router.delete("/{collection_id}", response_model=ApiResponse)
async def delete_collection(
    collection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Delete a collection."""
    result = await db.execute(select(Collection).where(Collection.id == collection_id))
    collection = result.scalar_one_or_none()
    
    if not collection:
        return ApiResponse(success=False, error="Collection not found")
    
    await db.execute(delete(Collection).where(Collection.id == collection_id))
    await db.commit()
    return ApiResponse(success=True, data={"message": "Collection deleted"})
