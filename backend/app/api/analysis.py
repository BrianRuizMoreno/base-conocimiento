"""Analysis router with real LLM-powered insights."""

import logging
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.db.database import get_db
from app.db.models import Collection
from app.api.auth import require_auth, verify_collection_access
from app.core.limiter import limiter
from app.search.web_search import search_web, format_web_results
from app.services.analysis_service import (
    generate_collection_summary,
    generate_collection_analysis,
    call_llm_json,
    get_collection_chunks,
)

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
# 5.1  Resumen automatico
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
        await verify_collection_access(db, collection_id, current_user)
        data = await generate_collection_summary(db, collection_id)
        return ApiResponse(success=True, data=data)
    except Exception as e:
        logger.error(f"Summary generation failed: {e}", exc_info=True)
        return ApiResponse(success=False, error=f"Error al generar resumen: {str(e)}")


# ---------------------------------------------------------------------------
# 5.2  Analisis predictivo
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
        await verify_collection_access(db, collection_id, current_user)
        data = await generate_collection_analysis(db, collection_id)
        return ApiResponse(success=True, data=data)
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
    request: Request,
    body: MarketCompareRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_auth),
):
    """Compare internal collection data against external web sources via Tavily."""
    try:
        await verify_collection_access(db, collection_id, current_user)
        
        # Get internal chunks
        chunks = await get_collection_chunks(db, collection_id, max_chars=60_000)
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

        parsed = await call_llm_json(
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
