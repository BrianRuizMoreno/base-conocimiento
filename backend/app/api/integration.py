"""Integration router (public API for n8n/bots) with real implementations."""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.db.database import get_db
from app.db.models import Collection, Chunk, IntegrationKey
from app.core.security import hash_api_key
from app.core.limiter import limiter
from app.core.config import settings
from app.rag.engine import chat_with_collection, search_chunks
from app.ingestion.embeddings import get_embedding
from app.search.web_search import search_web, format_web_results
from app.services.analysis_service import (
    generate_collection_summary,
    generate_collection_analysis,
    call_llm_json,
    get_collection_chunks,
)
from app.core.providers import ProviderFactory

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=0.6, ge=0.0, le=1.0)
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    web_search: bool = False
    use_graph: bool = False


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=10, ge=1, le=50)


class MarketCompareRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    dimensions: list[str] | None = Field(default=None)


class CampaignGenerateRequest(BaseModel):
    collection_id: UUID
    campaign_type: str = Field(default="general", description="Tipo de campana: email, social, ads, general")
    target_audience: str | None = Field(default=None, description="Audiencia objetivo (si no se proporciona, se infiere del contenido)")
    tone: str = Field(default="profesional", description="Tono: profesional, casual, persuasivo, informativo")


class CampaignContentRequest(BaseModel):
    collection_id: UUID
    brief: str = Field(..., min_length=10, description="Brief de la campana generado previamente")
    campaign_type: str = Field(default="general")
    tone: str = Field(default="profesional")


class ApiResponse(BaseModel):
    success: bool
    data: dict | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# API Key Auth
# ---------------------------------------------------------------------------

