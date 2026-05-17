"""Documents router with image serving and enhanced file type support."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID
import shutil
import os
import re
import logging
from datetime import datetime
import asyncio

from app.db.database import get_db
from app.db.models import Document, Chunk
from app.api.auth import require_auth, verify_collection_access
from app.core.config import settings
from app.ingestion.pipeline import process_document

logger = logging.getLogger(__name__)


def run_async_process(document_id: str, file_path: str, file_type: str, collection_id: str):
    """Synchronous wrapper to run async process_document in a new event loop."""
    asyncio.run(process_document(document_id, file_path, file_type, collection_id))


def secure_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal."""
    # Remove any path components
    filename = os.path.basename(filename)
    # Remove any non-alphanumeric, non-dot, non-underscore, non-hyphen characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    # Ensure it doesn't start with a dot (hidden files)
    filename = filename.lstrip('.')
    # If empty after sanitization, use a default
    if not filename:
        filename = "unnamed_file"
    return filename

router = APIRouter()


class ApiResponse(BaseModel):
    success: bool
    data: dict | list | None = None
    error: str | None = None


# Expanded allowed types with specific MIME type mapping
ALLOWED_TYPES = {
    # Documents
    'application/pdf': 'pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'text/markdown': 'md',
    'application/json': 'json',
    'text/xml': 'xml',
    'application/xml': 'xml',
    # Images
    'image/jpeg': 'image',
    'image/jpg': 'image',
    'image/png': 'image',
    'image/webp': 'image',
    'image/gif': 'image',
    'image/bmp': 'image',
    'image/tiff': 'image',
    # Audio
    'audio/mpeg': 'audio',
    'audio/mp3': 'audio',
    'audio/wav': 'audio',
    'audio/x-wav': 'audio',
    'audio/ogg': 'audio',
    'audio/flac': 'audio',
    'audio/x-m4a': 'audio',
    'audio/mp4': 'audio',
    # Video
    'video/mp4': 'video',
    'video/avi': 'video',
    'video/x-matroska': 'video',
    'video/quicktime': 'video',
    'video/x-ms-wmv': 'video',
    'video/x-flv': 'video',
    'video/webm': 'video',
}

# Extension fallback mapping
EXT_TO_TYPE = {
    '.pdf': 'pdf',
    '.docx': 'docx',
    '.md': 'md',
    '.txt': 'md',
    '.json': 'json',
    '.xml': 'xml',
    '.jpg': 'image',
    '.jpeg': 'image',
    '.png': 'image',
    '.webp': 'image',
    '.gif': 'image',
    '.bmp': 'image',
    '.tiff': 'image',
    '.mp3': 'audio',
    '.wav': 'audio',
    '.ogg': 'audio',
    '.flac': 'audio',
    '.m4a': 'audio',
    '.mp4': 'video',
    '.avi': 'video',
    '.mkv': 'video',
    '.mov': 'video',
    '.wmv': 'video',
    '.flv': 'video',
    '.webm': 'video',
}


def get_file_type(content_type: str, filename: str) -> str:
    """Determine file type from content type or extension."""
    # Try content type first
    file_type = ALLOWED_TYPES.get(content_type)
    if file_type:
        return file_type
    
    # Fallback to extension
    ext = os.path.splitext(filename)[1].lower()
    file_type = EXT_TO_TYPE.get(ext)
    if file_type:
        return file_type
    
    return 'unknown'


