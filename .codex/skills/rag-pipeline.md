---
name: rag-pipeline
description: Retrieval-Augmented Generation pipeline with hybrid vector+graph retrieval, HyDE, reranker, and configurable LLM parameters (top_p, temperature). Multi-provider support.
---

# RAG Pipeline Patterns

## Pipeline Flow
```
User Query
    ↓
[Query Expansion] — expand with related terms from graph entities
    ↓
[HyDE - Optional] — if low confidence, generate hypothetical answer → embed it
    ↓
[Vector Search] — cosine similarity on pgvector (top-20)
    ↓
[Graph Search] — find entities matching query → traverse relationships (top-10 related chunks)
    ↓
[Fusion] — combine vector + graph results, deduplicate
    ↓
[Rerank] — local cross-encoder scores and reorders (top-10 → top-5)
    ↓
[Context Builder] — assemble chunks with source metadata (filename, page, image_path)
    ↓
[LLM Generation] — send context + question to configured provider/model
    ↓
Response with citations + related_media (images)
```

## Configurable Parameters per Collection
```python
class ChatConfig(BaseModel):
    provider: str = "gemini"           # 'gemini' | 'openai' | 'anthropic'
    model: str = "gemini-2.0-flash"    # selected from available models
    temperature: float = 0.2           # 0.0 - 2.0
    top_p: float = 0.6                 # 0.0 - 1.0
    max_tokens: int = 2048
    use_hyde: bool = False             # auto-enable if <3 chunks with score>0.7
    use_graph: bool = True
    use_reranker: bool = True
```

## System Prompt
```
Eres un asistente experto que responde basado ÚNICAMENTE en la información proporcionada en el contexto.

Reglas:
1. Si la respuesta no está en el contexto, di "No tengo información suficiente para responder eso."
2. Cita las fuentes usando [Fuente: nombre_archivo, página X].
3. Si hay imágenes relacionadas, menciónalas.
4. Sé conciso pero completo.
5. Si la pregunta es ambigua, pide aclaración.

Contexto:
{context}

Pregunta: {question}
```

## Chunk Scoring Formula
```python
# Final score = weighted combination
def score_chunk(vector_score, graph_score, rerank_score):
    # vector_score: 0-1 (cosine similarity)
    # graph_score: 0-1 (entity match + relationship depth)
    # rerank_score: 0-1 (cross-encoder)
    return 0.4 * vector_score + 0.3 * graph_score + 0.3 * rerank_score
```

## Related Media Detection
```python
# When returning chat response, scan retrieved chunks for image references
related_media = []
for chunk in final_chunks:
    meta = chunk.metadata or {}
    if meta.get("source_type") == "image":
        related_media.append({
            "type": "image",
            "url": meta.get("storage_path"),
            "caption": meta.get("caption", "")
        })
```

## Fallback Strategy
```python
async def generate_response(query, context, config):
    # Try primary provider
    try:
        return await llm.generate(query, context, config)
    except Exception:
        # Fallback to next configured provider
        fallback = get_fallback_provider(config.provider)
        return await llm.generate(query, context, fallback)
```