async def require_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
):
    """Verify integration API key from header."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header requerido")
    
    key_hash = hash_api_key(x_api_key)
    result = await db.execute(
        select(IntegrationKey).where(
            IntegrationKey.key_hash == key_hash,
            IntegrationKey.is_active == True,
        )
    )
    key = result.scalar_one_or_none()
    
    if not key:
        raise HTTPException(status_code=401, detail="API key invalida")
    
    # Check expiration
    if key.expires_at and key.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="API key expirada")
    
    # Update last_used_at
    key.last_used_at = datetime.utcnow()
    await db.commit()
    
    return key


def _check_collection_scope(key: IntegrationKey, collection_id: UUID):
    """Check if the API key is scoped to the requested collection."""
    if key.scoped_collections and len(key.scoped_collections) > 0:
        if str(collection_id) not in [str(c) for c in key.scoped_collections]:
            raise HTTPException(status_code=403, detail="API key no autorizada para esta coleccion")


# ---------------------------------------------------------------------------
# 6.1 POST /integration/chat/{id}
# ---------------------------------------------------------------------------

@router.post("/chat/{collection_id}", response_model=ApiResponse)
@limiter.limit("30/minute")
async def integration_chat(
    collection_id: UUID,
    request: Request,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    api_key: IntegrationKey = Depends(require_api_key),
):
    """Chat with a collection via integration API (same RAG engine as panel)."""
    try:
        _check_collection_scope(api_key, collection_id)
        
        result = await chat_with_collection(
            db=db,
            collection_id=collection_id,
            question=body.question,
            temperature=body.temperature,
            top_p=body.top_p,
            max_tokens=body.max_tokens,
            provider="gemini",
            model="gemini-2.0-flash",
            web_search=body.web_search,
            use_graph=body.use_graph,
        )
        
        # Return simplified response for API consumers
        return ApiResponse(
            success=True,
            data={
                "answer": result.get("answer", ""),
                "sources": result.get("sources", []),
                "web_search_used": result.get("web_search_used", False),
                "model": result.get("model"),
                "tokens_used": result.get("tokens_used"),
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Integration chat failed: {e}", exc_info=True)
        return ApiResponse(success=False, error=f"Error en chat: {str(e)}")


# ---------------------------------------------------------------------------
# 6.2 POST /integration/search/{id}
# ---------------------------------------------------------------------------

@router.post("/search/{collection_id}", response_model=ApiResponse)
@limiter.limit("30/minute")
async def integration_search(
    collection_id: UUID,
    request: Request,
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
    api_key: IntegrationKey = Depends(require_api_key),
):
    """Pure vector search (no LLM generation). Returns top_k chunks."""
    try:
        _check_collection_scope(api_key, collection_id)
        
        query_embedding = await get_embedding(body.query, db=db)
        chunks = await search_chunks(db, collection_id, query_embedding, top_k=body.top_k)
        
        results = []
        for chunk in chunks:
            results.append({
                "chunk_id": str(chunk.id),
                "document_id": str(chunk.document_id),
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "metadata": chunk.metadata_,
            })
        
        return ApiResponse(
            success=True,
            data={
                "query": body.query,
                "top_k": body.top_k,
                "results_count": len(results),
                "results": results,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Integration search failed: {e}", exc_info=True)
        return ApiResponse(success=False, error=f"Error en busqueda: {str(e)}")


# ---------------------------------------------------------------------------
# 6.3 GET /integration/collections
# ---------------------------------------------------------------------------

@router.get("/collections", response_model=ApiResponse)
@limiter.limit("30/minute")
async def list_collections(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: IntegrationKey = Depends(require_api_key),
):
    """List collections accessible with this API key."""
    try:
        query = select(Collection)
        
        # If API key is scoped, filter collections
        if api_key.scoped_collections and len(api_key.scoped_collections) > 0:
            scoped_ids = [UUID(str(c)) for c in api_key.scoped_collections]
            query = query.where(Collection.id.in_(scoped_ids))
        
        result = await db.execute(query)
        collections = result.scalars().all()
        
        return ApiResponse(
            success=True,
            data=[
                {
                    "id": str(c.id),
                    "name": c.name,
                    "description": c.description,
                    "created_at": c.created_at.isoformat(),
                }
                for c in collections
            ]
        )
    except Exception as e:
        logger.error(f"Integration collections failed: {e}", exc_info=True)
        return ApiResponse(success=False, error=f"Error listando colecciones: {str(e)}")


# ---------------------------------------------------------------------------
# 6.4 GET /integration/summary/{id}
# ---------------------------------------------------------------------------

@router.get("/summary/{collection_id}", response_model=ApiResponse)
@limiter.limit("10/minute")
async def get_summary(
    collection_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: IntegrationKey = Depends(require_api_key),
):
    """Get collection summary via integration API."""
    try:
        _check_collection_scope(api_key, collection_id)
        
        data = await generate_collection_summary(db, collection_id)
        return ApiResponse(success=True, data=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Integration summary failed: {e}", exc_info=True)
        return ApiResponse(success=False, error=f"Error en resumen: {str(e)}")


# ---------------------------------------------------------------------------
# 6.5 POST /integration/market-compare/{id}
# ---------------------------------------------------------------------------

@router.post("/market-compare/{collection_id}", response_model=ApiResponse)
@limiter.limit("10/minute")
async def market_compare(
    collection_id: UUID,
    request: Request,
    body: MarketCompareRequest,
    db: AsyncSession = Depends(get_db),
    api_key: IntegrationKey = Depends(require_api_key),
):
    """Market comparison via integration API (internal data vs Tavily web search)."""
    try:
        _check_collection_scope(api_key, collection_id)
        
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Integration market compare failed: {e}", exc_info=True)
        return ApiResponse(success=False, error=f"Error en comparativa: {str(e)}")


# ---------------------------------------------------------------------------
# 6.6 POST /integration/campaign/generate
# ---------------------------------------------------------------------------

@router.post("/campaign/generate", response_model=ApiResponse)
@limiter.limit("10/minute")
async def generate_campaign(
    request: Request,
    body: CampaignGenerateRequest,
    db: AsyncSession = Depends(get_db),
    api_key: IntegrationKey = Depends(require_api_key),
):
    """Generate a campaign brief based on collection content."""
    try:
        _check_collection_scope(api_key, body.collection_id)
        
        # Get collection content
        chunks = await get_collection_chunks(db, body.collection_id, max_chars=60_000)
        if not chunks:
            return ApiResponse(
                success=True,
                data={
                    "brief": "No hay contenido en la coleccion para generar un brief.",
                    "key_points": [],
                    "target_audience": body.target_audience or "General",
                }
            )
        
        context = "\n\n---\n\n".join([c.content for c in chunks])
        
        prompt = f"""Basandote en el siguiente contenido de la empresa, genera un brief de campana de marketing completo.
