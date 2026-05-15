# Integración con n8n

## Visión General

El sistema expone endpoints de integración que n8n puede consumir mediante el nodo **HTTP Request**.

## Configuración Inicial

### 1. Crear API Key de Integración

En el panel de admin:
1. Ve a **Configuración** → **API Keys de Integración**
2. Click **Generar Nueva Key**
3. Selecciona las colecciones a las que tendrá acceso
4. Copia la key (formato: `rk_abcdef12...`)

### 2. Configurar n8n

En n8n, crea un **Credential** tipo **Header Auth**:
- **Name**: `X-API-Key`
- **Value**: `rk_abcdef12...`

## Workflows de Ejemplo

### Workflow 1: Bot WhatsApp con YCloud

```
[Webhook Trigger] 
  URL: https://tu-n8n.com/webhook/whatsapp
  Method: POST
    ↓
[HTTP Request]
  Method: GET
  URL: http://tu-vps:8000/api/v1/integration/collections
  Authentication: Header Auth (X-API-Key)
    ↓
[Code Node] 
  // Extraer collection_id del mensaje o usar default
  return { collection_id: "abc-123" }
    ↓
[HTTP Request]
  Method: POST
  URL: http://tu-vps:8000/api/v1/integration/chat/{{ $json.collection_id }}
  Body: {
    "question": "{{ $json.body.message }}"
  }
    ↓
[YCloud WhatsApp]
  To: {{ $json.body.from }}
  Body: {{ $json.data.answer }}
    ↓
[If] ¿Tiene imágenes relacionadas?
    ↓ Sí
[HTTP Request]
  Method: GET
  URL: http://tu-vps:8000{{ $json.data.related_media[0].url }}
    ↓
[YCloud WhatsApp]
  To: {{ $json.body.from }}
  Media: {{ $json.data }}
```

### Workflow 2: Resumen Diario Automático

```
[Schedule Trigger]
  Every day at 9:00 AM
    ↓
[HTTP Request]
  Method: GET
  URL: http://tu-vps:8000/api/v1/integration/summary/abc-123
    ↓
[YCloud WhatsApp]
  To: +5491112345678
  Body: "Resumen diario: {{ $json.data.summary }}"
```

### Workflow 3: Generar Campaña

```
[Manual Trigger]
    ↓
[HTTP Request]
  Method: POST
  URL: http://tu-vps:8000/api/v1/integration/campaign/generate
  Body: {
    "collection_id": "abc-123",
    "campaign_type": "whatsapp"
  }
    ↓
[HTTP Request]
  Method: POST
  URL: http://tu-vps:8000/api/v1/integration/campaign/content
  Body: {
    "collection_id": "abc-123",
    "brief": "{{ $json.data.brief }}"
  }
    ↓
[Google Sheets]
  Spreadsheet: Campañas 2025
  Range: A:D
  Values: [
    ["{{ $json.data.headline }}",
     "{{ $json.data.body }}",
     "{{ $json.data.cta }}",
     "{{ $json.data.segmentation }}"]
  ]
    ↓
[YCloud WhatsApp]
  To: +5491112345678
  Body: "Campaña generada: {{ $json.data.headline }}"
```

## Webhooks desde RAG a n8n

El sistema puede notificar a n8n cuando ocurren eventos:

### Eventos Disponibles
- `document_indexed` — Documento terminó de indexar
- `document_error` — Error al procesar documento
- `chat_low_confidence` — Chat con baja confianza en respuesta

### Configurar Webhook URL

```bash
# En .env
N8N_WEBHOOK_URL=https://tu-n8n.com/webhook/rag-events
```

### Payload de Webhook

```json
{
  "event": "document_indexed",
  "collection_id": "abc-123",
  "document_id": "def-456",
  "document_name": "brochure.pdf",
  "chunks_created": 12,
  "entities_extracted": 8,
  "timestamp": "2026-05-15T12:00:00Z"
}
```

## Variables de n8n Útiles

```javascript
// En Code Node de n8n

// Extraer texto del mensaje de WhatsApp
const message = $input.first().json.body.message;

// Detectar si el usuario quiere cambiar de colección
const collections = ["contabilidad", "rrhh", "sistemas"];
const mentioned = collections.find(c => message.toLowerCase().includes(c));

return {
  collection_id: mentioned ? getCollectionId(mentioned) : "default",
  question: message
};
```

## Seguridad

- Usa HTTPS para todos los endpoints en producción
- Rota las API Keys periódicamente
- Scopéa las keys a colecciones específicas
- No compartas la API Key en logs de n8n

## Troubleshooting

### Error 403 en n8n
- Verifica que la API Key esté activa
- Verifica que la key tenga acceso a la colección solicitada

### Timeout en respuestas largas
- Aumenta el timeout del nodo HTTP Request a 60s
- Considera usar el webhook de "document_indexed" en lugar de polling

### Caracteres especiales en respuestas
- Asegúrate de que n8n use UTF-8 en el body de WhatsApp
