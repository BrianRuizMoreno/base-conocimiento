"""Documents router."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID
import shutil
import os
from datetime import datetime

from app.db.database import get_db
from app.db.models import Document
from app.api.auth import require_auth
from app.core.config import settings

router = APIRouter()


class ApiResponse(BaseModel):
    success: bool
    data: dict | list | None = None
    error: str | None = None


ALLOWED_TYPES = {
    'application/pdf': 'pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'text/markdown': 'md',
    'application/json': 'json',
    'text/xml': 'xml',
    'image/jpeg': 'image',
    'image/png': 'image',
    'audio/mpeg': 'audio',
    'video/mp4': 'video',
}


@router.post("/collections/{collection_id}/upload", response_model=ApiResponse)
async def upload_document(
    collection_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Upload a document to a collection."""
    try:
        # Validate file type
        file_type = ALLOWED_TYPES.get(file.content_type, 'unknown')
        if file_type == 'unknown':
            return ApiResponse(success=False, error=f"File type not supported: {file.content_type}")
        
        # Save file
        upload_dir = os.path.join(settings.UPLOAD_DIR, str(collection_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Create document record
        document = Document(
            collection_id=collection_id,
            filename=file.filename,
            file_type=file_type,
            file_size=os.path.getsize(file_path),
            storage_path=file_path,
            status="processing"
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        return ApiResponse(
            success=True,
            data={
                "id": str(document.id),
                "filename": document.filename,
                "file_type": document.file_type,
                "status": document.status
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/collections/{collection_id}/documents", response_model=ApiResponse)
async def list_documents(
    collection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """List documents in a collection."""
    result = await db.execute(
        select(Document).where(Document.collection_id == collection_id)
    )
    documents = result.scalars().all()
    
    return ApiResponse(
        success=True,
        data=[{
            "id": str(d.id),
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "status": d.status,
            "created_at": d.created_at.isoformat()
        } for d in documents]
    )


@router.delete("/documents/{document_id}", response_model=ApiResponse)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Delete a document."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    
    if not document:
        return ApiResponse(success=False, error="Document not found")
    
    # Delete file
    if os.path.exists(document.storage_path):
        os.remove(document.storage_path)
    
    # Delete from DB
    await db.execute(delete(Document).where(Document.id == document_id))
    await db.commit()
    
    return ApiResponse(success=True, data={"message": "Document deleted"})


@router.get("/documents/{document_id}/progress", response_model=ApiResponse)
async def document_progress(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Get document processing progress."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    
    if not document:
        return ApiResponse(success=False, error="Document not found")
    
    return ApiResponse(
        success=True,
        data={
            "id": str(document.id),
            "status": document.status,
            "filename": document.filename
        }
    )
