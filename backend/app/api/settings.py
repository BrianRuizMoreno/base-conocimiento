"""Settings router with DB persistence for API keys and chat configuration."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.config import settings
from app.core.security import encrypt_value, decrypt_value, hash_api_key
from app.api.auth import require_auth
from app.db.database import get_db
from app.db.models import ProviderKey, ChatSettings, User

logger = logging.getLogger(__name__)
router = APIRouter()


class ApiResponse(BaseModel):
    success: bool
    data: dict | None = None
    error: str | None = None


class ApiKeyCreate(BaseModel):
    provider: str = Field(..., pattern="^(gemini|openai|anthropic|tavily)$")
    api_key: str = Field(..., min_length=10)
    label: Optional[str] = None
    priority: int = Field(default=0, ge=0, le=100)


class ApiKeyDelete(BaseModel):
    key_id: str


class ChatConfigUpdate(BaseModel):
    provider: str = Field(default="gemini", pattern="^(gemini|openai|anthropic)$")
    model: str = Field(default="gemini-2.0-flash")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=0.6, ge=0.0, le=1.0)
    max_tokens: int = Field(default=2048, ge=1, le=8192)


async def _get_global_chat_settings(db: AsyncSession) -> ChatSettings:
    """Get or create global chat settings (user_id=None)."""
    result = await db.execute(
        select(ChatSettings).where(ChatSettings.user_id.is_(None))
    )
    chat_settings = result.scalar_one_or_none()
    if not chat_settings:
        chat_settings = ChatSettings(
            user_id=None,
            provider="gemini",
            model="gemini-2.0-flash",
            temperature=0.2,
            top_p=0.6,
            max_tokens=2048,
        )
        db.add(chat_settings)
        await db.commit()
        await db.refresh(chat_settings)
    return chat_settings


@router.get("", response_model=ApiResponse)
async def get_settings(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get current settings (without sensitive data)."""
    chat_settings = await _get_global_chat_settings(db)

    # Count active provider keys
    provider_counts = {}
    for provider in ["gemini", "openai", "anthropic", "tavily"]:
        result = await db.execute(
            select(ProviderKey).where(
                ProviderKey.provider == provider,
                ProviderKey.is_active == True,
            )
        )
        provider_counts[provider] = len(result.scalars().all())

    return ApiResponse(
        success=True,
        data={
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "cors_origins": settings.CORS_ORIGINS,
            "max_file_size": settings.MAX_FILE_SIZE,
            "whisper_model": settings.WHISPER_MODEL,
            "chat_config": {
                "provider": chat_settings.provider,
                "model": chat_settings.model,
                "temperature": chat_settings.temperature,
                "top_p": chat_settings.top_p,
                "max_tokens": chat_settings.max_tokens,
            },
            "providers_configured": {
                "gemini": provider_counts["gemini"] > 0,
                "openai": provider_counts["openai"] > 0,
                "anthropic": provider_counts["anthropic"] > 0,
                "tavily": provider_counts["tavily"] > 0,
            }
        }
    )


@router.post("/keys", response_model=ApiResponse)
async def add_api_key(
    request: ApiKeyCreate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Add a new API key (stored encrypted in DB)."""
    try:
        encrypted = encrypt_value(request.api_key)
        key_hash = hash_api_key(request.api_key)

        provider_key = ProviderKey(
            provider=request.provider,
            api_key_encrypted=encrypted,
            api_key_hash=key_hash,
            label=request.label or f"{request.provider.upper()} Key",
            priority=request.priority,
            is_active=True,
            failure_count=0,
        )
        db.add(provider_key)
        await db.commit()
        await db.refresh(provider_key)

        return ApiResponse(
            success=True,
            data={
                "message": f"API key for {request.provider} added successfully",
                "key_id": str(provider_key.id),
                "provider": request.provider,
                "label": provider_key.label,
            }
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to add API key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add API key: {str(e)}")


@router.delete("/keys/{key_id}", response_model=ApiResponse)
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Delete an API key."""
    try:
        from uuid import UUID
        try:
            key_uuid = UUID(key_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="ID de key invalido")
        
        result = await db.execute(
            delete(ProviderKey).where(ProviderKey.id == key_uuid)
        )
        await db.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Key not found")

        return ApiResponse(
            success=True,
            data={"message": "API key deleted successfully"}
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete API key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete API key: {str(e)}")


@router.get("/keys", response_model=ApiResponse)
async def list_api_keys(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List configured API keys (masked, from DB)."""
    result = await db.execute(select(ProviderKey).order_by(ProviderKey.provider, ProviderKey.priority))
    keys = result.scalars().all()

    providers = {"gemini": [], "openai": [], "anthropic": [], "tavily": []}
    for key in keys:
        providers[key.provider].append({
            "id": str(key.id),
            "label": key.label,
            "is_active": key.is_active,
            "priority": key.priority,
            "failure_count": key.failure_count,
            "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
            "created_at": key.created_at.isoformat() if key.created_at else None,
        })

    return ApiResponse(
        success=True,
        data={"providers": providers}
    )


@router.put("/chat-config", response_model=ApiResponse)
async def update_chat_config(
    config: ChatConfigUpdate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update chat configuration (persisted in DB)."""
    try:
        chat_settings = await _get_global_chat_settings(db)

        chat_settings.provider = config.provider
        chat_settings.model = config.model
        chat_settings.temperature = config.temperature
        chat_settings.top_p = config.top_p
        chat_settings.max_tokens = config.max_tokens

        await db.commit()
        await db.refresh(chat_settings)

        return ApiResponse(
            success=True,
            data={
                "message": "Chat config updated",
                "config": {
                    "provider": chat_settings.provider,
                    "model": chat_settings.model,
                    "temperature": chat_settings.temperature,
                    "top_p": chat_settings.top_p,
                    "max_tokens": chat_settings.max_tokens,
                }
            }
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update chat config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update chat config: {str(e)}")


@router.post("/keys/{key_id}/toggle", response_model=ApiResponse)
async def toggle_api_key(
    key_id: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Toggle active/inactive an API key."""
    try:
        from uuid import UUID
        try:
            key_uuid = UUID(key_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="ID de key invalido")
        
        result = await db.execute(
            select(ProviderKey).where(ProviderKey.id == key_uuid)
        )
        key = result.scalar_one_or_none()

        if not key:
            raise HTTPException(status_code=404, detail="Key not found")

        key.is_active = not key.is_active
        key.failure_count = 0  # Reset failure count on toggle
        await db.commit()

        return ApiResponse(
            success=True,
            data={
                "message": f"Key {'activated' if key.is_active else 'deactivated'}",
                "is_active": key.is_active,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to toggle API key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to toggle API key: {str(e)}")