@router.post("/collections/{collection_id}/upload", response_model=ApiResponse)
async def upload_document(
    collection_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Upload a document to a collection."""
    try:
        # Validate file type
        file_type = get_file_type(file.content_type or '', file.filename)
        if file_type == 'unknown':
            return ApiResponse(
                success=False, 
                error=f"Tipo de archivo no soportado: {file.content_type or 'desconocido'} ({file.filename})"
            )
        
        # Check file size
        content = await file.read()
        file_size = len(content)
        max_size = settings.MAX_FILE_SIZE or (500 * 1024 * 1024)  # 500MB default
        
        if file_size > max_size:
            return ApiResponse(
                success=False,
                error=f"Archivo demasiado grande: {file_size} bytes. Maximo: {max_size} bytes"
            )
        
        # Save file with sanitized filename
        upload_dir = os.path.join(settings.UPLOAD_DIR, str(collection_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        safe_filename = secure_filename(file.filename)
        file_path = os.path.join(upload_dir, safe_filename)
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Create document record
        document = Document(
            collection_id=collection_id,
            filename=file.filename,
            file_type=file_type,
            file_size=file_size,
            storage_path=file_path,
            status="processing"
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        # Trigger background processing (use sync wrapper since process_document is async)
        background_tasks.add_task(
            run_async_process,
            str(document.id),
            file_path,
            file_type,
            str(collection_id)
        )
        
        return ApiResponse(
            success=True,
            data={
                "id": str(document.id),
                "filename": document.filename,
                "file_type": document.file_type,
                "file_size": document.file_size,
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
    await verify_collection_access(db, collection_id, current_user)
    
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
            "metadata": d.metadata_,
            "created_at": d.created_at.isoformat()
        } for d in documents]
    )


@router.delete("/documents/{document_id}", response_model=ApiResponse)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Delete a document and all associated data."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    
    if not document:
        return ApiResponse(success=False, error="Documento no encontrado")
    
    await verify_collection_access(db, document.collection_id, current_user)
    
    # Delete extracted images
    images_dir = os.path.join(settings.UPLOAD_DIR, "images", str(document.collection_id), str(document_id))
    if os.path.exists(images_dir):
        try:
            shutil.rmtree(images_dir)
        except Exception as e:
            logger.warning(f"Failed to delete images dir {images_dir}: {e}")
    
    # Delete original file
    if os.path.exists(document.storage_path):
        try:
            os.remove(document.storage_path)
        except Exception as e:
            logger.warning(f"Failed to delete file {document.storage_path}: {e}")
    
    # Delete chunks
    await db.execute(delete(Chunk).where(Chunk.document_id == document_id))
    
    # Delete from DB
    await db.execute(delete(Document).where(Document.id == document_id))
    await db.commit()
    
    return ApiResponse(success=True, data={"message": "Documento eliminado correctamente"})


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
        return ApiResponse(success=False, error="Documento no encontrado")
    
    await verify_collection_access(db, document.collection_id, current_user)
    
    return ApiResponse(
        success=True,
        data={
            "id": str(document.id),
            "status": document.status,
            "filename": document.filename,
            "metadata": document.metadata_
        }
    )


@router.post("/documents/{document_id}/reindex", response_model=ApiResponse)
async def reindex_document(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Re-process an existing document (useful after config changes)."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    
    if not document:
        return ApiResponse(success=False, error="Documento no encontrado")
    
    await verify_collection_access(db, document.collection_id, current_user)
    
    # Delete old chunks
    await db.execute(delete(Chunk).where(Chunk.document_id == document_id))
    
    # Reset status
    document.status = "processing"
    document.metadata_ = {}
    await db.commit()
    
    # Trigger re-processing (use sync wrapper for async process_document)
    background_tasks.add_task(
        run_async_process,
        str(document.id),
        document.storage_path,
        document.file_type,
        str(document.collection_id)
    )
    
    return ApiResponse(success=True, data={"message": "Re-indexacion iniciada"})


# Image serving endpoint
@router.get("/data/images/{collection_id}/{document_id}/{image_name}")
async def serve_image(
    collection_id: str,
    document_id: str,
    image_name: str,
    current_user = Depends(require_auth)
):
    """Serve an extracted image file."""
    # Validate UUID format to prevent path traversal
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if not (re.match(uuid_pattern, collection_id) and re.match(uuid_pattern, document_id)):
        raise HTTPException(status_code=400, detail="ID invalido")
    
    # Sanitize image name
    safe_image_name = secure_filename(image_name)
    
    image_path = os.path.realpath(os.path.join(
        settings.UPLOAD_DIR, "images", 
        collection_id, document_id, safe_image_name
    ))
    
    # Ensure the resolved path is within the images directory
    base_dir = os.path.realpath(os.path.join(settings.UPLOAD_DIR, "images"))
    if not image_path.startswith(base_dir):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    
    # Determine content type from extension
    ext = os.path.splitext(image_name)[1].lower()
    content_type_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.tiff': 'image/tiff',
    }
    media_type = content_type_map.get(ext, 'application/octet-stream')
    
    return FileResponse(image_path, media_type=media_type)
