# Log de Ejecucion - Fase 3: Chat RAG Conversacional Avanzado

**Fecha inicio:** 2026-05-16  
**Fecha completada:** 2026-05-16  
**Estado:** Completada

---

## Tareas completadas

- [x] 3.1 Modelos Conversation y Message en DB
- [x] 3.2 Endpoints CRUD de conversaciones (crear, listar, obtener, renombrar, eliminar)
- [x] 3.3 Chat con historial persistido (ultimos 6 mensajes como contexto)
- [x] 3.4 Titulo automatico de conversacion con LLM
- [x] 3.5 Toggle web search (Tavily) en chat
- [x] 3.6 Frontend: sidebar de conversaciones con gestion completa
- [x] 3.7 Frontend: toggle "Buscar en Internet" en header del chat
- [x] 3.8 Frontend: carga de mensajes previos al seleccionar conversacion

---

## Archivos creados/modificados

### Backend - Nuevos archivos

| Archivo | Descripcion |
|---|---|
| `app/api/conversations.py` | Endpoints CRUD: POST/GET/PATCH/DELETE /conversations. Listado filtrable por collection_id. Obtencion con mensajes incluidos. |
| `app/search/web_search.py` | Integracion Tavily API. Funciones `search_web()` y `format_web_results()` para incluir resultados web en el contexto del prompt. |
| `alembic/versions/003_conversations_and_messages.py` | Migracion que crea tablas `conversations` e `messages` con indices. |

### Backend - Modificados

| Archivo | Cambios |
|---|---|
| `app/db/models.py` | Agregados modelos `Conversation` (id, collection_id, title, created_at, updated_at) y `Message` (id, conversation_id, role, content, sources, related_media, model, tokens_used, created_at) |
| `app/api/chat.py` | Acepta `conversation_id` y `web_search` en request. Persiste mensajes en DB. Carga ultimos 6 mensajes como historial. Genera titulo automatico con LLM si es primera interaccion. |
| `app/rag/engine.py` | Integra `history` y `web_search_results` en el prompt. Ejecuta busqueda Tavily cuando `web_search=True`. |
| `app/main.py` | Registrado router de conversaciones en `/api/v1/conversations`. |

### Frontend - Modificado

| Archivo | Cambios |
|---|---|
| `src/pages/Chat.tsx` | **Reescrito** con sidebar izquierdo de conversaciones, boton "Nueva conversacion", menu contextual renombrar/eliminar, toggle "Buscar en Internet", carga de mensajes previos, responsive (drawer en mobile). |

---

## Decisiones tecnicas importantes

1. **Historial limitado a 6 mensajes**: Para no exceder el contexto del LLM y mantener latencia baja.
2. **Titulo automatico**: Se genera con LLM (max 50 tokens, temp 0.3) basado en la primera pregunta. Solo si la conversacion no tiene titulo previo.
3. **Web search como contexto adicional**: Los resultados de Tavily se insertan como un bloque "[Resultados de busqueda web]" en el prompt, junto a los documentos de la coleccion.
4. **Persistencia condicional**: Los mensajes solo se guardan en DB cuando hay un `conversation_id` activo. Chat sin sesion funciona como antes.

---

## Proxima fase

Fase 4: Grafo de Entidades y Visualizacion
- Extraccion de entidades y relaciones de los documentos
- Busqueda hibrida (vector + grafo)
- Visualizacion con Cytoscape.js en el panel admin
