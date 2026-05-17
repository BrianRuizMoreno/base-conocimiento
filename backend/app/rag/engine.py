"""RAG engine: vector search and response generation using multi-provider factory."""

import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Chunk
from app.ingestion.embeddings import get_embedding
from app.core.providers import ProviderFactory
from app.core.config import settings
from app.core.webhooks import notify_chat_low_confidence
from app.search.web_search import search_web, format_web_results
from app.graph.search import hybrid_search

logger = logging.getLogger(__name__)


async def search_chunks(db: AsyncSession, collection_id: UUID, query_embedding: list[float], top_k: int = 5):
    """Search for similar chunks using pgvector cosine distance."""
    result = await db.execute(
        select(Chunk)
        .where(Chunk.collection_id == collection_id)
        .order_by(Chunk.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )
    return result.scalars().all()


async def generate_response(
    db: AsyncSession,
    question: str,
    context_chunks: list[Chunk],
    temperature: float = 0.2,
    top_p: float = 0.6,
    max_tokens: int = 2048,
    model: str = "gemini-2.0-flash",
    provider: str = "gemini",
    collection_id: UUID = None,
    user_id: UUID = None,
    history: list[dict] | None = None,
    web_search_results: list[dict] | None = None,
) -> dict:
    """Generate response using provider factory with RAG context."""

    # Build document context
    context_text = ""
    if context_chunks:
        context_text = "\n\n---\n\n".join([
            f"[Documento {i+1}]\n{chunk.content}"
            for i, chunk in enumerate(context_chunks)
        ])

    # Build web search context
    web_context = ""
    if web_search_results:
        web_context = format_web_results(web_search_results)

    # Build history context
    history_text = ""
    if history:
        history_lines = []
        for msg in history:
            role_label = "Usuario" if msg["role"] == "user" else "Asistente"
            history_lines.append(f"{role_label}: {msg['content']}")
        history_text = "\n\n".join(history_lines)
        history_text = f"\n\nHISTORIAL DE CONVERSACION:\n{history_text}\n\n"

    # Assemble prompt
    prompt_parts = ["Eres un asistente experto que responde preguntas basandose en la informacion proporcionada."]

    if context_text:
        prompt_parts.append(f"""
DOCUMENTOS DE LA COLECCION:
{context_text}
""")

    if web_context:
        prompt_parts.append(f"""
{web_context}
""")

    if history_text:
        prompt_parts.append(history_text)

    prompt_parts.append(f"""
PREGUNTA DEL USUARIO:
{question}

INSTRUCCIONES:
- Responde basandote en la informacion de los documentos y/o resultados de busqueda proporcionados.
- Si activaste la busqueda web, integra la informacion de internet con los documentos cuando sea relevante.
- Si la informacion no esta disponible, indicalo claramente.
- Cita las fuentes cuando sea posible.
- Responde en el mismo idioma que la pregunta.
- Manten el contexto de la conversacion anterior.
""")

    prompt = "\n".join(prompt_parts)

    factory = ProviderFactory(db)
    result = await factory.generate(
        prompt=prompt,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        provider=provider,
        model=model,
        collection_id=collection_id,
        user_id=user_id,
    )

    # Extract related images from chunk metadata
    related_media = []
    seen_images = set()
    for chunk in context_chunks:
        if chunk.metadata_:
            image_paths = chunk.metadata_.get("image_paths", [])
            for img_path in image_paths:
                if img_path not in seen_images:
                    seen_images.add(img_path)
                    # Convert filesystem path to API URL
                    # Path format: /data/images/{collection_id}/{document_id}/{image_name}
                    parts = img_path.replace("\\", "/").split("/")
                    if "images" in parts:
                        idx = parts.index("images")
                        if len(parts) > idx + 3:
                            coll_id = parts[idx + 1]
                            doc_id = parts[idx + 2]
                            img_name = parts[idx + 3]
                            related_media.append({
                                "type": "image",
                                "url": f"/api/v1/data/images/{coll_id}/{doc_id}/{img_name}"
                            })

    return {
        "answer": result["answer"],
        "sources": [
            {
                "chunk_index": chunk.chunk_index,
                "content_preview": chunk.content[:200] + "..."
            }
            for chunk in context_chunks
        ],
        "related_media": related_media,
        "model": result["model"],
        "tokens_used": result["tokens_in"] + result["tokens_out"],
        "tokens_in": result["tokens_in"],
        "tokens_out": result["tokens_out"],
    }


async def chat_with_collection(
    db: AsyncSession,
    collection_id: UUID,
    question: str,
    temperature: float = 0.2,
    top_p: float = 0.6,
    max_tokens: int = 2048,
    model: str = "gemini-2.0-flash",
    provider: str = "gemini",
    user_id: UUID = None,
    history: list[dict] | None = None,
    web_search: bool = False,
    use_graph: bool = False,
) -> dict:
    """Full RAG pipeline: embed query, search, generate response."""
    logger.info(f"Processing chat query for collection {collection_id} (use_graph={use_graph})")

    # 1. Get query embedding (pass db to use provider factory)
    query_embedding = await get_embedding(question, db=db)

    # 2. Search relevant chunks
    if use_graph:
        chunks = await hybrid_search(db, collection_id, query_embedding, question, top_k=5)
    else:
        chunks = await search_chunks(db, collection_id, query_embedding, top_k=5)

    # 3. Web search if enabled
    web_search_results = None
    if web_search:
        logger.info("Web search enabled, querying Tavily...")
        web_search_results = await search_web(question, max_results=5)

    # 4. If no chunks and no web results, return early + notify webhook
    if not chunks and not web_search_results:
        answer = "No encontre informacion relevante en los documentos de esta coleccion ni en internet para responder tu pregunta."
        await notify_chat_low_confidence(
            collection_id=str(collection_id),
            question=question,
            response=answer,
            reason="No se encontraron chunks relevantes ni resultados de busqueda web",
        )
        return {
            "answer": answer,
            "sources": [],
            "model": model,
            "tokens_used": 0
        }

    # 5. Generate response using factory (logs token usage automatically)
    result = await generate_response(
        db=db,
        question=question,
        context_chunks=chunks,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        model=model,
        provider=provider,
        collection_id=collection_id,
        user_id=user_id,
        history=history,
        web_search_results=web_search_results,
    )

    # Add web search metadata if used
    if web_search_results is not None:
        result["web_search_used"] = True
        result["web_search_results"] = [
            {"title": r["title"], "url": r["url"]} for r in web_search_results
        ]
    else:
        result["web_search_used"] = False

    return result
