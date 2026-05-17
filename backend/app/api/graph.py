"""Graph API router for entity and relationship management."""

import logging
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List

from app.db.database import get_db
from app.db.models import Entity, Relationship, Chunk, Document
from app.api.auth import require_auth, verify_collection_access
from app.graph.extractor import extract_entities_from_chunk

router = APIRouter()
logger = logging.getLogger(__name__)


class ApiResponse(BaseModel):
    success: bool
    data: dict | list | None = None
    error: str | None = None


async def _build_graph_data(entities: list[Entity], relationships: list[Relationship]) -> dict:
    nodes = [
        {
            "data": {
                "id": str(e.id),
                "label": e.name,
                "type": e.type or "other",
            }
        }
        for e in entities
    ]

    edges = [
        {
            "data": {
                "source": str(r.source_entity_id),
                "target": str(r.target_entity_id),
                "label": r.relation_type or "related_to",
                "weight": r.weight or 1.0,
            }
        }
        for r in relationships
    ]

    return {"nodes": nodes, "edges": edges}


@router.get("/global/graph", response_model=ApiResponse)
async def get_global_graph(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth),
):
    """Return graph in Cytoscape format for all collections."""
    try:
        entity_result = await db.execute(select(Entity))
        entities = entity_result.scalars().all()

        entity_ids = {str(e.id) for e in entities}

        rel_result = await db.execute(
            select(Relationship).where(
                Relationship.source_entity_id.in_(entity_ids),
                Relationship.target_entity_id.in_(entity_ids),
            )
        )
        relationships = rel_result.scalars().all()

        data = await _build_graph_data(entities, relationships)
        return ApiResponse(success=True, data=data)
    except Exception as e:
        logger.error(f"Error getting global graph: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/{collection_id}/graph", response_model=ApiResponse)
async def get_collection_graph(
    collection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth),
):
    """Return graph in Cytoscape format for a collection."""
    try:
        await verify_collection_access(db, collection_id, current_user)
        
        # Get entities
        entity_result = await db.execute(
            select(Entity).where(Entity.collection_id == collection_id)
        )
        entities = entity_result.scalars().all()

        entity_ids = {str(e.id) for e in entities}

        # Get relationships between these entities
        rel_result = await db.execute(
            select(Relationship).where(
                Relationship.source_entity_id.in_(entity_ids),
                Relationship.target_entity_id.in_(entity_ids),
            )
        )
        relationships = rel_result.scalars().all()

        data = await _build_graph_data(entities, relationships)
        return ApiResponse(success=True, data=data)
    except Exception as e:
        logger.error(f"Error getting graph: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.post("/{collection_id}/regenerate-graph", response_model=ApiResponse)
async def regenerate_graph(
    collection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth),
):
    """Re-process entity extraction for all chunks in a collection."""
    try:
        await verify_collection_access(db, collection_id, current_user)
        
        # Delete existing entities and relationships for this collection
        await db.execute(
            delete(Relationship).where(
                Relationship.source_entity_id.in_(
                    select(Entity.id).where(Entity.collection_id == collection_id).scalar_subquery()
                )
            )
        )
        await db.execute(
            delete(Relationship).where(
                Relationship.target_entity_id.in_(
                    select(Entity.id).where(Entity.collection_id == collection_id).scalar_subquery()
                )
            )
        )
        await db.execute(delete(Entity).where(Entity.collection_id == collection_id))
        await db.commit()

        # Get all chunks for this collection
        chunk_result = await db.execute(
            select(Chunk).where(Chunk.collection_id == collection_id)
        )
        chunks = chunk_result.scalars().all()

        total_entities = 0
        total_relationships = 0

        for chunk in chunks:
            result = await extract_entities_from_chunk(
                chunk_text=chunk.content,
                db=db,
                collection_id=collection_id,
            )
            entity_ids = result.get("entity_ids", [])
            relationship_ids = result.get("relationship_ids", [])

            # Update chunk metadata with entity_ids
            if entity_ids:
                metadata = chunk.metadata_ or {}
                metadata["entity_ids"] = [str(eid) for eid in entity_ids]
                chunk.metadata_ = metadata
                db.add(chunk)

            total_entities += len(entity_ids)
            total_relationships += len(relationship_ids)

        await db.commit()

        return ApiResponse(
            success=True,
            data={
                "message": "Grafo regenerado correctamente",
                "chunks_processed": len(chunks),
                "entities_extracted": total_entities,
                "relationships_extracted": total_relationships,
            },
        )
    except Exception as e:
        logger.error(f"Error regenerating graph: {e}", exc_info=True)
        await db.rollback()
        return ApiResponse(success=False, error=str(e))


@router.get("/{collection_id}/entities", response_model=ApiResponse)
async def list_entities(
    collection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth),
):
    """List all entities for a collection."""
    try:
        await verify_collection_access(db, collection_id, current_user)
        
        result = await db.execute(
            select(Entity).where(Entity.collection_id == collection_id)
        )
        entities = result.scalars().all()

        data = [
            {
                "id": str(e.id),
                "name": e.name,
                "type": e.type,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entities
        ]

        return ApiResponse(success=True, data=data)
    except Exception as e:
        logger.error(f"Error listing entities: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/entities/{entity_id}/related", response_model=ApiResponse)
async def get_related_entities(
    entity_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth),
):
    """Get related entities up to 2 hops away."""
    try:
        # 1-hop relationships
        hop1_result = await db.execute(
            select(Relationship).where(
                (Relationship.source_entity_id == str(entity_id))
                | (Relationship.target_entity_id == str(entity_id))
            )
        )
        hop1_rels = hop1_result.scalars().all()

        hop1_ids = set()
        for r in hop1_rels:
            hop1_ids.add(str(r.source_entity_id))
            hop1_ids.add(str(r.target_entity_id))
        hop1_ids.discard(str(entity_id))

        # 2-hop relationships
        hop2_ids = set()
        if hop1_ids:
            hop2_result = await db.execute(
                select(Relationship).where(
                    Relationship.source_entity_id.in_(hop1_ids)
                    | Relationship.target_entity_id.in_(hop1_ids)
                )
            )
            hop2_rels = hop2_result.scalars().all()
            for r in hop2_rels:
                hop2_ids.add(str(r.source_entity_id))
                hop2_ids.add(str(r.target_entity_id))

        # Remove self and 1-hop from 2-hop to get pure 2-hop
        hop2_ids.discard(str(entity_id))
        hop2_ids -= hop1_ids

        # Fetch entity details
        all_related_ids = hop1_ids | hop2_ids
        if not all_related_ids:
            return ApiResponse(success=True, data={"hop1": [], "hop2": []})

        entity_result = await db.execute(
            select(Entity).where(Entity.id.in_(all_related_ids))
        )
        entities = entity_result.scalars().all()
        entity_map = {str(e.id): e for e in entities}

        hop1_data = []
        for eid in hop1_ids:
            ent = entity_map.get(eid)
            if ent:
                hop1_data.append({
                    "id": str(ent.id),
                    "name": ent.name,
                    "type": ent.type,
                })

        hop2_data = []
        for eid in hop2_ids:
            ent = entity_map.get(eid)
            if ent:
                hop2_data.append({
                    "id": str(ent.id),
                    "name": ent.name,
                    "type": ent.type,
                })

        return ApiResponse(success=True, data={"hop1": hop1_data, "hop2": hop2_data})
    except Exception as e:
        logger.error(f"Error getting related entities: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))
