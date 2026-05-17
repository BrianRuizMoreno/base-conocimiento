# Log de Ejecucion - Fase 4: Grafo de Entidades y Visualizacion

**Fecha inicio:** 2026-05-16  
**Fecha completada:** 2026-05-16  
**Estado:** Completada

---

## Tareas completadas

- [x] 4.1 Extraccion de entidades y relaciones con Gemini (prompt estructurado JSON)
- [x] 4.2 Deduplicacion de entidades por nombre+tipo+coleccion
- [x] 4.3 Busqueda hibrida (vector top-20 + grafo + fusion + rerank)
- [x] 4.4 Endpoints REST del grafo (GET /graph, POST /regenerate-graph, GET /entities, GET /related)
- [x] 4.5 Integracion en pipeline de ingesta (extraccion post-chunking)
- [x] 4.6 Visualizacion con Cytoscape.js (nodos coloreados por tipo, layout force-directed)
- [x] 4.7 Pestaña Grafo en admin dashboard
- [x] 4.8 Pestaña Grafo en vista de coleccion

---

## Archivos creados/modificados

### Backend - Nuevos archivos

| Archivo | Descripcion |
|---|---|
| `app/graph/extractor.py` | Extraccion de entidades/relaciones de chunks con Gemini. Prompt estructurado en JSON. Deduplicacion defensiva. Manejo de errores con rollback parcial. |
| `app/graph/search.py` | Busqueda hibrida: vector search (top-20) + graph search (entidades en query) + fusion + rerank simple. Retorna top-5 chunks. |
| `app/api/graph.py` | Endpoints: GET /collections/global/graph, GET /collections/{id}/graph, POST /collections/{id}/regenerate-graph, GET /collections/{id}/entities, GET /entities/{id}/related. Formato Cytoscape. |

### Backend - Modificados

| Archivo | Cambios |
|---|---|
| `app/ingestion/pipeline.py` | Llama al extractor despues de chunking. Guarda entity_ids en metadata de chunks. |
| `app/rag/engine.py` | Agrega parametro `use_graph: bool = False`. Si true, usa hybrid_search en vez de search_chunks puro. |
| `app/api/chat.py` | Expone `use_graph` en el request body del chat. |
| `app/main.py` | Registrado router de grafo. |

### Frontend - Nuevos archivos

| Archivo | Descripcion |
|---|---|
| `src/components/EntityGraph.tsx` | Visualizacion interactiva con react-cytoscapejs. Layout cose (force-directed). Nodos coloreados por tipo con leyenda. Zoom, pan, fit. Click en nodo muestra info. Responsive. |

### Frontend - Modificados

| Archivo | Cambios |
|---|---|
| `src/pages/admin/AdminDashboard.tsx` | Agregada pestaña "Grafo" mostrando grafo global. |
| `src/pages/Collection.tsx` | Agregada pestaña "Grafo de Entidades" mostrando grafo de la coleccion actual. |

---

## Decisiones tecnicas importantes

1. **Relacion chunk-entidad via metadata**: En vez de crear tabla de union, los `entity_ids` se guardan en el campo `metadata` (JSONB) del chunk. Simplifica el esquema y permite busqueda hibrida sin migraciones adicionales.
2. **Extraccion durante ingesta**: Se ejecuta chunk por chunk para maximizar contexto local y no exceder limites de tokens de Gemini.
3. **Deduplicacion defensiva**: El extractor maneja fallos individuales de entidad/relacion con rollback parcial, evitando que un error deje el documento sin procesar.
4. **Sin migracion necesaria**: Las tablas `entities` y `relationships` ya existian en la migracion 001_initial.py. No se modifico su estructura.

---

## Proxima fase

Fase 5: Analisis Predictivo y Comparativa de Mercado
- Resumenes automaticos de coleccion
- Analisis de tendencias con metricas numericas
- Comparativa de mercado con Tavily web search
- Gráficos con Recharts en el panel de analisis
