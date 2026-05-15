---
name: fastapi-backend
description: FastAPI backend patterns for the RAG system. Handles collections, document upload, chat endpoints, integration APIs. Uses SQLAlchemy 2.0 + pgvector + Gemini. PIN-based auth, multi-provider LLM support, async endpoints.
---

# FastAPI Backend Patterns

## Project Structure
```
backend/app/
├── main.py              # FastAPI app factory, lifespan events
├── api/                 # Route handlers (FastAPI routers)
│   ├── auth.py          # PIN verification, API key auth
│   ├── collections.py   # CRUD collections
│   ├── documents.py     # Upload, parse, delete, progress
│   ├── chat.py          # RAG chat endpoint
│   ├── analysis.py      # Summary, predictive, campaigns
│   ├── settings.py      # API keys, model config
│   ├── integration.py   # Public endpoints for n8n/bots
│   └── admin.py         # Metrics, logs, server status
├── core/
│   ├── config.py        # Pydantic Settings, env vars
│   ├── security.py      # PIN hash, API key gen, encrypt/decrypt
│   ├── providers.py     # LLM provider factory (Gemini, OpenAI, Anthropic)
│   ├── pricing.py       # Cost calculation per model
│   └── metrics.py       # Token tracking, execution logging
├── ingestion/
│   ├── pdf_parser.py    # PyMuPDF (fitz)
│   ├── docx_parser.py   # python-docx
│   ├── md_parser.py     # markdown + beautifulsoup
│   ├── json_parser.py   # json + ijson streaming
│   ├── xml_parser.py    # lxml structured/flat modes
│   ├── image_parser.py  # Gemini Flash OCR (3.0 → 3.1 fallback)
│   ├── audio_parser.py  # faster-whisper (local)
│   ├── video_parser.py  # ffmpeg extract audio → whisper
│   └── chunking_service.py  # RecursiveCharacterTextSplitter, streaming
├── vectorstore/
│   ├── pgvector.py      # SQLAlchemy pgvector operations
│   └── embeddings.py    # Hash cache, multi-provider embeddings
├── rag/
│   ├── retriever.py     # Vector search + HyDE optional
│   ├── graph_retriever.py  # Entity-relationship queries
│   ├── reranker.py      # Local cross-encoder
│   └── generator.py     # Chat response with source citations
├── search/
│   └── web_search.py    # Tavily integration for market compare
├── analysis/
│   ├── summarizer.py    # Auto-summary of collection
│   ├── predictive.py    # Trend analysis on structured data
│   └── campaign.py      # Campaign generation endpoint
├── models/              # Pydantic schemas
└── db/
    ├── database.py      # Async engine, session
    ├── models.py        # SQLAlchemy ORM + pgvector
    └── seed.py          # Admin user, pricing defaults
```

## Conventions
- All endpoints async (`async def`)
- Pydantic v2 for request/response schemas
- SQLAlchemy 2.0 with async sessions (`AsyncSession`)
- Dependency injection for services via `Depends()`
- Consistent response format: `{success: bool, data: Any, error: str|null}`
- Use `Annotated` for FastAPI dependencies
- Alembic for migrations: `alembic revision --autogenerate -m "msg"`

## Auth
- PIN stored as bcrypt hash in `users.pin_hash`
- API keys: prefix + hash, stored in `integration_keys`
- API keys scoped to collections via `scoped_collections UUID[]`
- Admin (`role='admin'`) sees all collections

## Cost Tracking
- Every LLM call logged to `token_usage` table
- `pricing.py` holds per-model rates (updatable by admin)
- Embedding calls cached by SHA256 hash → no re-embed

## Error Handling
- Custom exception handlers in `main.py`
- Structured errors: `{success: false, error: "message", code: "ERR_CODE"}`
- All exceptions logged to `error_log` table with traceback
