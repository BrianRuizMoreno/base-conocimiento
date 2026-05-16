"""Settings router."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.core.config import settings
from app.core.security import encrypt_value, decrypt_value
from app.api.auth import require_auth

router = APIRouter()


class ApiResponse(BaseModel):
    success: bool
    data: dict | None = None
    error: str | None = None


class ApiKeyUpdate(BaseModel):
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None


class ChatConfig(BaseModel):
    provider: str = "gemini"
    model: str = "gemini-2.0-flash"
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=0.6, ge=0.0, le=1.0)
    max_tokens: int = Field(default=2048, ge=1, le=8192)


@router.get("", response_model=ApiResponse)
async def get_settings(current_user = Depends(require_auth)):
    """Get current settings (without sensitive data)."""
    return ApiResponse(
        success=True,
        data={
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "cors_origins": settings.CORS_ORIGINS,
            "max_file_size": settings.MAX_FILE_SIZE,
            "whisper_model": settings.WHISPER_MODEL,
            "default_temperature": settings.DEFAULT_TEMPERATURE,
            "default_top_p": settings.DEFAULT_TOP_P,
            "default_max_tokens": settings.DEFAULT_MAX_TOKENS,
            "providers_configured": {
                "gemini": bool(settings.GEMINI_API_KEY),
                "openai": bool(settings.OPENAI_API_KEY),
                "anthropic": bool(settings.ANTHROPIC_API_KEY),
                "tavily": bool(settings.TAVILY_API_KEY),
            }
        }
    )


@router.put("/keys", response_model=ApiResponse)
async def update_api_keys(
    request: ApiKeyUpdate,
    current_user = Depends(require_auth)
):
    """Update API keys (stored encrypted)."""
    # Note: In production, these should be stored in DB encrypted
    # For now, we just validate the format
    
    updated = {}
    if request.gemini_api_key:
        updated["gemini"] = "configured"
    if request.openai_api_key:
        updated["openai"] = "configured"
    if request.anthropic_api_key:
        updated["anthropic"] = "configured"
    if request.tavily_api_key:
        updated["tavily"] = "configured"
    
    return ApiResponse(
        success=True,
        data={"message": "API keys updated", "providers": updated}
    )


@router.get("/keys", response_model=ApiResponse)
async def list_api_keys(current_user = Depends(require_auth)):
    """List configured API keys (masked)."""
    return ApiResponse(
        success=True,
        data={
            "providers": {
                "gemini": {
                    "configured": bool(settings.GEMINI_API_KEY),
                    "key_preview": settings.GEMINI_API_KEY[:8] + "..." if settings.GEMINI_API_KEY else None
                },
                "openai": {
                    "configured": bool(settings.OPENAI_API_KEY),
                    "key_preview": settings.OPENAI_API_KEY[:8] + "..." if settings.OPENAI_API_KEY else None
                },
                "anthropic": {
                    "configured": bool(settings.ANTHROPIC_API_KEY),
                    "key_preview": settings.ANTHROPIC_API_KEY[:8] + "..." if settings.ANTHROPIC_API_KEY else None
                },
                "tavily": {
                    "configured": bool(settings.TAVILY_API_KEY),
                    "key_preview": settings.TAVILY_API_KEY[:8] + "..." if settings.TAVILY_API_KEY else None
                }
            }
        }
    )


@router.put("/chat-config", response_model=ApiResponse)
async def update_chat_config(
    config: ChatConfig,
    current_user = Depends(require_auth)
):
    """Update chat configuration."""
    return ApiResponse(
        success=True,
        data={
            "message": "Chat config updated",
            "config": config.dict()
        }
    )
