"""Conversations router with CRUD operations and message history."""

import logging
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from uuid import UUID

from app.db.database import get_db
from app.db.models import Conversation, Message
from app.api.auth import require_auth, verify_collection_access

router = APIRouter()
logger = logging.getLogger(__name__)


class ApiResponse(BaseModel):
    success: bool
    data: dict | list | None = None
    error: str | None = None


class CreateConversationRequest(BaseModel):
    collection_id: UUID
    title: str | None = None


class RenameConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: list | None = None
    related_media: list | None = None
    model: str | None = None
    tokens_used: int | None = None
    created_at: str


class ConversationOut(BaseModel):
    id: str
    collection_id: str
    title: str | None = None
    created_at: str
    updated_at: str


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut]


@router.post("/conversations", response_model=ApiResponse)
async def create_conversation(
    request: CreateConversationRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Create a new conversation for a collection."""
    try:
        await verify_collection_access(db, request.collection_id, current_user)
        
        conversation = Conversation(
            collection_id=request.collection_id,
            title=request.title,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

        return ApiResponse(
            success=True,
            data={
                "id": str(conversation.id),
                "collection_id": str(conversation.collection_id),
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
            }
        )
    except Exception as e:
        logger.error(f"Error creating conversation: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/conversations", response_model=ApiResponse)
async def list_conversations(
    collection_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """List conversations, optionally filtered by collection_id."""
    try:
        if collection_id:
            await verify_collection_access(db, collection_id, current_user)
        
        stmt = select(Conversation).order_by(desc(Conversation.updated_at))
        if collection_id:
            stmt = stmt.where(Conversation.collection_id == collection_id)

        result = await db.execute(stmt)
        conversations = result.scalars().all()

        return ApiResponse(
            success=True,
            data=[
                {
                    "id": str(c.id),
                    "collection_id": str(c.collection_id),
                    "title": c.title or "Nueva conversacion",
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                }
                for c in conversations
            ]
        )
    except Exception as e:
        logger.error(f"Error listing conversations: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/conversations/{conversation_id}", response_model=ApiResponse)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Get a conversation with all its messages."""
    try:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            return ApiResponse(success=False, error="Conversacion no encontrada")

        await verify_collection_access(db, conversation.collection_id, current_user)

        messages_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        messages = messages_result.scalars().all()

        return ApiResponse(
            success=True,
            data={
                "id": str(conversation.id),
                "collection_id": str(conversation.collection_id),
                "title": conversation.title or "Nueva conversacion",
                "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
                "messages": [
                    {
                        "id": str(m.id),
                        "role": m.role,
                        "content": m.content,
                        "sources": m.sources,
                        "related_media": m.related_media,
                        "model": m.model,
                        "tokens_used": m.tokens_used,
                        "created_at": m.created_at.isoformat() if m.created_at else None,
                    }
                    for m in messages
                ],
            }
        )
    except Exception as e:
        logger.error(f"Error getting conversation: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.patch("/conversations/{conversation_id}", response_model=ApiResponse)
async def rename_conversation(
    conversation_id: UUID,
    request: RenameConversationRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Rename a conversation."""
    try:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            return ApiResponse(success=False, error="Conversacion no encontrada")

        conversation.title = request.title
        await db.commit()
        await db.refresh(conversation)

        return ApiResponse(
            success=True,
            data={
                "id": str(conversation.id),
                "title": conversation.title,
                "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
            }
        )
    except Exception as e:
        logger.error(f"Error renaming conversation: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.delete("/conversations/{conversation_id}", response_model=ApiResponse)
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Delete a conversation and all its messages."""
    try:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            return ApiResponse(success=False, error="Conversacion no encontrada")

        db.delete(conversation)
        await db.commit()

        return ApiResponse(
            success=True,
            data={"message": "Conversacion eliminada correctamente"}
        )
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))
