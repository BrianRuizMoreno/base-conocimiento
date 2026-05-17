"""Analysis service layer for reusable logic across routers."""

import json
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Chunk, Collection
from app.core.providers import ProviderFactory

logger = logging.getLogger(__name__)


async def get_collection_chunks(db: AsyncSession, collection_id: UUID, max_chars: int = 100_000) -> list[Chunk]:
    """Fetch chunks for a collection, limited by total characters."""
    result = await db.execute(
        select(Chunk)
        .where(Chunk.collection_id == collection_id)
        .order_by(Chunk.chunk_index.asc())
    )
    chunks = result.scalars().all()

    selected = []
    total_len = 0
    for chunk in chunks:
        if total_len + len(chunk.content) > max_chars:
            break
        selected.append(chunk)
        total_len += len(chunk.content)
    return selected


async def call_llm_json(
    db: AsyncSession,
    prompt: str,
    system: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    provider: str = "gemini",
    model: str = "gemini-2.0-flash",
    collection_id: UUID | None = None,
) -> dict:
    """Call LLM and attempt to parse JSON response."""
    factory = ProviderFactory(db)
    result = await factory.generate(
        prompt=prompt,
        system=system,
        temperature=temperature,
        top_p=0.6,
        max_tokens=max_tokens,
        provider=provider,
        model=model,
        collection_id=collection_id,
    )

    raw = result.get("answer", "").strip()
    # Try to extract JSON from markdown code blocks
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: try to find JSON-like structure
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                parsed = {"raw_response": raw}
        else:
            parsed = {"raw_response": raw}

    return parsed


async def generate_collection_summary(
    db: AsyncSession,
    collection_id: UUID,
    provider: str = "gemini",
    model: str = "gemini-2.0-flash",
) -> dict:
    """Generate summary, entities, and topics for a collection."""
    chunks = await get_collection_chunks(db, collection_id, max_chars=80_000)
    if not chunks:
        return {
            "summary": "No hay documentos indexados en esta coleccion para resumir.",
            "key_entities": [],
            "topics": [],
            "document_count": 0,
            "chunk_count": 0,
        }

    context = "\n\n---\n\n".join([c.content for c in chunks])

    prompt = f"""Analiza los siguientes documentos y genera un resumen estructurado en formato JSON exacto con esta estructura:
{{
  "summary": "resumen ejecutivo de maximo 300 palabras",
  "key_entities": ["entidad 1", "entidad 2", ...],
  "topics": ["tema 1", "tema 2", ...]
}}

Documentos:
{context}

Responde SOLO con el JSON valido, sin markdown ni explicaciones adicionales."""

    parsed = await call_llm_json(
        db=db,
        prompt=prompt,
        temperature=0.3,
        max_tokens=1024,
        provider=provider,
        model=model,
        collection_id=collection_id,
    )

    summary_text = parsed.get("summary", parsed.get("raw_response", "Resumen no disponible"))
    key_entities = parsed.get("key_entities", [])
    topics = parsed.get("topics", [])

    if isinstance(key_entities, str):
        key_entities = [key_entities]
    if isinstance(topics, str):
        topics = [topics]

    return {
        "summary": summary_text,
        "key_entities": key_entities,
        "topics": topics,
        "document_count": len(set(c.document_id for c in chunks)),
        "chunk_count": len(chunks),
    }


async def generate_collection_analysis(
    db: AsyncSession,
    collection_id: UUID,
    provider: str = "gemini",
    model: str = "gemini-2.0-flash",
) -> dict:
    """Generate predictive analysis with metrics, trends, and predictions."""
    chunks = await get_collection_chunks(db, collection_id, max_chars=80_000)
    if not chunks:
        return {
            "metrics": {},
            "trends": [],
            "predictions": [],
            "document_count": 0,
            "chunk_count": 0,
        }

    context = "\n\n---\n\n".join([c.content for c in chunks])

    prompt = f"""Analiza los siguientes documentos y extrae metricas, tendencias y predicciones.
Responde en formato JSON exacto con esta estructura:
{{
  "metrics": {{
    "nombre_metrica_1": valor_numerico_o_texto,
    "nombre_metrica_2": valor_numerico_o_texto
  }},
  "trends": [
    {{"name": "nombre tendencia", "value": valor_numerico, "direction": "up|down|stable", "period": "2023-2024"}},
    ...
  ],
  "predictions": [
    {{"statement": "prediccion descriptiva", "confidence": "alta|media|baja", "timeframe": "corto|medio|largo plazo"}},
    ...
  ]
}}

Si no hay datos numericos claros, usa estimaciones cualitativas como texto en metrics.

Documentos:
{context}

Responde SOLO con el JSON valido."""

    parsed = await call_llm_json(
        db=db,
        prompt=prompt,
        temperature=0.3,
        max_tokens=2048,
        provider=provider,
        model=model,
        collection_id=collection_id,
    )

    metrics = parsed.get("metrics", {})
    trends = parsed.get("trends", [])
    predictions = parsed.get("predictions", [])

    normalized_trends = []
    for t in trends:
        if isinstance(t, dict):
            normalized_trends.append({
                "name": t.get("name", "Tendencia"),
                "value": t.get("value", 0),
                "direction": t.get("direction", "stable"),
                "period": t.get("period", "Reciente"),
            })
        elif isinstance(t, str):
            normalized_trends.append({"name": t, "value": 0, "direction": "stable", "period": "Reciente"})

    normalized_predictions = []
    for p in predictions:
        if isinstance(p, dict):
            normalized_predictions.append({
                "statement": p.get("statement", ""),
                "confidence": p.get("confidence", "media"),
                "timeframe": p.get("timeframe", "medio plazo"),
            })
        elif isinstance(p, str):
            normalized_predictions.append({"statement": p, "confidence": "media", "timeframe": "medio plazo"})

    return {
        "metrics": metrics,
        "trends": normalized_trends,
        "predictions": normalized_predictions,
        "document_count": len(set(c.document_id for c in chunks)),
        "chunk_count": len(chunks),
    }
