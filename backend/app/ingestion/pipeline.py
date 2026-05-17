"""Document processing pipeline with image extraction and large file support."""

import logging
import os
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession


from app.db.database import SessionLocal
from app.db.models import Document, Chunk
from app.ingestion.parser import parse_file, split_large_file
from app.ingestion.chunker import chunk_text
from app.ingestion.embeddings import get_embeddings
from app.graph.extractor import extract_entities_from_chunk
from app.core.config import settings
from app.core.webhooks import notify_document_indexed, notify_document_error

logger = logging.getLogger(__name__)

# Max file size before splitting (20MB)
MAX_FILE_SIZE_MB = 20


async def process_document(document_id: str, file_path: str, file_type: str, collection_id: str):
    """
    Process a document: parse, chunk, embed, store.
    Handles images, audio, video, and large files.
    """
    async with SessionLocal() as db:
        try:
            # Update status to processing
            doc = await db.get(Document, UUID(document_id))
            if not doc:
                logger.error(f"Document {document_id} not found")
                return
            
            doc.status = "processing"
            await db.commit()
            
            # Check file size and split if needed
            file_size = os.path.getsize(file_path)
            max_size = MAX_FILE_SIZE_MB * 1024 * 1024
            
            if file_size > max_size:
                logger.info(f"File {file_path} is {file_size} bytes, splitting...")
                parts = split_large_file(file_path, MAX_FILE_SIZE_MB)
            else:
                parts = [file_path]
            
            all_chunks_data = []
            all_images = []
            total_text_length = 0
            parse_metadata = {}
            
            # Process each part
            for part_idx, part_path in enumerate(parts):
                logger.info(f"Parsing part {part_idx + 1}/{len(parts)} of document {document_id}...")
                
                # Parse file
                parse_result = await parse_file(part_path, file_type, collection_id, document_id)
                text = parse_result.get("text", "")
                images = parse_result.get("images", [])
                parse_metadata = parse_result.get("metadata", {})
                
                all_images.extend(images)
                total_text_length += len(text)
                
                # Chunk text
                if text and text.strip():
                    logger.info(f"Chunking part {part_idx + 1}...")
                    chunks = chunk_text(text)
                    
                    # Add image references to first chunk if there are images
                    if images and chunks:
                        if "image_paths" not in chunks[0]:
                            chunks[0]["image_paths"] = []
                        chunks[0]["image_paths"].extend(images)
                    
                    all_chunks_data.extend(chunks)
                
                # Cleanup temp part files
                if part_path != file_path and os.path.exists(part_path):
                    try:
                        os.remove(part_path)
                    except:
                        pass
            
            # Extract entities and generate embeddings
            all_entity_ids = set()
            if all_chunks_data:
                logger.info(f"Generating embeddings for {len(all_chunks_data)} chunks...")
                contents = [c["content"] for c in all_chunks_data]
                embeddings = await get_embeddings(contents, db=db)
                
                # Store chunks and extract entities
                logger.info(f"Storing chunks for document {document_id}...")
                for chunk_data, embedding in zip(all_chunks_data, embeddings):
                    metadata = {"index": chunk_data["index"]}
                    if "image_paths" in chunk_data:
                        metadata["image_paths"] = chunk_data["image_paths"]
                    
                    # Extract entities from chunk
                    try:
                        extraction = await extract_entities_from_chunk(
                            chunk_text=chunk_data["content"],
                            db=db,
                            collection_id=UUID(collection_id),
                        )
                        if extraction.get("entity_ids"):
                            metadata["entity_ids"] = [str(eid) for eid in extraction["entity_ids"]]
                            all_entity_ids.update(str(eid) for eid in extraction["entity_ids"])
                    except Exception as e:
                        logger.warning(f"Entity extraction failed for chunk: {e}")
                    
                    chunk = Chunk(
                        document_id=UUID(document_id),
                        collection_id=UUID(collection_id),
                        content=chunk_data["content"],
                        embedding=embedding,
                        chunk_index=chunk_data["index"],
                        metadata_=metadata
                    )
                    db.add(chunk)
            
            # Update document status
            doc.status = "completed"
            doc.metadata_ = {
                "total_chunks": len(all_chunks_data),
                "total_chars": total_text_length,
                "images_extracted": len(all_images),
                "image_paths": all_images,
                "parts_processed": len(parts),
                "parser": parse_metadata.get("source_type", file_type),
                "ocr_used": parse_metadata.get("ocr_used", False),
                "entity_ids": list(all_entity_ids),
            }
            await db.commit()
            logger.info(f"Document {document_id} processed successfully with {len(all_chunks_data)} chunks and {len(all_images)} images")
            
            # Notify n8n webhook
            await notify_document_indexed(
                document_id=document_id,
                collection_id=collection_id,
                filename=doc.filename,
                status="completed",
                metadata={
                    "total_chunks": len(all_chunks_data),
                    "total_chars": total_text_length,
                    "images_extracted": len(all_images),
                    "parts_processed": len(parts),
                },
            )
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}", exc_info=True)
            error_msg = str(e)
            try:
                doc = await db.get(Document, UUID(document_id))
                if doc:
                    doc.status = "error"
                    doc.metadata_ = {"error": error_msg}
                    await db.commit()
                    
                    # Notify n8n webhook
                    await notify_document_error(
                        document_id=document_id,
                        collection_id=collection_id,
                        filename=doc.filename,
                        error=error_msg,
                    )
            except Exception as inner:
                logger.error(f"Failed to update error status: {inner}")
