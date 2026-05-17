"""Entity and relationship extraction using Gemini."""

import json
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Entity, Relationship
from app.core.providers import ProviderFactory

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Extrae todas las entidades y relaciones del siguiente texto.

Formato de salida (JSON):
{
  "entities": [
    {"name": "nombre", "type": "company|person|product|metric|date|location|technology|industry"}
  ],
  "relationships": [
    {"source": "entidad A", "target": "entidad B", "type": "competes_with|sells|works_for|located_in|has_price|grows_by|uses|belongs_to"}
  ]
}

Texto: {chunk_text}
"""

VALID_ENTITY_TYPES = {
    "company", "person", "product", "metric", "date", "location", "technology", "industry"
}

VALID_RELATION_TYPES = {
    "competes_with", "sells", "works_for", "located_in", "has_price", "grows_by", "uses", "belongs_to"
}


def _sanitize_entity_type(entity_type: str) -> str:
    t = entity_type.lower().strip()
    return t if t in VALID_ENTITY_TYPES else "other"


def _sanitize_relation_type(rel_type: str) -> str:
    t = rel_type.lower().strip().replace(" ", "_")
    return t if t in VALID_RELATION_TYPES else "related_to"


def _parse_extraction_response(answer: str) -> dict:
    """Parse Gemini response to extract JSON."""
    # Try to find JSON block
    text = answer.strip()
    # Remove markdown code blocks
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first line if it starts with ```
        if lines[0].startswith("```"):
            lines = lines[1:]
        # Remove last line if it starts with ```
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find json substring
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse extraction JSON: {answer[:200]}")
                return {"entities": [], "relationships": []}
        else:
            logger.warning(f"No JSON found in extraction response: {answer[:200]}")
            return {"entities": [], "relationships": []}

    entities = data.get("entities", []) if isinstance(data.get("entities"), list) else []
    relationships = data.get("relationships", []) if isinstance(data.get("relationships"), list) else []
    return {"entities": entities, "relationships": relationships}


async def extract_entities_from_chunk(
    chunk_text: str,
    db: AsyncSession,
    collection_id: UUID,
) -> dict:
    """
    Extract entities and relationships from a chunk of text using Gemini.
    Deduplicates by name + type + collection_id.
    Stores in entities and relationships tables.
    Returns dict with stored entity_ids and relationship_ids.
    """
    if not chunk_text or not chunk_text.strip():
        return {"entity_ids": [], "relationship_ids": []}

    try:
        factory = ProviderFactory(db)
        prompt = EXTRACTION_PROMPT.format(chunk_text=chunk_text[:8000])

        result = await factory.generate(
            prompt=prompt,
            temperature=0.1,
            top_p=0.5,
            max_tokens=1024,
            provider="gemini",
            model="gemini-2.0-flash",
            collection_id=collection_id,
        )

        parsed = _parse_extraction_response(result.get("answer", ""))
    except Exception as e:
        logger.error(f"Gemini extraction failed: {e}", exc_info=True)
        return {"entity_ids": [], "relationship_ids": []}

    entity_ids = []
    name_to_id = {}

    # Deduplicate and store entities
    for ent in parsed["entities"]:
        name = ent.get("name", "").strip()
        raw_type = ent.get("type", "other")
        if not name:
            continue

        entity_type = _sanitize_entity_type(raw_type)
        key = (name.lower(), entity_type)

        if key in name_to_id:
            entity_ids.append(name_to_id[key])
            continue

        # Check if already exists in DB for this collection
        try:
            existing_result = await db.execute(
                select(Entity).where(
                    Entity.collection_id == collection_id,
                    Entity.name.ilike(name),
                    Entity.type == entity_type,
                )
            )
            existing = existing_result.scalar_one_or_none()
            if existing:
                name_to_id[key] = existing.id
                entity_ids.append(existing.id)
                continue
        except Exception as e:
            logger.warning(f"Error checking existing entity: {e}")

        new_entity = Entity(
            name=name,
            type=entity_type,
            collection_id=collection_id,
            metadata_={"extracted_from": "chunk"},
        )
        db.add(new_entity)
        try:
            await db.commit()
            await db.refresh(new_entity)
            name_to_id[key] = new_entity.id
            entity_ids.append(new_entity.id)
        except Exception as e:
            logger.warning(f"Error storing entity: {e}")
            await db.rollback()

    # Store relationships
    relationship_ids = []
    seen_rels = set()

    for rel in parsed["relationships"]:
        source_name = rel.get("source", "").strip()
        target_name = rel.get("target", "").strip()
        rel_type = _sanitize_relation_type(rel.get("type", "related_to"))

        if not source_name or not target_name:
            continue

        source_key = (source_name.lower(),)
        target_key = (target_name.lower(),)

        # Find source and target entity IDs (match by name, any type)
        source_id = None
        target_id = None
        for key, eid in name_to_id.items():
            if key[0] == source_name.lower():
                source_id = eid
            if key[0] == target_name.lower():
                target_id = eid
            if source_id and target_id:
                break

        if not source_id or not target_id:
            # Try DB lookup by name only
            try:
                if not source_id:
                    res = await db.execute(
                        select(Entity).where(
                            Entity.collection_id == collection_id,
                            Entity.name.ilike(source_name),
                        )
                    )
                    ent = res.scalar_one_or_none()
                    if ent:
                        source_id = ent.id
                if not target_id:
                    res = await db.execute(
                        select(Entity).where(
                            Entity.collection_id == collection_id,
                            Entity.name.ilike(target_name),
                        )
                    )
                    ent = res.scalar_one_or_none()
                    if ent:
                        target_id = ent.id
            except Exception as e:
                logger.warning(f"Error looking up entities for relationship: {e}")

        if not source_id or not target_id or source_id == target_id:
            continue

        rel_key = (str(source_id), str(target_id), rel_type)
        if rel_key in seen_rels:
            continue
        seen_rels.add(rel_key)

        # Check existing relationship
        try:
            existing_result = await db.execute(
                select(Relationship).where(
                    Relationship.source_entity_id == source_id,
                    Relationship.target_entity_id == target_id,
                    Relationship.relation_type == rel_type,
                )
            )
            existing = existing_result.scalar_one_or_none()
            if existing:
                relationship_ids.append(existing.id)
                continue
        except Exception as e:
            logger.warning(f"Error checking existing relationship: {e}")

        new_rel = Relationship(
            source_entity_id=source_id,
            target_entity_id=target_id,
            relation_type=rel_type,
            weight=1.0,
            metadata_={"extracted_from": "chunk"},
        )
        db.add(new_rel)
        try:
            await db.commit()
            await db.refresh(new_rel)
            relationship_ids.append(new_rel.id)
        except Exception as e:
            logger.warning(f"Error storing relationship: {e}")
            await db.rollback()

    return {"entity_ids": entity_ids, "relationship_ids": relationship_ids}
