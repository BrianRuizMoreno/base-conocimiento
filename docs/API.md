# Referencia de API

Base URL: `http://localhost:8000/api/v1`

## Autenticación

### Web App (PIN)
```
Header: X-Auth-PIN: 1234
```

### Integración (API Key)
```
Header: X-API-Key: rk_abcdef12
```

---

## Endpoints del Panel Web

### Auth
| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/auth/verify` | Verificar PIN |

```json
// Request
{"pin": "1234"}

// Response
{"success": true, "data": {"role": "admin"}}
```

### Colecciones
| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/collections` | Listar colecciones |
| POST | `/collections` | Crear colección |
| GET | `/collections/{id}` | Ver colección |
| DELETE | `/collections/{id}` | Eliminar colección |

```json
// POST /collections
{"name": "Contabilidad", "description": "Docs del área contable"}

// Response
{"success": true, "data": {"id": "uuid", "name": "Contabilidad"}}
```

### Documentos
| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/collections/{id}/upload` | Subir archivo |
| GET | `/collections/{id}/documents` | Listar documentos |
| DELETE | `/documents/{id}` | Eliminar documento |
| GET | `/documents/{id}/progress` | Progreso de indexación |

```bash
curl -X POST http://localhost:8000/api/v1/collections/abc-123/upload \
  -H "X-Auth-PIN: 1234" \
  -F "file=@documento.pdf"
```

### Chat
| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/collections/{id}/chat` | Chat RAG |

```json
// Request
{
  "question": "¿Qué vende la empresa?",
  "temperature": 0.2,
  "top_p": 0.6
}

// Response
{
  "success": true,
  "data": {
    "answer": "La empresa vende software CRM...",
    "sources": [
      {"filename": "brochure.pdf", "page": 2, "score": 0.89}
    ],
    "related_media": [
      {"type": "image", "url": "/data/abc/img_1.png"}
    ]
  }
}
```

### Análisis
| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/collections/{id}/summary` | Resumen automático |
| GET | `/collections/{id}/analysis` | Análisis predictivo |
| POST | `/collections/{id}/market-compare` | Comparativa de mercado |

### Admin
| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/admin/metrics` | Métricas generales |
| GET | `/admin/tokens` | Uso de tokens |
| GET | `/admin/executions` | Log de ejecuciones |
| GET | `/admin/errors` | Log de errores |
| GET | `/admin/server` | Estado del servidor |

```bash
# Métricas con filtro de tiempo
curl http://localhost:8000/api/v1/admin/metrics?period=24h \
  -H "X-Auth-PIN: 1234"
```

### Settings
| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/settings` | Ver configuración actual |
| PUT | `/settings` | Actualizar configuración |
| GET | `/settings/keys` | Listar API keys guardadas |
| POST | `/settings/keys` | Guardar API key |
| DELETE | `/settings/keys/{provider}` | Eliminar API key |
| GET | `/settings/integration-keys` | Listar keys de integración |
| POST | `/settings/integration-keys` | Crear key de integración |
| DELETE | `/settings/integration-keys/{id}` | Revocar key |

---

## Endpoints de Integración (públicos, API Key)

### Chat
```bash
POST /api/v1/integration/chat/{collection_id}
Content-Type: application/json
X-API-Key: rk_abcdef12

{"question": "¿Qué productos venden?"}
```

### Search
```bash
POST /api/v1/integration/search/{collection_id}
X-API-Key: rk_abcdef12

{"query": "precios competencia", "top_k": 5}
```

### Collections List
```bash
GET /api/v1/integration/collections
X-API-Key: rk_abcdef12
```

### Summary
```bash
GET /api/v1/integration/summary/{collection_id}
X-API-Key: rk_abcdef12
```

### Market Compare
```bash
POST /api/v1/integration/market-compare/{collection_id}
X-API-Key: rk_abcdef12

{
  "query": "¿Cómo nos comparamos con el mercado?",
  "compare_dimensions": ["pricing", "market_share"]
}
```

### Campaign Generate
```bash
POST /api/v1/integration/campaign/generate
X-API-Key: rk_abcdef12

{"collection_id": "abc-123", "campaign_type": "whatsapp"}
```

### Campaign Content
```bash
POST /api/v1/integration/campaign/content
X-API-Key: rk_abcdef12

{"collection_id": "abc-123", "brief": "..."}
```

---

## Formatos de Respuesta

### Éxito
```json
{
  "success": true,
  "data": { ... }
}
```

### Error
```json
{
  "success": false,
  "error": "Mensaje de error",
  "code": "ERR_CODE"
}
```

## Códigos de Error

| Código | Descripción |
|---|---|
| `AUTH_INVALID_PIN` | PIN incorrecto |
| `AUTH_INVALID_API_KEY` | API Key inválida |
| `AUTH_API_KEY_EXPIRED` | API Key expirada |
| `COLLECTION_NOT_FOUND` | Colección no existe |
| `DOCUMENT_NOT_FOUND` | Documento no existe |
| `FILE_TYPE_UNSUPPORTED` | Tipo de archivo no soportado |
| `FILE_TOO_LARGE` | Archivo excede tamaño máximo |
| `LLM_RATE_LIMIT` | Límite de rate del proveedor |
| `LLM_PROVIDER_ERROR` | Error del proveedor LLM |
| `DB_CONNECTION_ERROR` | Error de conexión a PostgreSQL |
