---
name: pgvector-db
description: PostgreSQL + pgvector patterns for the RAG system. Async SQLAlchemy 2.0, pgvector extension for embeddings, entity-relationship tables for graph, token/execution/error logs.
---

# pgvector Database Patterns

## Core Tables

### Collections (knowledge bases)
```sql
CREATE TABLE collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id UUID REFERENCES users(id),
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT now()
);
```

### Documents
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,
    filename VARCHAR(500),
    file_type VARCHAR(50),  -- 'pdf','docx','md','json','xml','image','audio','video'
    file_size BIGINT,
    storage_path TEXT,
    status VARCHAR(20) DEFAULT 'processing', -- 'processing','indexed','error'
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now()
);
```

### Chunks (pgvector)
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding VECTOR(768),  -- Gemini text-embedding-004 = 768 dims
    chunk_index INT,
    hash VARCHAR(64),       -- SHA256 of content for dedup/cache
    metadata JSONB,         -- {page_num, source_type, image_path, ...}
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_chunks_collection ON chunks(collection_id);
CREATE INDEX idx_chunks_document ON chunks(document_id);
```

### Entities (graph)
```sql
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    type VARCHAR(50),       -- 'company','person','product','metric','date','location'
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_entities_type ON entities(type);
CREATE INDEX idx_entities_collection ON entities(collection_id);
```

### Relationships (graph edges)
```sql
CREATE TABLE relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    relation_type VARCHAR(100),  -- 'competes_with','sells','works_for','located_in'
    weight FLOAT DEFAULT 1.0,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_rel_source ON relationships(source_entity_id);
CREATE INDEX idx_rel_target ON relationships(target_entity_id);
CREATE INDEX idx_rel_type ON relationships(relation_type);
```

### Users (multi-tenant ready)
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    pin_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',  -- 'admin' | 'user'
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE collection_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    permission VARCHAR(20) DEFAULT 'read',  -- 'read' | 'write' | 'admin'
    UNIQUE(collection_id, user_id)
);
```

### Integration API Keys
```sql
CREATE TABLE integration_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(8) NOT NULL,
    name VARCHAR(100),
    user_id UUID REFERENCES users(id),
    scoped_collections UUID[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now()
);
```

### Admin Metrics Tables
```sql
CREATE TABLE token_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(20),
    model VARCHAR(50),
    operation VARCHAR(20),
    tokens_in INT,
    tokens_out INT,
    cost_usd DECIMAL(10,6),
    collection_id UUID REFERENCES collections(id),
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE execution_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operation VARCHAR(50),
    status VARCHAR(20),
    duration_ms INT,
    metadata JSONB,
    user_id UUID,
    collection_id UUID,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE error_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level VARCHAR(10),
    source VARCHAR(50),
    message TEXT,
    traceback TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE server_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disk_used_gb DECIMAL(10,2),
    disk_total_gb DECIMAL(10,2),
    ram_used_gb DECIMAL(10,2),
    ram_total_gb DECIMAL(10,2),
    cpu_percent DECIMAL(5,1),
    total_files INT,
    total_chunks INT,
    total_entities INT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE pricing (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(20),
    model VARCHAR(50),
    input_price_per_1m DECIMAL(10,6),
    output_price_per_1m DECIMAL(10,6),
    currency VARCHAR(3) DEFAULT 'USD',
    updated_at TIMESTAMP DEFAULT now()
);
```

## Async SQLAlchemy Pattern
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

DATABASE_URL = "postgresql+asyncpg://user:pass@host:5432/db"

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        yield session
```

## Vector Search Query
```python
from pgvector.sqlalchemy import Vector

async def search_similar(session: AsyncSession, collection_id: UUID, query_embedding: list, top_k: int = 5):
    stmt = (
        select(Chunk)
        .where(Chunk.collection_id == collection_id)
        .order_by(Chunk.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )
    result = await session.execute(stmt)
    return result.scalars().all()
```
