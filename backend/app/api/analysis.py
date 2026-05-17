"""Analysis router with real LLM-powered insights."""

import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.db.database import get_db
from app.db.models import Chunk, Collection
from app.api.auth import require_auth
from app.core.providers import ProviderFactory
from app.core.limiter import limiter
from app.search.web_search import search_web, format_web_results

logger = logging.getLogger(__name__)
router = APIRouter()


class MarketCompareRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500, description="Tema o producto a comparar")
    dimensions: list[str] | None = Field(default=None, description="Dimensiones especificas a comparar (ej: precio, calidad, mercado)")


class ApiResponse(BaseModel):
    success: bool
    data: dict | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_collection_chunks(db: AsyncSession, collection_id: UUID, max_chars: int = 100_000) -> list[Chunk]:
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


async def _call_llm_json(
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


# ---------------------------------------------------------------------------
# 5.1  Resumen automático
# ---------------------------------------------------------------------------

@router.get("/collections/{collection_id}/summary", response_model=ApiResponse)
@limiter.limit("5/minute")
async def get_summary(
    collection_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth),
):
    """Generate an automatic summary of a collection using LLM."""
    try:
        # Verify collection exists
        coll_result = await db.execute(
            select(Collection).where(Collection.id == collection_id)
        )
        collection = coll_result.scalar_one_or_none()
        if not collection:
            return ApiResponse(success=False, error="Coleccion no encontrada")

        chunks = await _get_collection_chunks(db, collection_id, max_chars=80_000)
        if not chunks:
            return ApiResponse(
                success=True,
                data={
                    "summary": "No hay documentos indexados en esta coleccion para resumir.",
                    "key_entities": [],
                    "topics": [],
                    "document_count": 0,
                    "chunk_count": 0,
                }
            )

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

        parsed = await _call_llm_json(
            db=db,
            prompt=prompt,
            temperature=0.3,
            max_tokens=1024,
            collection_id=collection_id,
        )

        # Normalize fields
        summary_text = parsed.get("summary", parsed.get("raw_response", "Resumen no disponible"))
        key_entities = parsed.get("key_entities", [])
        topics = parsed.get("topics", [])

        # Ensure lists
        if isinstance(key_entities, str):
            key_entities = [key_entities]
        if isinstance(topics, str):
            topics = [topics]

        return ApiResponse(
            success=True,
            data={
                "summary": summary_text,
                "key_entities": key_entities,
                "topics": topics,
                "document_count": len(set(c.document_id for c in chunks)),
                "chunk_count": len(chunks),
            }
        )
    except Exception as e:
        logger.error(f"Summary generation failed: {e}", exc_info=True)
        return ApiResponse(success=False, error=f"Error al generar resumen: {str(e)}")


# ---------------------------------------------------------------------------
# 5.2  Análisis predictivo
# ---------------------------------------------------------------------------

@router.get("/collections/{collection_id}/analysis", response_model=ApiResponse)
@limiter.limit("5/minute")
async def get_analysis(
    collection_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth),
):
    """Generate predictive analysis with metrics, trends and predictions."""
    try:
        coll_result = await db.execute(
            select(Collection).where(Collection.id == collection_id)
        )
        collection = coll_result.scalar_one_or_none()
        if not collection:
            return ApiResponse(success=False, error="Coleccion no encontrada")

        chunks = await _get_collection_chunks(db, collection_id, max_chars=80_000)
        if not chunks:
            return ApiResponse(
                success=True,
                data={
                    "metrics": {},
                    "trends": [],
                    "predictions": [],
                    "document_count": 0,
                    "chunk_count": 0,
                }
            )

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

        parsed = await _call_llm_json(
            db=db,
            prompt=prompt,
            temperature=0.3,
            max_tokens=2048,
            collection_id=collection_id,
        )

        metrics = parsed.get("metrics", {})
        trends = parsed.get("trends", [])
        predictions = parsed.get("predictions", [])

        # Normalize trends
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

        return ApiResponse(
            success=True,
            data={
                "metrics": metrics,
                "trends": normalized_trends,
                "predictions": normalized_predictions,
                "document_count": len(set(c.document_id for c in chunks)),
                "chunk_count": len(chunks),
            }
        )
    except Exception as e:
        logger.error(f"Analysis generation failed: {e}", exc_info=True)
        return ApiResponse(success=False, error=f"Error al generar analisis: {str(e)}")


