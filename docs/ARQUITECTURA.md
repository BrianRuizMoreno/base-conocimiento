# Arquitectura del Sistema

## Visión General

El sistema es un **Glean self-hosted** — un motor de conocimiento empresarial con RAG, grafo de entidades, y análisis predictivo.

```
┌──────────────────────────────────────────────────────────────────┐
│                         USUARIO                                   │
│  [Web App] ←──→ [WhatsApp Bot] ←──→ [n8n Workflows]            │
└────────────────┬────────────────────┬────────────────────────────┘
                 │                    │
                 ▼                    ▼
┌──────────────────────────────────────────────────────────────────┐
│  FRONTEND (React + Vite + Tailwind)                              │
│  ─────────────────────────────────────                           │
│  Dashboard │ Upload │ Chat │ Analysis │ Admin Panel              │
│  Dark Mode │ Tabs   │ Images │ Graph Viz │ Settings              │
└────────────────┬─────────────────────────────────────────────────┘
                 │ HTTP/JSON
                 ▼
┌──────────────────────────────────────────────────────────────────┐
│  BACKEND (FastAPI + Python 3.12)                                 │
│  ─────────────────────────────────────                           │
│  Auth │ Collections │ Documents │ Chat │ Analysis │ Admin        │
│  Integration API (n8n/bots)                                       │
└────────────────┬─────────────────────────────────────────────────┘
                 │ SQLAlchemy Async
                 ▼
┌──────────────────────────────────────────────────────────────────┐
│  DATA LAYER                                                       │
│  ─────────────────────────────────────                           │
│  PostgreSQL + pgvector │ Entities │ Relationships │ Metrics Logs │
└──────────────────────────────────────────────────────────────────┘
```

## Decisiones de Arquitectura

### 1. PostgreSQL + pgvector vs ChromaDB/Qdrant

**Elegido: PostgreSQL + pgvector**

| Criterio | PostgreSQL + pgvector | ChromaDB | Qdrant |
|---|---|---|---|
| Ya existente | ✅ Sí | ❌ No | ❌ No |
| ACID transactions | ✅ Sí | ⚠️ Parcial | ✅ Sí |
| Relaciones SQL | ✅ Nativo | ❌ No | ❌ No |
| Grafo entidades | ✅ Tablas SQL | ❌ No | ❌ No |
| Escalabilidad | ✅ Alta | ⚠️ Media | ✅ Alta |
| Costo | ✅ $0 | ✅ $0 | ✅ $0 |

**Conclusión:** Ya tienes PostgreSQL en tu VPS. pgvector añade vectores sin nuevo contenedor. Las relaciones SQL nativas permiten el grafo híbrido sin Neo4j.

### 2. Gemini como proveedor principal

**Elegido: Google Gemini (capa gratuita)**

| Proveedor | OCR | Chat | Embeddings | Costo |
|---|---|---|---|---|
| Gemini | ✅ Gratis | ✅ Gratis | ✅ Gratis | **$0** |
| OpenAI | ✅ Pago | ✅ Pago | ✅ Pago | $$$ |
| Anthropic | ❌ No | ✅ Pago | ❌ No | $$ |

**Conclusión:** Gemini ofrece OCR + chat + embeddings en capa gratuita. Perfecto para empezar. Los demás proveedores son opcionales (fallback).

### 3. Whisper local vs API

**Elegido: faster-whisper local**

| Opción | Costo | Calidad | Requisitos |
|---|---|---|---|
| faster-whisper local | **$0** | Buena | 2GB RAM |
| OpenAI Whisper API | $0.006/min | Excelente | Internet |

**Conclusión:** Con 8GB RAM en tu VPS, el modelo "base" o "small" de Whisper corre sin problemas en CPU. $0 de costo.

### 4. Grafo híbrido vs GraphRAG puro

**Elegido: Grafo híbrido en PostgreSQL**

