# PLANIFICACIÓN RAG SYSTEM (v2.1)

## Visión General

Sistema de conocimiento empresarial con RAG multi-documento para **una empresa**, desplegado en un VPS Hostinger (8GB RAM, 100GB SSD, 2 cores). Chat conversacional con historial, grafo de entidades, análisis predictivo, comparativa web, gestión de fuentes editables, e integración con n8n. **Diseño responsive obligatorio en todas las vistas.**

**Stack:** FastAPI + React 18/Vite + Tailwind CSS + PostgreSQL/pgvector + Gemini + Whisper

---

## Requisitos Transversales (todas las fases)

- **Diseño responsive obligatorio:** mobile-first, todas las vistas deben funcionar en móvil, tablet y desktop
- **Modelo IA preestablecido:** Gemini 2.5 Flash (última versión disponible de Gemini Flash)
- **Particionado:** archivos >20MB se dividen en chunks adaptativos
- **Gestión de fuentes:** cualquier documento indexado debe poder eliminarse o modificarse (re-indexar)
- **Idioma:** toda la interfaz en español

---

## Fase 1: Configuración Persistente y Multi-proveedor IA

**Objetivo:** Que el panel de configuración guarde realmente las API keys y que el sistema use múltiples proveedores con fallback automático.

### Tareas Backend
| # | Tarea | Descripción |
|---|---|---|
| 1.1 | Tabla `provider_keys` | Almacenar API keys encriptadas (Fernet AES-128) para cada proveedor (Gemini, OpenAI, Anthropic) |
| 1.2 | Refactorizar `settings.py` | Todos los endpoints leen/escriben de DB, no de memoria/env |
| 1.3 | Motor multi-proveedor | Lógica de fallback: intenta Gemini API key #1 → #2 → #3, luego OpenAI, luego Anthropic |
| 1.4 | Selector de modelo dinámico | El chat acepta parámetro `model` y selecciona el proveedor correspondiente |
| 1.5 | Logging de `TokenUsage` | Escribir en DB cada llamada LLM (tokens in/out, costo estimado, modelo usado) |
| 1.6 | Logging de `ErrorLog` | Escribir en DB errores de proveedores LLM para debugging |

### Tareas Frontend
| # | Tarea | Descripción |
|---|---|---|
| 1.7 | Settings wiring | Formularios del admin que persisten al guardar (ya tiene UI, falta wiring) |
| 1.8 | Indicador de proveedor | Badge en el chat mostrando qué modelo/proveedor está activo |
| 1.9 | Configuración de chat | Selector de modelo, temperatura (0-2), top_p (0-1) desde el panel y desde el chat |

### Criterios de Aceptación
- [x] Se configuran 3 API keys de Gemini y el sistema hace fallback si una falla
- [x] Cambiar modelo/temperatura/top_p desde el panel → se refleja instantáneamente en el chat
- [x] `TokenUsage` registra cada request al LLM con tokens y costo

---

## Fase 2: Ingesta Completa de Documentos

**Objetivo:** Procesar TODOS los formatos declarados (imágenes, audio, video, PDF/DOCX con imágenes), con particionado a 20MB, y servir imágenes extraídas.

### Tareas Backend
| # | Tarea | Descripción |
|---|---|---|
| 2.1 | OCR de imágenes | `.jpg`, `.png`, `.webp` → Gemini 2.5 Flash extrae texto. Imagen original se almacena en `/data/images/` |
| 2.2 | Extraer imágenes de PDF | PyMuPDF extrae imágenes incrustadas → almacenarlas en `/data/images/{collection_id}/{doc_id}/` |
| 2.3 | Extraer imágenes de DOCX | python-docx + extracción de relaciones de imagen → mismo destino |
| 2.4 | Transcripción de audio/video | `.mp3`, `.mp4`, `.wav`, `.ogg` → faster-whisper (modelo base, CPU) → texto |
| 2.5 | Servir imágenes estáticas | Endpoint `/api/v1/data/images/{path}` con cache headers |
| 2.6 | Particionado a 20MB | Archivos >20MB → división en chunks más pequeños antes de procesar |
| 2.7 | Indexar imágenes en vector store | Cada imagen guarda: embedding de su descripción + referencia `image_url` en metadata del chunk |

