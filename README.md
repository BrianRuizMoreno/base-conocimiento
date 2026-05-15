# Sistema RAG Multi-documento

Sistema de conocimiento empresarial con RAG (Retrieval-Augmented Generation) que permite subir documentos en múltiples formatos, vectorizarlos, y chatear con la información. Incluye panel de administración, análisis predictivo, comparativa de mercado, e integración con n8n para WhatsApp.

## Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2.0 |
| Frontend | React 18 + Vite + TypeScript + Tailwind CSS |
| Vector DB | PostgreSQL + pgvector |
| OCR | Gemini 2.0 Flash (fallback a 2.5 Flash) |
| Transcripción | faster-whisper (local, CPU) |
| Embeddings | Gemini text-embedding-004 / OpenAI |
| Chat LLM | Gemini / OpenAI / Anthropic (configurable) |
| Web Search | Tavily |
| Container | Docker + Docker Compose + Portainer |

## Características

- **Formatos soportados**: PDF, DOCX, MD, JSON, XML, JPG, PNG, MP3, MP4
- **Sin límite de tamaño**: Streaming y chunking progresivo
- **Grafo de entidades**: Entidades + relaciones en PostgreSQL
- **Multi-tenant**: Schema listo para usuarios por departamento
- **Admin Panel**: Métricas, tokens, costos, espacio, errores, ejecuciones
- **Modo oscuro**: Toggle en header
- **Integración n8n**: API keys scoped para WhatsApp y campañas
- **Costo mensual**: $0 (capas gratuitas + procesamiento local)

## Estructura

```
rag-system/
├── .codex/skills/        # Skills para AI assistants
├── .codex/agents/        # Agents para tareas específicas
├── docs/                 # Documentación
├── backend/              # FastAPI
├── frontend/             # React + Vite
├── docker-compose.yml
└── .env.example
```

## Inicio Rápido

1. Copiar `.env.example` a `.env` y completar variables
2. Generar hash del PIN de admin: `python -c "import bcrypt; print(bcrypt.hashpw(b'1234', bcrypt.gensalt()).decode())"`
3. Ejecutar: `docker-compose up -d`
4. Acceder: http://localhost:3000

## Documentación

- [CONFIGURACION.md](docs/CONFIGURACION.md) — Manual de configuración
- [API.md](docs/API.md) — Referencia de endpoints
- [ARQUITECTURA.md](docs/ARQUITECTURA.md) — Decisiones técnicas
- [DESPLIEGUE.md](docs/DESPLIEGUE.md) — Guía de despliegue
- [INTEGRACION_N8N.md](docs/INTEGRACION_N8N.md) — Conexión con n8n

## Licencia

MIT
