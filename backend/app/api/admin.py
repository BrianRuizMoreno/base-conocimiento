"""Admin router."""

import asyncio
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timedelta

from app.db.database import get_db
from app.db.models import TokenUsage, ExecutionLog, ErrorLog, ServerMetrics, Collection, Document, Chunk, Entity
from app.api.auth import require_auth

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
