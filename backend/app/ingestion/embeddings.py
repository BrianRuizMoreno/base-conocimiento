"""Embedding generation using provider factory or fallback to env keys."""

import logging
import httpx
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.providers import ProviderFactory

logger = logging.getLogger(__name__)

GEMINI_EMBEDDING_URL = "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent"


async def get_embedding(text: str, db: Optional[AsyncSession] = None) -> list[float]:
    """Get embedding for a single text.

    If `db` is provided, uses ProviderFactory with key management.
    Otherwise falls back to GEMINI_API_KEY env var.
    """
    if db:
        factory = ProviderFactory(db)
        result = await factory.embed(
            [text],
            provider="gemini",
        )
        return result[0]

    # Fallback to env key
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not configured")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GEMINI_EMBEDDING_URL}?key={settings.GEMINI_API_KEY}",
            json={
                "model": "models/text-embedding-004",
                "content": {
                    "parts": [{"text": text[:8000]}]  # Truncate to avoid limits
                }
            },
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()
        return data["embedding"]["values"]


async def get_embeddings(texts: list[str], db: Optional[AsyncSession] = None) -> list[list[float]]:
    """Get embeddings for multiple texts.

    If `db` is provided, uses ProviderFactory with key management.
    Otherwise falls back to GEMINI_API_KEY env var.
    """
    if db:
        factory = ProviderFactory(db)
        result = await factory.embed(
            texts,
            provider="gemini",
        )
        return result

    # Fallback to env key (sequential with rate limit handling)
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not configured")

    results = []
    for text in texts:
        try:
            emb = await get_embedding(text)
            results.append(emb)
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            # Return zero vector as fallback
            results.append([0.0] * 768)
    return results