### Tareas Frontend
| # | Tarea | Descripción |
|---|---|---|
| 2.8 | Thumbnails de documentos | Mostrar preview de imagen si el documento es imagen o contiene imágenes |
| 2.9 | Indicador de tipo | Iconos visuales para cada tipo de archivo (PDF, imagen, audio, video, DOCX, etc.) |
| 2.10 | Galería de imágenes | Vista de imágenes extraídas por colección |

### Criterios de Aceptación
- [x] Subir un `.jpg` con texto → se indexa y se puede preguntar por ese texto
- [x] Subir un PDF con imágenes → las imágenes se extraen, almacenan y sirven vía API
- [x] Subir un `.mp3` → se transcribe y el texto es consultable
- [x] Archivo de 50MB se particiona automáticamente en chunks sin timeout

---

## Fase 3: Chat RAG Conversacional Avanzado

**Objetivo:** Chat multi-sesión con historial persistido, web search opcional vía Tavily, retorno de imágenes relevantes, y eliminación/modificación de fuentes.

### Tareas Backend
| # | Tarea | Descripción |
|---|---|---|
| 3.1 | Modelo `Conversation` y `Message` | Tablas en DB: id, collection_id, title, created_at, mensajes con rol + contenido + fuentes |
| 3.2 | CRUD de conversaciones | `GET /conversations` (listar), `POST /conversations` (crear), `DELETE /conversations/{id}`, `PATCH /conversations/{id}` (renombrar) |
| 3.3 | Historial como contexto | Últimos N mensajes incluidos en el prompt del LLM para mantener coherencia |
| 3.4 | Toggle web search | Parámetro `web_search: bool` → si true, consulta Tavily y añade resultados al contexto del prompt |
| 3.5 | Retorno de imágenes relevantes | Si los chunks recuperados tienen `image_url` en metadata → incluir en respuesta |
| 3.6 | Eliminar fuente de información | `DELETE /documents/{id}` → elimina documento, chunks, entidades asociadas y archivos físicos |
| 3.7 | Modificar fuente | `POST /documents/{id}/reindex` → re-procesa un documento existente (útil si cambió el archivo o la configuración) |

### Tareas Frontend
| # | Tarea | Descripción |
|---|---|---|
| 3.8 | Sidebar de conversaciones | Lista de sesiones con título, botón "+" nueva conversación, menú contextual (renombrar, eliminar) |
| 3.9 | Historial scrollable | Carga de mensajes anteriores al hacer scroll hacia arriba (paginación) |
| 3.10 | Toggle "Buscar en Internet" | Switch en el header del chat que activa/desactiva Tavily |
| 3.11 | Imágenes en respuestas | Renderizar imágenes inline en los mensajes del asistente cuando aplique |
| 3.12 | Título automático | Usar el LLM para generar un título descriptivo basado en el primer mensaje del usuario |
| 3.13 | Gestión de fuentes | Botón "Eliminar" y "Re-indexar" en cada documento de la colección |

### Criterios de Aceptación
- [x] 3 conversaciones abiertas, cada una mantiene su historial independiente
- [x] Web search activado → respuestas citan fuentes externas (Tavily)
- [x] "Muéstrame la imagen del brochure" → devuelve imagen embebida en el chat
- [x] Eliminar un documento → sus chunks e imágenes desaparecen; el chat ya no lo referencia
- [x] Re-indexar un documento actualizado → nuevos chunks reemplazan los viejos

---

## Fase 4: Grafo de Entidades y Visualización

**Objetivo:** Extraer entidades y relaciones de los documentos, integrar búsqueda híbrida (vector + grafo), visualizar el grafo en el panel admin y en cada colección.

