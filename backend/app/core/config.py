"""Pydantic settings and configuration."""

import json

from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/rag_system"

    # Security
    ADMIN_PIN_HASH: str = ""
    SECRET_KEY: str = "your-secret-key-change-this"

    # Providers
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # CORS (acepta JSON array o string simple/comma-separated)
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                try:
                    return json.loads(v)
                except json.JSONDecodeError as exc:
                    raise ValueError("CORS_ORIGINS no es un JSON valido") from exc
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    # File Upload
    MAX_FILE_SIZE: int = 500 * 1024 * 1024  # 500MB
    UPLOAD_DIR: str = "/app/data"
    
    # Whisper
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cpu"
    
    # Chat Defaults
    DEFAULT_TEMPERATURE: float = 0.2
    DEFAULT_TOP_P: float = 0.6
    DEFAULT_MAX_TOKENS: int = 2048
    
    # n8n
    N8N_WEBHOOK_URL: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
