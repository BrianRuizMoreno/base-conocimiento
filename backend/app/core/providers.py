"""Multi-provider LLM factory with fallback and key rotation."""

import logging
import httpx
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import ProviderKey, TokenUsage, ErrorLog, Pricing
from app.core.config import settings
from app.core.security import decrypt_value

logger = logging.getLogger(__name__)

GEMINI_GENERATE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent"

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_EMBED_URL = "https://api.openai.com/v1/embeddings"

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        top_p: float = 0.6,
        max_tokens: int = 2048,
        model: Optional[str] = None,
    ) -> dict:
        """Generate response. Returns {answer, tokens_in, tokens_out, model}."""
        pass

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings. Returns list of vectors."""
        pass


class GeminiProvider(LLMProvider):
    """Google Gemini provider."""

    MODELS = ["gemini-2.0-flash", "gemini-2.5-flash"]
    EMBED_MODEL = "text-embedding-004"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        top_p: float = 0.6,
        max_tokens: int = 2048,
        model: Optional[str] = None,
    ) -> dict:
        model = model or self.MODELS[0]
        url = GEMINI_GENERATE_URL.format(model=model)

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "topP": top_p,
                "maxOutputTokens": max_tokens,
            },
        }
        if system:
            payload["system_instruction"] = {"parts": [{"text": system}]}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{url}?key={self.api_key}",
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("No response from Gemini")

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            answer = "".join([p.get("text", "") for p in parts])

            usage = data.get("usageMetadata", {})
            tokens_in = usage.get("promptTokenCount", 0)
            tokens_out = usage.get("candidatesTokenCount", 0)

            return {
                "answer": answer,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "model": model,
            }

    async def embed(self, texts: list[str]) -> list[list[float]]:
        results = []
        for text in texts:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{GEMINI_EMBED_URL}?key={self.api_key}",
                    json={
                        "model": f"models/{self.EMBED_MODEL}",
                        "content": {"parts": [{"text": text[:8000]}]},
                    },
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                results.append(data["embedding"]["values"])
        return results


class OpenAIProvider(LLMProvider):
    """OpenAI provider."""

    DEFAULT_MODEL = "gpt-4o-mini"
    EMBED_MODEL = "text-embedding-3-small"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        top_p: float = 0.6,
        max_tokens: int = 2048,
        model: Optional[str] = None,
    ) -> dict:
        model = model or self.DEFAULT_MODEL
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient() as client:
            response = await client.post(
                OPENAI_CHAT_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "top_p": top_p,
                    "max_tokens": max_tokens,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            answer = choice["message"]["content"]
            usage = data.get("usage", {})

            return {
                "answer": answer,
                "tokens_in": usage.get("prompt_tokens", 0),
                "tokens_out": usage.get("completion_tokens", 0),
                "model": model,
            }

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                OPENAI_EMBED_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.EMBED_MODEL, "input": texts},
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    DEFAULT_MODEL = "claude-3-haiku-20240307"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        top_p: float = 0.6,
        max_tokens: int = 2048,
        model: Optional[str] = None,
    ) -> dict:
        model = model or self.DEFAULT_MODEL

        async with httpx.AsyncClient() as client:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                payload["system"] = system

            response = await client.post(
                ANTHROPIC_URL,
                headers=headers,
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            answer = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    answer += block.get("text", "")

            usage = data.get("usage", {})
            return {
                "answer": answer,
                "tokens_in": usage.get("input_tokens", 0),
                "tokens_out": usage.get("output_tokens", 0),
                "model": model,
            }

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("Anthropic does not provide embeddings")


class ProviderFactory:
    """Factory that loads keys from DB and provides fallback logic."""

    PROVIDER_MAP = {
        "gemini": GeminiProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_active_keys(self, provider_name: str) -> list[ProviderKey]:
        """Get active keys for a provider, ordered by priority."""
        result = await self.db.execute(
            select(ProviderKey)
            .where(
                ProviderKey.provider == provider_name,
                ProviderKey.is_active == True,
            )
            .order_by(ProviderKey.priority.asc())
        )
        return result.scalars().all()

    def _create_provider(self, provider_name: str, api_key: str):
        """Instantiate provider class."""
        provider_class = self.PROVIDER_MAP.get(provider_name)
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_name}")
        return provider_class(api_key)

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        top_p: float = 0.6,
        max_tokens: int = 2048,
        provider: str = "gemini",
        model: Optional[str] = None,
        collection_id=None,
        user_id=None,
    ) -> dict:
        """Generate with fallback across multiple keys and providers."""
        # Try primary provider keys first
        keys = await self._get_active_keys(provider)
        last_error = None

        for key in keys:
            try:
                decrypted = decrypt_value(key.api_key_encrypted)
                provider_instance = self._create_provider(provider, decrypted)
                result = await provider_instance.generate(
                    prompt=prompt,
                    system=system,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    model=model,
                )

                # Update last_used_at, reset failure count
                key.last_used_at = datetime.utcnow()
                key.failure_count = 0
                await self.db.commit()

                # Log token usage
                await log_token_usage(
                    self.db,
                    provider=provider,
                    model=result["model"],
                    operation="chat",
                    tokens_in=result["tokens_in"],
                    tokens_out=result["tokens_out"],
                    collection_id=collection_id,
                    user_id=user_id,
                )

                return result
            except Exception as e:
                last_error = e
                logger.warning(f"Key {key.id} failed for {provider}: {e}")
                key.failure_count = (key.failure_count or 0) + 1
                # Deactivate if too many failures
                if key.failure_count >= 5:
                    key.is_active = False
                await self.db.commit()
                continue

        # Fallback to env var if no DB keys
        env_keys = {
            "gemini": settings.GEMINI_API_KEY,
            "openai": settings.OPENAI_API_KEY,
            "anthropic": settings.ANTHROPIC_API_KEY,
        }
        env_key = env_keys.get(provider)
        if env_key:
            try:
                provider_instance = self._create_provider(provider, env_key)
                result = await provider_instance.generate(
                    prompt=prompt,
                    system=system,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    model=model,
                )
                await log_token_usage(
                    self.db,
                    provider=provider,
                    model=result["model"],
                    operation="chat",
                    tokens_in=result["tokens_in"],
                    tokens_out=result["tokens_out"],
                    collection_id=collection_id,
                    user_id=user_id,
                )
                return result
            except Exception as e:
                logger.warning(f"Env key for {provider} failed: {e}")

        # Fallback to other providers
        fallback_order = ["openai", "anthropic"]
        for fallback_provider in fallback_order:
            if fallback_provider == provider:
                continue
            try:
                keys = await self._get_active_keys(fallback_provider)
                if not keys:
                    continue
                key = keys[0]
                decrypted = decrypt_value(key.api_key_encrypted)
                provider_instance = self._create_provider(fallback_provider, decrypted)
                result = await provider_instance.generate(
                    prompt=prompt,
                    system=system,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )

                key.last_used_at = datetime.utcnow()
                key.failure_count = 0
                await self.db.commit()

                await log_token_usage(
                    self.db,
                    provider=fallback_provider,
                    model=result["model"],
                    operation="chat",
                    tokens_in=result["tokens_in"],
                    tokens_out=result["tokens_out"],
                    collection_id=collection_id,
                    user_id=user_id,
                )

                return result
            except Exception as e:
                logger.warning(f"Fallback provider {fallback_provider} failed: {e}")
                continue

        # Log final error
        await log_error(
            self.db,
            level="error",
            source="ProviderFactory.generate",
            message=f"All providers failed. Last error: {last_error}",
            traceback=str(last_error) if last_error else None,
        )
        raise RuntimeError(f"All providers failed. Last error: {last_error}")

    async def embed(
        self,
        texts: list[str],
        provider: str = "gemini",
        collection_id=None,
        user_id=None,
    ) -> list[list[float]]:
        """Generate embeddings with fallback."""
        keys = await self._get_active_keys(provider)
        last_error = None

        for key in keys:
            try:
                decrypted = decrypt_value(key.api_key_encrypted)
                provider_instance = self._create_provider(provider, decrypted)
                result = await provider_instance.embed(texts)

                key.last_used_at = datetime.utcnow()
                key.failure_count = 0
                await self.db.commit()

                await log_token_usage(
                    self.db,
                    provider=provider,
                    model=f"{provider}-embedding",
                    operation="embedding",
                    tokens_in=sum(len(t) // 4 for t in texts),
                    tokens_out=0,
                    collection_id=collection_id,
                    user_id=user_id,
                )

                return result
            except Exception as e:
                last_error = e
                logger.warning(f"Key {key.id} failed for {provider} embed: {e}")
                key.failure_count = (key.failure_count or 0) + 1
                if key.failure_count >= 5:
                    key.is_active = False
                await self.db.commit()
                continue

        # Fallback to env var if no DB keys
        env_keys = {
            "gemini": settings.GEMINI_API_KEY,
            "openai": settings.OPENAI_API_KEY,
        }
        env_key = env_keys.get(provider)
        if env_key:
            try:
                provider_instance = self._create_provider(provider, env_key)
                result = await provider_instance.embed(texts)
                await log_token_usage(
                    self.db,
                    provider=provider,
                    model=f"{provider}-embedding",
                    operation="embedding",
                    tokens_in=sum(len(t) // 4 for t in texts),
                    tokens_out=0,
                    collection_id=collection_id,
                    user_id=user_id,
                )
                return result
            except Exception as e:
                logger.warning(f"Env key for {provider} embed failed: {e}")

        # Fallback to OpenAI for embeddings
        if provider != "openai":
            try:
                keys = await self._get_active_keys("openai")
                if keys:
                    key = keys[0]
                    decrypted = decrypt_value(key.api_key_encrypted)
                    provider_instance = OpenAIProvider(decrypted)
                    result = await provider_instance.embed(texts)

                    key.last_used_at = datetime.utcnow()
                    key.failure_count = 0
                    await self.db.commit()

                    await log_token_usage(
                        self.db,
                        provider="openai",
                        model="text-embedding-3-small",
                        operation="embedding",
                        tokens_in=sum(len(t) // 4 for t in texts),
                        tokens_out=0,
                        collection_id=collection_id,
                        user_id=user_id,
                    )

                    return result
            except Exception as e:
                logger.warning(f"Fallback OpenAI embed failed: {e}")

        await log_error(
            self.db,
            level="error",
            source="ProviderFactory.embed",
            message=f"All embedding providers failed. Last error: {last_error}",
            traceback=str(last_error) if last_error else None,
        )
        raise RuntimeError(f"All embedding providers failed. Last error: {last_error}")


async def log_token_usage(
    db: AsyncSession,
    provider: str,
    model: str,
    operation: str,
    tokens_in: int,
    tokens_out: int,
    collection_id=None,
    user_id=None,
):
    """Log token usage to the database."""
    try:
        # Calculate cost using pricing table
        cost = 0.0
        result = await db.execute(
            select(Pricing)
            .where(Pricing.provider == provider, Pricing.model == model)
        )
        pricing = result.scalar_one_or_none()
        if pricing:
            cost = (
                (tokens_in / 1_000_000) * (pricing.input_price_per_1m or 0)
                + (tokens_out / 1_000_000) * (pricing.output_price_per_1m or 0)
            )

        usage = TokenUsage(
            provider=provider,
            model=model,
            operation=operation,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
            collection_id=collection_id,
            user_id=user_id,
        )
        db.add(usage)
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to log token usage: {e}")
        await db.rollback()


async def log_error(
    db: AsyncSession,
    level: str,
    source: str,
    message: str,
    traceback: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    """Log error to the database."""
    try:
        error = ErrorLog(
            level=level,
            source=source,
            message=message,
            traceback=traceback,
            metadata_=metadata,
        )
        db.add(error)
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to log error: {e}")
        await db.rollback()