# ---------------------------------------------------------------------------
# 5.3  Comparativa de mercado
# ---------------------------------------------------------------------------

@router.post("/collections/{collection_id}/market-compare", response_model=ApiResponse)
@limiter.limit("5/minute")
async def market_compare(
    collection_id: UUID,
    body: MarketCompareRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth),
):
    """Compare internal collection data against external web sources via Tavily."""
    try:
        coll_result = await db.execute(
            select(Collection).where(Collection.id == collection_id)
        )
        collection = coll_result.scalar_one_or_none()
        if not collection:
            return ApiResponse(success=False, error="Coleccion no encontrada")

        # Get internal chunks
        chunks = await _get_collection_chunks(db, collection_id, max_chars=60_000)
        internal_context = "\n\n---\n\n".join([c.content for c in chunks]) if chunks else ""

        # Web search via Tavily
        search_query = body.topic
        if body.dimensions:
            search_query += " " + " ".join(body.dimensions)

        web_results = await search_web(search_query, max_results=8, search_depth="advanced")
        web_context = format_web_results(web_results) if web_results else ""

        if not internal_context and not web_context:
            return ApiResponse(
                success=True,
                data={
                    "topic": body.topic,
                    "comparison_rows": [],
                    "conclusion": "No hay datos internos ni externos disponibles para comparar.",
                    "sources": [],
                }
            )

        prompt = f"""Realiza una comparativa de mercado entre los datos internos de la empresa y la informacion encontrada en internet.
Responde en formato JSON exacto con esta estructura:
{{
  "comparison_rows": [
    {{"dimension": "nombre de la dimension", "internal_data": "dato interno", "external_data": "dato externo", "source_url": "url de la fuente"}},
    ...
  ],
  "conclusion": "conclusion general de la comparativa en 2-3 oraciones"
}}

Tema a comparar: {body.topic}
Dimensiones: {', '.join(body.dimensions) if body.dimensions else 'generales'}

DATOS INTERNOS:
{internal_context or "No hay datos internos disponibles."}

DATOS EXTERNOS (Internet):
{web_context or "No se encontraron datos externos."}

Responde SOLO con el JSON valido."""

        parsed = await _call_llm_json(
            db=db,
            prompt=prompt,
            temperature=0.3,
            max_tokens=2048,
            collection_id=collection_id,
        )

        comparison_rows = parsed.get("comparison_rows", [])
        conclusion = parsed.get("conclusion", "Comparativa completada.")

        # Normalize rows
        normalized_rows = []
        for row in comparison_rows:
            if isinstance(row, dict):
                normalized_rows.append({
                    "dimension": row.get("dimension", "General"),
                    "internal_data": row.get("internal_data", "N/A"),
                    "external_data": row.get("external_data", "N/A"),
                    "source_url": row.get("source_url", ""),
                })
            elif isinstance(row, str):
                normalized_rows.append({
                    "dimension": "General",
                    "internal_data": row,
                    "external_data": "N/A",
                    "source_url": "",
                })

        sources = []
        for r in web_results:
            sources.append({"title": r["title"], "url": r["url"]})

        return ApiResponse(
            success=True,
            data={
                "topic": body.topic,
                "comparison_rows": normalized_rows,
                "conclusion": conclusion,
                "sources": sources,
            }
        )
    except Exception as e:
        logger.error(f"Market comparison failed: {e}", exc_info=True)
        return ApiResponse(success=False, error=f"Error en comparativa de mercado: {str(e)}")