| Opción | Complejidad | RAM | Precisión |
|---|---|---|---|
| Grafo en PostgreSQL | Media | +200MB | 85-92% |
| GraphRAG (Neo4j) | Alta | +2GB | 90-95% |
| Solo vector | Baja | +0MB | 65-75% |

**Conclusión:** El grafo en PostgreSQL (2 tablas extra) da 85-92% de precisión sin añadir un nuevo contenedor. Es el sweet spot para tu hardware.

### 5. FastAPI vs Django/Flask

**Elegido: FastAPI**

| Framework | Async | Type Safety | Performance | Ecosistema AI |
|---|---|---|---|---|
| FastAPI | ✅ Nativo | ✅ Pydantic | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Django | ⚠️ Channels | ✅ Models | ⭐⭐⭐ | ⭐⭐⭐ |
| Flask | ❌ No | ⚠️ Manual | ⭐⭐⭐ | ⭐⭐⭐ |

**Conclusión:** FastAPI es el estándar para backends AI. Async nativo, OpenAPI auto-generado, perfecto para integraciones.

### 6. React + Vite vs Next.js

**Elegido: React + Vite**

| Framework | SSR | Build Speed | Size | Necesidad |
|---|---|---|---|---|
| React + Vite | ❌ No | ⭐⭐⭐⭐⭐ | Pequeño | SPA simple |
| Next.js | ✅ Sí | ⭐⭐⭐ | Grande | SEO, SSR |

**Conclusión:** Es una app interna/admin. No necesita SEO ni SSR. Vite es más rápido y ligero.

## Flujo de Datos

### Upload de Documento
```
[Usuario sube archivo]
    ↓
[Frontend] → POST /api/v1/collections/{id}/upload
    ↓
[Backend] Guarda en /data/
    ↓
[Parser] Detecta tipo → extrae texto
    ↓
[Chunking] Divide en segmentos de 1500 tokens con 200 overlap
    ↓
[Embedding] Genera vectores (con hash cache)
    ↓
[pgvector] Almacena chunks + embeddings
    ↓
[Entity Extraction] Extrae entidades y relaciones (batch)
    ↓
[PostgreSQL] Almacena en entities + relationships
    ↓
[Response] Devuelve status + progreso
```

### Chat RAG
```
[Usuario pregunta]
    ↓
[Backend] Recibe pregunta + config (temp, top_p)
    ↓
[Query Expansion] Añade términos del grafo
    ↓
[HyDE - opcional] Genera respuesta hipotética si baja confianza
    ↓
[Vector Search] Top-20 chunks similares (cosine)
    ↓
[Graph Search] Top-10 chunks relacionados por entidades
    ↓
[Fusion] Combina y deduplica resultados
    ↓
[Rerank] Cross-encoder local reordena → top-5
    ↓
[Context Builder] Arma contexto con fuentes
    ↓
[LLM] Genera respuesta con sistema prompt
    ↓
[Response] Devuelve respuesta + fuentes + imágenes relacionadas
    ↓
[Log] Guarda tokens usados en token_usage
```

## Seguridad

### Autenticación
- PIN bcrypt hasheado (admin)
- API Keys con prefix + hash (integraciones)
- API Keys scoped a colecciones específicas

### Autorización
- Admin: acceso a todo
- Usuario futuro: solo colecciones asignadas en `collection_access`
- Integration Key: solo colecciones en `scoped_collections`

### Datos Sensibles
- API Keys encriptadas con Fernet (AES-128)
- Nunca expuestas en logs ni respuestas
- Archivos subidos en volumen Docker (`/data/`)

## Escalabilidad Futura

### Fase 1 (ahora)
- 1 admin, 50-500 docs
- Todo en un VPS

### Fase 2 (futuro)
- Multi-usuario por departamento
- Workers separados para procesamiento en background (Celery)

### Fase 3 (futuro)
- Replicación PostgreSQL
- CDN para archivos estáticos
- Caché Redis para queries frecuentes
