"""Chat router with DB-persisted settings and conversation history."""

import logging
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from uuid import UUID

from app.db.database import get_db
from app.db.models import ChatSettings, ProviderKey, Conversation, Message
from app.api.auth import require_auth, verify_collection_access
from app.rag.engine import chat_with_collection
from app.core.providers import ProviderFactory
from app.core.limiter import limiter

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    question: str
    provider: str | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)
    conversation_id: UUID | None = None
    web_search: bool = False
    use_graph: bool = False


class ApiResponse(BaseModel):
    success: bool
    data: dict | None = None
    error: str | None = None


async def _get_global_chat_settings(db: AsyncSession) -> ChatSettings:
    """Get or create global chat settings."""
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


async def _load_conversation_history(db: AsyncSession, conversation_id: UUID, limit: int = 6):
    """Load recent messages from a conversation."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(desc(Message.created_at))
        .limit(limit)
    )
    messages = result.scalars().all()
    # Return in chronological order
    return list(reversed(messages))


async def _generate_conversation_title(db: AsyncSession, question: str, provider: str, model: str) -> str:
    """Generate a short title for a conversation based on the first question."""
    try:
        factory = ProviderFactory(db)
        prompt = f"""Genera un titulo corto y descriptivo (maximo 5 palabras) para una conversacion que empieza con esta pregunta. Responde SOLO con el titulo, sin comillas ni explicaciones.

Pregunta: {question}
"""
        result = await factory.generate(
            prompt=prompt,
            temperature=0.3,
            top_p=0.8,
            max_tokens=50,
            provider=provider,
            model=model,
        )
        title = result.get("answer", "").strip().strip('"').strip("'")
        # Limit length
        if len(title) > 255:
            title = title[:255]
        return title or "Nueva conversacion"
    except Exception as e:
        logger.warning(f"Failed to generate conversation title: {e}")
        return "Nueva conversacion"


@router.post("/collections/{collection_id}/chat", response_model=ApiResponse)
@limiter.limit("20/minute")
async def chat(
    collection_id: UUID,
    request: ChatRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Chat with a collection using RAG with DB-persisted settings and optional conversation history."""
    try:
        # Verify collection access
        await verify_collection_access(db, collection_id, current_user)
        
        # Load global chat settings from DB
        chat_settings = await _get_global_chat_settings(db)

        # Override with request params if provided
        provider = request.provider or chat_settings.provider
        model = request.model or chat_settings.model
        temperature = request.temperature if request.temperature is not None else chat_settings.temperature
        top_p = request.top_p if request.top_p is not None else chat_settings.top_p
        max_tokens = request.max_tokens if request.max_tokens is not None else chat_settings.max_tokens

        # Check that at least one key exists for the chosen provider
        result = await db.execute(
            select(ProviderKey).where(
                ProviderKey.provider == provider,
                ProviderKey.is_active == True,
            )
        )
        keys = result.scalars().all()

        if not keys:
            return ApiResponse(
                success=False,
                error=f"No hay API keys activas para el proveedor '{provider}'. Ve a Admin > Configuracion para agregarlas."
            )

        # Handle conversation
        conversation = None
        history = []
        if request.conversation_id:
            conv_result = await db.execute(
                select(Conversation).where(
                    Conversation.id == request.conversation_id,
                    Conversation.collection_id == collection_id,
                )
            )
            conversation = conv_result.scalar_one_or_none()
            if conversation:
                history = await _load_conversation_history(db, conversation.id)
        
        # Build history context for the prompt
        history_context = []
        for msg in history:
            history_context.append({
                "role": msg.role,
                "content": msg.content,
            })

        result = await chat_with_collection(
            db=db,
            collection_id=collection_id,
            question=request.question,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            model=model,
            provider=provider,
            user_id=current_user.id,
            history=history_context,
            web_search=request.web_search,
            use_graph=request.use_graph,
        )

        # Persist messages if conversation exists
        if conversation:
            # Save user message
            user_msg = Message(
                conversation_id=conversation.id,
                role="user",
                content=request.question,
            )
            db.add(user_msg)

            # Save assistant message
            assistant_msg = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=result.get("answer", ""),
                sources=result.get("sources"),
                related_media=result.get("related_media"),
                model=result.get("model"),
                tokens_used=result.get("tokens_used"),
            )
            db.add(assistant_msg)

            # Update conversation updated_at
            from datetime import datetime
            conversation.updated_at = datetime.utcnow()

            # Generate title automatically if this is the first exchange and no title
            if not conversation.title and len(history) == 0:
                conversation.title = await _generate_conversation_title(
                    db=db,
                    question=request.question,
                    provider=provider,
                    model=model,
                )

            await db.commit()

            result["conversation_id"] = str(conversation.id)
            result["conversation_title"] = conversation.title

        return ApiResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return ApiResponse(
            success=False,
            error=str(e)
        )