### Tareas Backend
| # | Tarea | Descripción |
|---|---|---|
| 4.1 | Pipeline de extracción | Enviar chunks a Gemini con prompt estructurado (definido en `ENTIDADES_GRAFO.md`) → entidades + relaciones en JSON |
| 4.2 | Deduplicación | Entidades con mismo nombre + tipo + colección → se mergean, no se duplican |
| 4.3 | Almacenamiento | Tablas `entities` y `relationships` pobladas automáticamente post-indexación |
| 4.4 | Búsqueda híbrida | Vector search (top-20) + Graph search (chunks relacionados por entidad) → fusión + rerank → top-5 |
| 4.5 | Endpoint del grafo | `GET /collections/{id}/graph` → nodos y aristas en formato compatible con Cytoscape |
| 4.6 | Regeneración | `POST /collections/{id}/regenerate-graph` → re-procesa extracción para toda la colección |

### Tareas Frontend
| # | Tarea | Descripción |
|---|---|---|
| 4.7 | Componente `GrafoEntidades` | Visualización interactiva con Cytoscape.js (zoom, drag, click en nodo → info) |
| 4.8 | Pestaña "Grafo" | En cada colección, pestaña dedicada al grafo de entidades |
| 4.9 | Grafo en panel admin | Vista consolidada en el admin mostrando el grafo global |

### Criterios de Aceptación
- [x] Indexar un documento con empresas, productos → entidades extraídas automáticamente
- [x] Grafo interactivo renderizado correctamente (nodos coloreados por tipo)
- [x] "¿Quién compite con X?" → usa búsqueda híbrida vector + grafo, respuesta más precisa

---

## Fase 5: Análisis Predictivo y Comparativa de Mercado

**Objetivo:** Implementar análisis reales (no placeholders) usando LLM + Tavily, con gráficos interactivos.

### Tareas Backend
| # | Tarea | Descripción |
|---|---|---|
| 5.1 | Resumen automático | `GET /collections/{id}/summary` → Gemini analiza todos los chunks y genera resumen + entidades clave + tópicos |
| 5.2 | Análisis predictivo | `GET /collections/{id}/analysis` → extraer métricas numéricas de los documentos, identificar tendencias, generar predicciones |
| 5.3 | Comparativa de mercado | `POST /collections/{id}/market-compare` → datos internos vs búsqueda Tavily, respuesta estructurada con fuentes |
| 5.4 | Rate limiting | Aplicar slowapi (5 req/min en endpoints de análisis, 20 req/min en chat) |

### Tareas Frontend
| # | Tarea | Descripción |
|---|---|---|
| 5.5 | Gráficos de tendencias | Recharts: líneas de tendencia, barras comparativas en "Análisis Predictivo" |
| 5.6 | Tabla comparativa | "Comparativa de Mercado" muestra tabla estructurada (dimensión, dato interno, dato externo, fuente) |
| 5.7 | Tags clickeables | Entidades y tópicos en los resúmenes son clickeables → abren búsqueda relacionada |

### Criterios de Aceptación
- [x] Resumen automático genera texto coherente + entidades + tópicos relevantes
- [x] Análisis predictivo muestra gráficos de líneas/barras con datos reales extraídos
- [x] Comparativa de mercado enfrenta datos internos con búsqueda web de Tavily

---

## Fase 6: Integración n8n y API Externa

**Objetivo:** Implementar los 7 endpoints de integración con autenticación real por API key, webhooks a n8n.

### Tareas Backend
| # | Tarea | Descripción |
|---|---|---|
| 6.1 | `POST /integration/chat/{id}` | Mismo motor RAG que el chat del panel, autenticado con `X-API-Key` |
| 6.2 | `POST /integration/search/{id}` | Búsqueda vectorial pura (top_k configurable, sin LLM) |
| 6.3 | `GET /integration/collections` | Listar colecciones reales con su id, nombre, sector |
| 6.4 | `GET /integration/summary/{id}` | Llamar al motor de análisis (Fase 5) |
| 6.5 | `POST /integration/market-compare/{id}` | Llamar al motor de comparativa (Fase 5) |
| 6.6 | `POST /integration/campaign/generate` | Gemini genera brief de campaña basado en contenido de la colección |
| 6.7 | `POST /integration/campaign/content` | Generar headline, body, CTA, segmentación para el brief |
| 6.8 | Webhooks a n8n | Notificar `document_indexed`, `document_error`, `chat_low_confidence` → POST al `N8N_WEBHOOK_URL` |

