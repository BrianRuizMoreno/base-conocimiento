"""Admin router."""

import asyncio
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timedelta

from app.db.database import get_db
from app.db.models import TokenUsage, ExecutionLog, ErrorLog, ServerMetrics, Collection, Document, Chunk, Entity, Sector, IntegrationKey
from app.api.auth import require_auth
from app.core.security import generate_api_key, hash_api_key

router = APIRouter()


class ApiResponse(BaseModel):
    success: bool
    data: dict | None = None
    error: str | None = None


def get_period_dates(period: str):
    """Get start and end dates for a period."""
    now = datetime.utcnow()
    if period == "24h":
        return now - timedelta(hours=24), now
    elif period == "7d":
        return now - timedelta(days=7), now
    elif period == "30d":
        return now - timedelta(days=30), now
    else:  # all
        return datetime(2020, 1, 1), now


@router.get("/metrics", response_model=ApiResponse)
async def get_metrics(
    period: str = "24h",
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Get admin metrics."""
    start_date, end_date = get_period_dates(period)
    
    # Count stats
    collections_count = await db.execute(select(func.count(Collection.id)))
    documents_count = await db.execute(select(func.count(Document.id)))
    chunks_count = await db.execute(select(func.count(Chunk.id)))
    entities_count = await db.execute(select(func.count(Entity.id)))
    
    # Token usage stats
    token_stats = await db.execute(
        select(
            func.coalesce(func.sum(TokenUsage.tokens_in), 0),
            func.coalesce(func.sum(TokenUsage.tokens_out), 0),
            func.coalesce(func.sum(TokenUsage.cost_usd), 0.0)
        ).where(TokenUsage.created_at >= start_date)
    )
    tokens_in, tokens_out, cost = token_stats.first()
    
    # Error count
    error_count = await db.execute(
        select(func.count(ErrorLog.id)).where(ErrorLog.created_at >= start_date)
    )
    
    # Execution count
    execution_count = await db.execute(
        select(func.count(ExecutionLog.id)).where(ExecutionLog.created_at >= start_date)
    )
    
    return ApiResponse(
        success=True,
        data={
            "period": period,
            "stats": {
                "collections": collections_count.scalar(),
                "documents": documents_count.scalar(),
                "chunks": chunks_count.scalar(),
                "entities": entities_count.scalar(),
            },
            "tokens": {
                "total_in": int(tokens_in),
                "total_out": int(tokens_out),
                "cost_usd": round(float(cost), 6)
            },
            "errors": error_count.scalar(),
            "executions": execution_count.scalar(),
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat()
        }
    )


@router.get("/tokens", response_model=ApiResponse)
async def get_token_usage(
    period: str = "24h",
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Get token usage breakdown."""
    start_date, end_date = get_period_dates(period)
    
    result = await db.execute(
        select(TokenUsage).where(
            TokenUsage.created_at >= start_date
        ).order_by(TokenUsage.created_at.desc()).limit(100)
    )
    usages = result.scalars().all()
    
    return ApiResponse(
        success=True,
        data=[{
            "id": str(u.id),
            "provider": u.provider,
            "model": u.model,
            "operation": u.operation,
            "tokens_in": u.tokens_in,
            "tokens_out": u.tokens_out,
            "cost_usd": u.cost_usd,
            "created_at": u.created_at.isoformat()
        } for u in usages]
    )


@router.get("/executions", response_model=ApiResponse)
async def get_executions(
    period: str = "24h",
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Get execution logs."""
    start_date, end_date = get_period_dates(period)
    
    result = await db.execute(
        select(ExecutionLog).where(
            ExecutionLog.created_at >= start_date
        ).order_by(ExecutionLog.created_at.desc()).limit(100)
    )
    logs = result.scalars().all()
    
    return ApiResponse(
        success=True,
        data=[{
            "id": str(l.id),
            "operation": l.operation,
            "status": l.status,
            "duration_ms": l.duration_ms,
            "metadata": l.metadata,
            "created_at": l.created_at.isoformat()
        } for l in logs]
    )


@router.get("/errors", response_model=ApiResponse)
async def get_errors(
    period: str = "24h",
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Get error logs."""
    start_date, end_date = get_period_dates(period)
    
    result = await db.execute(
        select(ErrorLog).where(
            ErrorLog.created_at >= start_date
        ).order_by(ErrorLog.created_at.desc()).limit(100)
    )
    logs = result.scalars().all()
    
    return ApiResponse(
        success=True,
        data=[{
            "id": str(l.id),
            "level": l.level,
            "source": l.source,
            "message": l.message,
            "created_at": l.created_at.isoformat()
        } for l in logs]
    )


class SectorCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None


class SectorUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None


@router.get("/sectors", response_model=ApiResponse)
async def list_sectors(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """List all sectors."""
    result = await db.execute(select(Sector).order_by(Sector.name))
    sectors = result.scalars().all()
    return ApiResponse(
        success=True,
        data=[{
            "id": str(s.id),
            "name": s.name,
            "slug": s.slug,
            "description": s.description,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        } for s in sectors]
    )


@router.post("/sectors", response_model=ApiResponse)
async def create_sector(
    request: SectorCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Create a new sector."""
    # Check if slug already exists
    existing = await db.execute(select(Sector).where(Sector.slug == request.slug))
    if existing.scalar_one_or_none():
        return ApiResponse(success=False, error=f"El slug '{request.slug}' ya existe")
    
    sector = Sector(
        name=request.name,
        slug=request.slug,
        description=request.description,
    )
    db.add(sector)
    await db.commit()
    await db.refresh(sector)
    return ApiResponse(
        success=True,
        data={
            "id": str(sector.id),
            "name": sector.name,
            "slug": sector.slug,
        }
    )


@router.patch("/sectors/{sector_id}", response_model=ApiResponse)
async def update_sector(
    sector_id: UUID,
    request: SectorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Update a sector."""
    result = await db.execute(select(Sector).where(Sector.id == sector_id))
    sector = result.scalar_one_or_none()
    if not sector:
        return ApiResponse(success=False, error="Sector no encontrado")
    
    if request.name is not None:
        sector.name = request.name
    if request.slug is not None:
        sector.slug = request.slug
    if request.description is not None:
        sector.description = request.description
    
    await db.commit()
    await db.refresh(sector)
    return ApiResponse(
        success=True,
        data={
            "id": str(sector.id),
            "name": sector.name,
            "slug": sector.slug,
        }
    )


@router.delete("/sectors/{sector_id}", response_model=ApiResponse)
async def delete_sector(
    sector_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Delete a sector (collections lose their sector_id)."""
    result = await db.execute(select(Sector).where(Sector.id == sector_id))
    sector = result.scalar_one_or_none()
    if not sector:
        return ApiResponse(success=False, error="Sector no encontrado")
    
    await db.execute(select(Sector).where(Sector.id == sector_id))
    await db.commit()
    return ApiResponse(success=True, data={"message": "Sector eliminado"})


@router.get("/sectors/{sector_id}/collections", response_model=ApiResponse)
async def get_sector_collections(
    sector_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Get collections assigned to a sector."""
    result = await db.execute(
        select(Collection).where(Collection.sector_id == sector_id)
    )
    collections = result.scalars().all()
    return ApiResponse(
        success=True,
        data=[{
            "id": str(c.id),
            "name": c.name,
            "description": c.description,
        } for c in collections]
    )


@router.post("/sectors/{sector_id}/collections/{collection_id}", response_model=ApiResponse)
async def assign_collection_to_sector(
    sector_id: UUID,
    collection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Assign a collection to a sector."""
    # Verify sector exists
    sector_result = await db.execute(select(Sector).where(Sector.id == sector_id))
    if not sector_result.scalar_one_or_none():
        return ApiResponse(success=False, error="Sector no encontrado")
    
    # Update collection
    coll_result = await db.execute(select(Collection).where(Collection.id == collection_id))
    collection = coll_result.scalar_one_or_none()
    if not collection:
        return ApiResponse(success=False, error="Coleccion no encontrada")
    
    collection.sector_id = sector_id
    await db.commit()
    return ApiResponse(success=True, data={"message": "Coleccion asignada al sector"})


@router.get("/server", response_model=ApiResponse)
async def get_server_status(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Get server status."""
    import shutil
    import psutil
    
    # Disk usage
    disk = shutil.disk_usage("/")
    disk_used_gb = disk.used / (1024**3)
    disk_total_gb = disk.total / (1024**3)
    
    # RAM
    ram = psutil.virtual_memory()
    ram_used_gb = ram.used / (1024**3)
    ram_total_gb = ram.total / (1024**3)
    
    # CPU (run in thread to avoid blocking event loop)
    cpu_percent = await asyncio.to_thread(psutil.cpu_percent, interval=1)
    
    # DB counts
    files_count = await db.execute(select(func.count(Document.id)))
    chunks_count = await db.execute(select(func.count(Chunk.id)))
    entities_count = await db.execute(select(func.count(Entity.id)))
    
    return ApiResponse(
        success=True,
        data={
            "disk": {
                "used_gb": round(disk_used_gb, 2),
                "total_gb": round(disk_total_gb, 2),
                "percent": round((disk_used_gb / disk_total_gb) * 100, 1)
            },
            "ram": {
                "used_gb": round(ram_used_gb, 2),
                "total_gb": round(ram_total_gb, 2),
                "percent": round((ram_used_gb / ram_total_gb) * 100, 1)
            },
            "cpu": {
                "percent": cpu_percent
            },
            "database": {
                "files": files_count.scalar(),
                "chunks": chunks_count.scalar(),
                "entities": entities_count.scalar()
            }
        }
    )


# ---------------------------------------------------------------------------
# Sector Tokens
# ---------------------------------------------------------------------------

class TokenCreate(BaseModel):
    name: str
    expires_at: datetime | None = None


@router.post("/sectors/{sector_id}/tokens", response_model=ApiResponse)
async def create_sector_token(
    sector_id: UUID,
    request: TokenCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Generate an API token scoped to a sector."""
    # Verify sector exists
    sector_result = await db.execute(select(Sector).where(Sector.id == sector_id))
    if not sector_result.scalar_one_or_none():
        return ApiResponse(success=False, error="Sector no encontrado")
    
    # Generate token
    full_key, prefix = generate_api_key()
    key_hash = hash_api_key(full_key)
    
    token = IntegrationKey(
        key_hash=key_hash,
        key_prefix=prefix,
        name=request.name,
        sector_id=sector_id,
        is_active=True,
        expires_at=request.expires_at,
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    
    return ApiResponse(
        success=True,
        data={
            "token": full_key,  # Show only once
            "name": token.name,
            "sector_id": str(sector_id),
            "expires_at": token.expires_at.isoformat() if token.expires_at else None,
            "message": "Guarda este token ahora. No se mostrara de nuevo.",
        }
    )


@router.get("/tokens", response_model=ApiResponse)
async def list_tokens(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """List all integration tokens."""
    result = await db.execute(
        select(IntegrationKey, Sector)
        .outerjoin(Sector, IntegrationKey.sector_id == Sector.id)
        .order_by(IntegrationKey.created_at.desc())
    )
    rows = result.all()
    
    return ApiResponse(
        success=True,
        data=[{
            "id": str(t.id),
            "name": t.name,
            "prefix": t.key_prefix,
            "sector_id": str(t.sector_id) if t.sector_id else None,
            "sector_name": s.name if s else None,
            "is_active": t.is_active,
            "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None,
            "expires_at": t.expires_at.isoformat() if t.expires_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        } for t, s in rows]
    )


@router.delete("/tokens/{token_id}", response_model=ApiResponse)
async def revoke_token(
    token_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Revoke an integration token."""
    result = await db.execute(select(IntegrationKey).where(IntegrationKey.id == token_id))
    token = result.scalar_one_or_none()
    if not token:
        return ApiResponse(success=False, error="Token no encontrado")
    
    token.is_active = False
    await db.commit()
    return ApiResponse(success=True, data={"message": "Token revocado"})
