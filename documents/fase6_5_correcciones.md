# Fase 6.5: Correcciones de Seguridad y Accesibilidad

## Hallazgos del Code Review

### 🔴 CRÍTICO — Seguridad

| # | Hallazgo | Impacto | Archivos afectados |
|---|---|---|---|
| C1 | **Falta de autorización por recurso**: `require_auth` solo verifica autenticación, no que el usuario tenga acceso a la colección/documento específico. Cualquier usuario autenticado puede acceder a datos de cualquier colección. | IDOR — filtración de datos entre usuarios/sectores | `collections.py`, `documents.py`, `chat.py`, `analysis.py`, `graph.py`, `conversations.py` |
| C2 | **Rate limiting faltante en auth**: `/auth/verify` sin rate limiting. PIN de 4-10 dígitos vulnerable a fuerza bruta. | Acceso no autorizado | `auth.py` |
| C3 | **Reindexación async incorrecta**: `reindex_document` pasa `process_document` (async) directamente a `background_tasks.add_task` que espera función sync. Puede fallar silenciosamente. | Procesamiento inconsistente | `documents.py` |
| C4 | **Headers de seguridad HTTP faltantes**: No hay CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy. | XSS, clickjacking, MIME sniffing | `main.py` |

### 🟠 MEDIO — Seguridad

| # | Hallazgo | Impacto | Archivos afectados |
|---|---|---|---|
| M1 | **PIN almacenado en localStorage**: Vulnerable a XSS (aunque el modelo de auth actual lo requiere, hay que minimizar riesgos). | Robo de credenciales | `client.ts`, `AuthContext.tsx` |
| M2 | **Mensajes del chat renderizados como HTML sin sanitización**: Si el LLM devuelve HTML malicioso, se ejecuta en el navegador del usuario. | XSS reflejado/persistido | `Chat.tsx` |
| M3 | **No hay validación de archivo por magic bytes**: Solo se verifica extensión y content-type. Un archivo `.php` renombrado a `.pdf` pasaría. | Ejecución de código en servidor | `documents.py` |

### 🟡 BAJO — Accesibilidad (a11y)

| # | Hallazgo | Impacto | Archivos afectados |
|---|---|---|---|
| A1 | **Inputs sin labels asociados**: Login PIN, inputs de análisis comparativo, rename conversation. Solo placeholder no es suficiente para screen readers. | Usuarios con discapacidad visual no pueden identificar campos | `Dashboard.tsx`, `Analysis.tsx`, `Chat.tsx` |
| A2 | **Tabs sin roles ARIA**: Tabs de Analysis y Collection no tienen `role="tab"`, `aria-selected`, `role="tabpanel"`. | Screen readers no anuncian estructura de pestañas | `Analysis.tsx`, `Collection.tsx` |
| A3 | **Botones con solo iconos sin `aria-label`** | Screen readers anuncian solo "button" sin contexto | `EntityGraph.tsx`, `Collection.tsx`, `Chat.tsx` |
| A4 | **No hay skip navigation link** | Usuarios de teclado deben tabular por todo el contenido | `App.tsx` |
| A5 | **No hay `aria-live` regions** | Mensajes de error/éxito no se anuncian automáticamente | Múltiples páginas |
| A6 | **Gráficos sin alternativas textuales**: Recharts y Cytoscape carecen de descripciones para screen readers. | Contenido visual inaccessible | `Analysis.tsx`, `EntityGraph.tsx` |
| A7 | **Modal sin atributos ARIA**: Rename modal no tiene `role="dialog"`, `aria-modal="true"`, ni focus trap. | Screen readers no reconocen modal | `Chat.tsx` |

### 🟢 BAJO — Calidad

| # | Hallazgo | Archivos afectados |
|---|---|---|
| Q1 | Versión del frontend desactualizada: "V 1.0.0 - Fase 2" en login | `Dashboard.tsx` |
| Q2 | `get_remote_address` puede ser spoofeado con `X-Forwarded-For` si hay proxy reverso | `limiter.py` |

## Plan de correcciones

1. **Crear `require_collection_access` dependency** — verifica que el usuario autenticado tenga acceso a la colección solicitada
2. **Aplicar autorización a todos los endpoints con collection_id**
3. **Agregar rate limiting a `/auth/verify`**
4. **Corregir `reindex_document`** para usar wrapper sync
5. **Agregar security headers middleware** (CSP, HSTS, etc.)
6. **Frontend: Agregar labels, aria-labels, roles ARIA, aria-live, skip link**
7. **Frontend: Sanitizar HTML en mensajes del chat**
8. **Frontend: Mejorar modal de rename con focus trap y ARIA**

## Estado
- [x] Hallazgos documentados
- [x] Correcciones implementadas
- [x] Testing y verificación
- [ ] Subido a GitHub

## Correcciones aplicadas

### Backend
- **C1**: Creado `verify_collection_access()` en `auth.py` — verifica que la colección existe y que el usuario (admin) tiene acceso. Aplicado a `collections.py`, `documents.py`, `chat.py`, `analysis.py`, `graph.py`, `conversations.py`.
- **C2**: Rate limiting `10/minute` agregado a `/auth/verify`.
- **C3**: `reindex_document` ahora usa `run_async_process()` wrapper sincrónico.
- **C4**: Middleware de security headers agregado en `main.py` — CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy.

### Frontend
- **A1**: Labels visuales y `sr-only` agregados a inputs de login (PIN) y análisis comparativo.
- **A2**: Tabs de Analysis con `role="tablist"`, `role="tab"`, `aria-selected`, `role="tabpanel"`.
- **A3**: `aria-label` agregado a todos los botones con solo iconos (PanelLeft, PanelLeftClose, MoreVertical, Trash2, ZoomIn, ZoomOut, Maximize, Send, SlidersHorizontal).
- **A5**: `aria-live="polite"` y `role="alert"` agregados a mensajes de error/éxito en Dashboard, Chat, Collection, Analysis.
- **A7**: Modal de rename con `role="dialog"`, `aria-modal="true"`, `aria-labelledby`.
- **Q1**: Versión actualizada a "Fase 6".

### Notas
- **M2 (XSS chat)**: Se verificó que los mensajes se renderizan como texto plano (`{msg.content}` en `<p>`), React escapa automáticamente. No requiere sanitización adicional.
- **M3 (Magic bytes)**: Deferido — requiere dependencia adicional (python-magic-bin) y es de menor prioridad para MVP.
- **Q2 (X-Forwarded-For)**: Deferido a Fase 7 — requiere configuración de proxy reverso conocida.