### Criterios de Aceptación
- [x] Workflow de n8n chatea contra una colección con `X-API-Key` → respuesta real del RAG
- [x] Al indexar un documento → n8n recibe webhook `document_indexed` con metadata
- [x] Generar campaña devuelve headline, body, CTA y segmentación basados en datos reales

---

## Fase 7: Sectores y Panel Admin Completo

**Objetivo:** Control de acceso por sector de la empresa, gráficos completos en el admin, visualización del grafo, y pulido final responsive.

### Tareas Backend
| # | Tarea | Descripción |
|---|---|---|
| 7.1 | Modelo `Sector` | Tabla: id, name, slug, description, created_at |
| 7.2 | Vinculación colección-sector | `collection.sector_id` → cada colección pertenece a un sector |
| 7.3 | Tokens de sector | Generar tokens `st_xxxx` scoped a un sector específico |
| 7.4 | Middleware de autorización | Verificar token → limitar queries solo a colecciones del sector autorizado |
| 7.5 | CRUD de sectores | `GET/POST/PATCH/DELETE /admin/sectors` → solo super admin |
| 7.6 | Completar logging | `TokenUsage`, `ExecutionLog`, `ErrorLog` escritos en TODAS las operaciones restantes |

### Tareas Frontend
| # | Tarea | Descripción |
|---|---|---|
| 7.7 | Gráficos del dashboard | Recharts en admin dashboard: tokens/día, docs procesados, errores (líneas y barras) |
| 7.8 | Gestión de sectores | UI para crear/editar/eliminar sectores, asignar colecciones, generar tokens |
| 7.9 | Grafo en admin | Pestaña "Grafo" en el panel admin (aprovecha componente de Fase 4) |
| 7.10 | Filtros funcionales | Selector de período (24h/7d/30d/All) con datos reales en todas las tabs |
| 7.11 | Corrección de navegación | Reemplazar `<a href>` por `<Link>` de react-router en todo el frontend |
| 7.12 | Limpieza de dependencias | Implementar o eliminar `clsx`, `tailwind-merge`, `__init__.py` extraviado |

### Criterios de Aceptación
- [ ] Token del sector "Ventas" → solo ve colecciones de Ventas en la UI y API
- [ ] Super admin ve y gestiona todos los sectores
- [ ] Dashboard admin muestra gráficos de tendencias, no solo tablas
- [ ] El grafo de entidades se visualiza en el panel admin
- [ ] Todas las vistas son completamente responsive (móvil, tablet, desktop)

---

## Resumen de Fases

| Fase | Nombre | Estado Actual | Prioridad | Depende de | Tareas |
|---|---|---|---|---|---|
| **1** | Multi-proveedor + Config Persistente | 100% | **Alta** | — | 9 |
| **2** | Ingesta Completa | 100% | **Alta** | — | 10 |
| **3** | Chat Conversacional Avanzado | 100% | **Alta** | F1, F2 | 13 |
| **4** | Grafo de Entidades | 100% | **Media** | F2 | 9 |
| **5** | Análisis y Comparativa | 10% (placeholders) | **Media** | F1 | 7 |
| **6** | Integración n8n | 10% (placeholders) | **Baja** | F3, F5 | 8 |
| **7** | Sectores + Admin Completo | 50% (admin parcial) | **Media** | F4 | 12 |

**Total: ~68 tareas**

---

## Orden de Ejecución Recomendado

```
Fase 1 ──→ Fase 3 ──→ Fase 6
    │
    └──→ Fase 5

Fase 2 ──→ Fase 3
    │
    └──→ Fase 4 ──→ Fase 7
```

**F1 + F2** en paralelo → **F3** las integra → **F4** (grafo) y **F5** (análisis) en paralelo → **F6** (n8n) + **F7** (sectores/admin final)

---

## Estado de la ejecución

| Fase | Estado | Progreso |
|---|---|---|
| Fase 1 | ✅ Completada | 100% |
| Fase 2 | ✅ Completada | 100% |
| Fase 3 | ✅ Completada | 100% |
| Fase 4 | ✅ Completada | 100% |
| Fase 5 | ⏳ Pendiente | 0% |
| Fase 6 | ⏳ Pendiente | 0% |
| Fase 7 | ⏳ Pendiente | 0% |

*Última actualización: en ejecución*
