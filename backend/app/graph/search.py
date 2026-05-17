"""Hybrid search combining vector similarity and graph traversal."""

import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func

from app.db.models import Chunk, Entity, Relationship

logger = logging.getLogger(__name__)


async def hybrid_search(
    db: AsyncSession,
    collection_id: UUID,
    query_embedding: list[float],
    query_text: str,
    top_k: int = 5,
) -> list[Chunk]:
    """
    Hybrid search combining vector similarity and graph-based retrieval.

    Steps:
    1. Vector search: top-20 chunks by cosine similarity
    2. Graph search: find entities mentioned in query_text, then find chunks
       whose metadata contains those entity ids
    3. Fusion: combine, deduplicate by chunk_id
    4. Rerank: sort by combined score (vector rank + graph presence boost)
    5. Return top-k chunks
    """
    # 1. Vector search
    vector_result = await db.execute(
        select(Chunk)
        .where(Chunk.collection_id == collection_id)
        .order_by(Chunk.embedding.cosine_distance(query_embedding))
        .limit(20)
    )
    vector_chunks = vector_result.scalars().all()

    # 2. Graph search - find entities in query text
    # Simple approach: find all entities in the collection whose name appears in the query
    entity_result = await db.execute(
        select(Entity).where(Entity.collection_id == collection_id)
    )
    all_entities = entity_result.scalars().all()

    query_lower = query_text.lower()
    matched_entity_ids = []
    for ent in all_entities:
        if ent.name.lower() in query_lower:
            matched_entity_ids.append(str(ent.id))

    graph_chunks = []
    if matched_entity_ids:
        # Find chunks whose metadata contains any of these entity_ids
        # Since metadata is JSONB, we check if metadata->'entity_ids' contains the UUID
        # For simplicity, we iterate through chunks - could be optimized with JSONB operator
        chunk_result = await db.execute(
            select(Chunk).where(Chunk.collection_id == collection_id)
        )
        all_chunks = chunk_result.scalars().all()
        for chunk in all_chunks:
            if chunk.metadata_ and "entity_ids" in chunk.metadata_:
                chunk_entity_ids = chunk.metadata_["entity_ids"]
                if isinstance(chunk_entity_ids, list):
                    for eid in matched_entity_ids:
                        if eid in chunk_entity_ids:
                            graph_chunks.append(chunk)
                            break

    # 3. Fusion and deduplication
    seen_ids = set()
    combined = []

    for rank, chunk in enumerate(vector_chunks):
        if chunk.id not in seen_ids:
            seen_ids.add(chunk.id)
            combined.append({"chunk": chunk, "vector_rank": rank, "graph_match": False})

    for chunk in graph_chunks:
        if chunk.id in seen_ids:
            # Boost existing entry
            for item in combined:
                if item["chunk"].id == chunk.id:
                    item["graph_match"] = True
                    break
        else:
            seen_ids.add(chunk.id)
            combined.append({"chunk": chunk, "vector_rank": 999, "graph_match": True})

    # 4. Rerank: lower score is better
    # vector_rank [0..19] + graph_match gives -5 bonus
    def score(item):
        s = item["vector_rank"]
        if item["graph_match"]:
            s -= 10
        return s

    combined.sort(key=score)

    # 5. Return top-k
    return [item["chunk"] for item in combined[:top_k]]
