---
name: n8n-integration
description: Integration patterns for connecting the RAG system with n8n workflows. WhatsApp bot via YCloud node, campaign automation, webhook triggers. API key scoped endpoints.
---

# n8n Integration Patterns

## API Key for n8n
1. Admin creates Integration Key in Settings → scoped to specific collections
2. Copy key to n8n HTTP Request node header `X-API-Key`

## n8n Workflow: WhatsApp Bot
```
[Webhook Trigger] ← recibe mensaje de WhatsApp (YCloud)
    ↓
[HTTP Request] GET /api/v1/integration/collections
    Headers: X-API-Key: rk_abcdef12
    ↓
[If] ¿Mensaje contiene nombre de colección?
    ↓ Sí
[Set] collection_id = ID de la colección
    ↓
[HTTP Request] POST /api/v1/integration/chat/{collection_id}
    Body: { "question": "{{ $json.body.message }}" }
    ↓
[YCloud WhatsApp] Enviar respuesta al usuario
    Body: {{ $json.response.answer }}
    ↓
[Optional] Si respuesta tiene related_media
    [YCloud WhatsApp] Enviar imagen adjunta
```

## n8n Workflow: Campaign Generation
```
[Manual Trigger / Schedule]
    ↓
[HTTP Request] POST /api/v1/integration/campaign/generate
    Body: { "collection_id": "abc-123", "campaign_type": "whatsapp" }
    ↓
[HTTP Request] POST /api/v1/integration/campaign/content
    Body: { "collection_id": "abc-123", "brief": "{{ $json.brief }}" }
    ↓
[Google Sheets] Guardar copys en spreadsheet
    ↓
[YCloud WhatsApp] Enviar preview de campaña a admin
```

## Integration API Endpoints

### Chat
```bash
curl -X POST https://your-api.com/api/v1/integration/chat/abc-123 \
  -H "X-API-Key: rk_abcdef12" \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Qué productos vende la empresa?"}'
```

Response:
```json
{
  "success": true,
  "data": {
    "answer": "La empresa vende software CRM...",
    "sources": [
      {"filename": "brochure.pdf", "page": 2}
    ],
    "related_media": [
      {"type": "image", "url": "/data/abc/img_1.png"}
    ]
  }
}
```

### Search Only
```bash
curl -X POST https://your-api.com/api/v1/integration/search/abc-123 \
  -H "X-API-Key: rk_abcdef12" \
  -d '{"query": "precios competencia", "top_k": 5}'
```

### Market Compare (Web Search)
```bash
curl -X POST https://your-api.com/api/v1/integration/market-compare/abc-123 \
  -H "X-API-Key: rk_abcdef12" \
  -d '{
    "query": "¿Cómo se compara mi empresa con el mercado?",
    "compare_dimensions": ["pricing", "market_share"]
  }'
```

### Collections List
```bash
curl https://your-api.com/api/v1/integration/collections \
  -H "X-API-Key: rk_abcdef12"
```

## Webhook from RAG to n8n
```python
# Trigger n8n webhook when document finishes indexing
async def notify_n8n_webhook(collection_id: UUID, document_id: UUID, status: str):
    webhook_url = os.getenv("N8N_WEBHOOK_URL")
    if not webhook_url:
        return
    
    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json={
            "event": "document_indexed",
            "collection_id": str(collection_id),
            "document_id": str(document_id),
            "status": status
        })
```

## Error Handling in n8n
- If RAG API returns 429 (rate limit): n8n waits 60s and retries
- If RAG API returns 500: n8n logs error, sends alert to admin
- If no relevant chunks found: return "No tengo información sobre eso en esta colección."