Responde en formato JSON exacto con esta estructura:
{{
  "brief": "descripcion completa de la campana en 200-400 palabras",
  "key_points": ["punto clave 1", "punto clave 2", ...],
  "target_audience": "descripcion del publico objetivo",
  "value_proposition": "propuesta de valor principal",
  "channels": ["canal 1", "canal 2", ...],
  "goals": ["objetivo 1", "objetivo 2", ...],
  "tone": "tono recomendado"
}}

Tipo de campana: {body.campaign_type}
Tono deseado: {body.tone}
Audiencia objetivo: {body.target_audience or "Infierela del contenido"}

CONTENIDO DE LA EMPRESA:
{context}

Responde SOLO con el JSON valido."""
        
        parsed = await call_llm_json(
            db=db,
            prompt=prompt,
            temperature=0.4,
            max_tokens=2048,
            collection_id=body.collection_id,
        )
        
        return ApiResponse(
            success=True,
            data={
                "brief": parsed.get("brief", parsed.get("raw_response", "Brief no disponible")),
                "key_points": parsed.get("key_points", []),
                "target_audience": parsed.get("target_audience", body.target_audience or "General"),
                "value_proposition": parsed.get("value_proposition", ""),
                "channels": parsed.get("channels", []),
                "goals": parsed.get("goals", []),
                "tone": parsed.get("tone", body.tone),
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Campaign generation failed: {e}", exc_info=True)
        return ApiResponse(success=False, error=f"Error generando campana: {str(e)}")


# ---------------------------------------------------------------------------
# 6.7 POST /integration/campaign/content
# ---------------------------------------------------------------------------

@router.post("/campaign/content", response_model=ApiResponse)
@limiter.limit("10/minute")
async def generate_campaign_content(
    request: Request,
    body: CampaignContentRequest,
    db: AsyncSession = Depends(get_db),
    api_key: IntegrationKey = Depends(require_api_key),
):
    """Generate campaign content pieces (headline, body, CTA) from a brief."""
    try:
        _check_collection_scope(api_key, body.collection_id)
        
        # Get some collection context for grounding
        chunks = await get_collection_chunks(db, body.collection_id, max_chars=30_000)
        context = "\n\n---\n\n".join([c.content for c in chunks]) if chunks else ""
        
        prompt = f"""Basandote en el siguiente brief y en el contenido de la empresa, genera piezas de contenido para la campana.
Responde en formato JSON exacto con esta estructura:
{{
  "headline": "titular principal atractivo (max 100 caracteres)",
  "headline_variants": ["variante 1", "variante 2", "variante 3"],
  "body": "cuerpo del mensaje (150-300 palabras)",
  "cta": "call to action corto y persuasivo (max 50 caracteres)",
  "cta_variants": ["variante 1", "variante 2"],
  "segmentation": ["segmento 1", "segmento 2", ...],
  "hashtags": ["#hashtag1", "#hashtag2", ...],
  "email_subject": "asunto para email (max 60 caracteres)",
  "ad_copy": "texto para anuncio corto (max 150 caracteres)"
}}

Tipo de campana: {body.campaign_type}
Tono: {body.tone}

BRIEF:
{body.brief}

CONTENIDO DE REFERENCIA:
{context or "No hay contenido de referencia adicional."}

Responde SOLO con el JSON valido."""
        
        parsed = await call_llm_json(
            db=db,
            prompt=prompt,
            temperature=0.5,
            max_tokens=2048,
            collection_id=body.collection_id,
        )
        
        return ApiResponse(
            success=True,
            data={
                "headline": parsed.get("headline", "Titular no disponible"),
                "headline_variants": parsed.get("headline_variants", []),
                "body": parsed.get("body", ""),
                "cta": parsed.get("cta", "Saber mas"),
                "cta_variants": parsed.get("cta_variants", []),
                "segmentation": parsed.get("segmentation", []),
                "hashtags": parsed.get("hashtags", []),
                "email_subject": parsed.get("email_subject", ""),
                "ad_copy": parsed.get("ad_copy", ""),
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Campaign content generation failed: {e}", exc_info=True)
        return ApiResponse(success=False, error=f"Error generando contenido: {str(e)}")
