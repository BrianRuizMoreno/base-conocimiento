"""Webhook system for n8n notifications."""

import logging
import httpx
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT = 10.0


async def send_webhook(event_type: str, payload: dict) -> bool:
    """Send a webhook event to the configured n8n webhook URL.
    
    Args:
        event_type: Type of event (document_indexed, document_error, chat_low_confidence)
        payload: Event payload data
        
    Returns:
        True if webhook was sent successfully or no URL configured
    """
    webhook_url = settings.N8N_WEBHOOK_URL
    if not webhook_url:
        return True  # Silently skip if not configured
    
    full_payload = {
        "event": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        **payload,
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=full_payload,
                timeout=WEBHOOK_TIMEOUT,
            )
            response.raise_for_status()
            logger.info(f"Webhook {event_type} sent successfully to n8n")
            return True
    except httpx.HTTPStatusError as e:
        logger.warning(f"Webhook {event_type} received error {e.response.status_code}: {e.response.text}")
        return False
    except Exception as e:
        logger.warning(f"Webhook {event_type} failed: {e}")
        return False


async def notify_document_indexed(document_id: str, collection_id: str, filename: str, status: str, metadata: dict | None = None):
    """Notify n8n that a document has been indexed."""
    await send_webhook("document_indexed", {
        "document_id": document_id,
        "collection_id": collection_id,
        "filename": filename,
        "status": status,
        "metadata": metadata or {},
    })


async def notify_document_error(document_id: str, collection_id: str, filename: str, error: str):
    """Notify n8n that a document processing failed."""
    await send_webhook("document_error", {
        "document_id": document_id,
        "collection_id": collection_id,
        "filename": filename,
        "error": error,
    })


async def notify_chat_low_confidence(collection_id: str, question: str, response: str, reason: str):
    """Notify n8n that a chat query had low confidence."""
    await send_webhook("chat_low_confidence", {
        "collection_id": collection_id,
        "question": question,
        "response": response,
        "reason": reason,
    })
