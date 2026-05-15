# Entidades y Grafo de Conocimiento

## Visión General

El grafo de entidades complementa la búsqueda vectorial con relaciones estructuradas entre conceptos extraídos de los documentos.

## Tipos de Entidades

| Tipo | Ejemplos | Uso |
|---|---|---|
| `company` | Acme Corp, Beta Inc | Competidores, proveedores |
| `person` | Juan Pérez, CEO | Autores, contactos |
| `product` | CRM Software, Plan Básico | Catálogo, pricing |
| `metric` | $50/mes, 12% crecimiento | Datos numéricos |
| `date` | 2025-01-15, Q1 2026 | Eventos, plazos |
| `location` | Buenos Aires, Argentina | Oficinas, mercados |
| `technology` | Python, React | Stack técnico |
| `industry` | SaaS, Fintech | Sector de mercado |

## Tipos de Relaciones

| Relación | Descripción | Ejemplo |
|---|---|---|
| `competes_with` | Competencia directa | Acme Corp → Beta Inc |
| `sells` | Producto ofrecido | Acme Corp → CRM Software |
| `works_for` | Empleado de | Juan Pérez → Acme Corp |
| `located_in` | Ubicación | Acme Corp → Buenos Aires |
| `has_price` | Precio de producto | CRM Software → $50/mes |
| `grows_by` | Métrica de crecimiento | Mercado SaaS → 12% |
| `uses` | Tecnología usada | Acme Corp → Python |
| `belongs_to` | Categoría/sector | Acme Corp → SaaS |

## Extracción de Entidades

Cuando se indexa un documento, el sistema:

1. **Divide** el texto en chunks
2. **Envía** los chunks a Gemini con prompt de extracción:

```
Extrae todas las entidades y relaciones del siguiente texto.

Formato de salida (JSON):
{
  "entities": [
    {"name": "nombre", "type": "company|person|product|..."}
  ],
  "relationships": [
    {"source": "entidad A", "target": "entidad B", "type": "relación"}
  ]
}

Texto:
{chunk_text}
```

3. **Deduplica** entidades por nombre + colección
4. **Almacena** en tablas `entities` y `relationships`

## Búsqueda en el Grafo

### Por entidad
```sql
-- Encontrar todo sobre "Acme Corp"
SELECT e.*, r.relation_type, t.name as target_name
FROM entities e
LEFT JOIN relationships r ON e.id = r.source_entity_id
LEFT JOIN entities t ON r.target_entity_id = t.id
WHERE e.name ILIKE '%Acme Corp%'
```

### Por relación
```sql
-- Competidores de Acme Corp
SELECT t.name as competitor
FROM entities e
JOIN relationships r ON e.id = r.source_entity_id
JOIN entities t ON r.target_entity_id = t.id
WHERE e.name = 'Acme Corp' AND r.relation_type = 'competes_with'
```

### Por comunidad
```sql
-- Entidades relacionadas indirectamente (2 saltos)
WITH RECURSIVE related AS (
  SELECT target_entity_id as id, 1 as depth
  FROM relationships
  WHERE source_entity_id = 'uuid-acme'
  
  UNION ALL
  
  SELECT r.target_entity_id, depth + 1
  FROM relationships r
  JOIN related ON r.source_entity_id = related.id
  WHERE depth < 3
)
SELECT DISTINCT e.* FROM related r
JOIN entities e ON r.id = e.id;
```

## Visualización

El frontend incluye un componente `GrafoEntidades` que renderiza el grafo usando **Cytoscape.js**:

```tsx
// GrafoEntidades.tsx
import CytoscapeComponent from 'react-cytoscapejs';

const elements = [
  // Nodes
  { data: { id: 'acme', label: 'Acme Corp', type: 'company' } },
  { data: { id: 'beta', label: 'Beta Inc', type: 'company' } },
  { data: { id: 'crm', label: 'CRM Software', type: 'product' } },
  
  // Edges
  { data: { source: 'acme', target: 'beta', label: 'compite con' } },
  { data: { source: 'acme', target: 'crm', label: 'vende' } },
];

<CytoscapeComponent
  elements={elements}
  style={{ width: '100%', height: '400px' }}
  layout={{ name: 'cose', padding: 10 }}
  stylesheet={[...]}
/>
```

## Combinación con Vector Search

El RAG pipeline usa ambas fuentes:

```
Query: "¿Quiénes son los competidores de Acme?"

Vector Search:
  - Chunk 1: "Acme Corp vende CRM..." (score: 0.85)
  - Chunk 2: "Beta Inc ofrece similar..." (score: 0.72)

Graph Search:
  - Entity: "Acme Corp" → COMPETES_WITH → "Beta Inc"
  - Related chunks: [chunk_2, chunk_5, chunk_8]

Fusion:
  - Vector: chunk_1, chunk_2
  - Graph: chunk_2, chunk_5, chunk_8
  - Deduplicated: chunk_1, chunk_2, chunk_5, chunk_8
  - Reranked: chunk_2 (0.91), chunk_5 (0.87), chunk_1 (0.85), chunk_8 (0.80)

Context:
  [chunk_2] Acme Corp compite con Beta Inc en el mercado CRM...
  [chunk_5] Beta Inc fue fundada en 2020 y tiene 500 clientes...
  [chunk_1] Acme Corp vende software CRM a $50/mes...
  
Respuesta: "Los principales competidores de Acme Corp son Beta Inc, 
           que ofrece un producto similar en el mercado CRM..."
```

## Mantenimiento

### Entidades huérfanas
Cuando se elimina un documento, sus chunks desaparecen. Las entidades que ya no tienen chunks asociados se marcan como "huérfanas" y pueden eliminarse:

```python
async def cleanup_orphan_entities(db: AsyncSession, collection_id: UUID):
    stmt = """
    DELETE FROM entities e
    WHERE e.collection_id = :collection_id
    AND NOT EXISTS (
        SELECT 1 FROM chunks c
        WHERE c.metadata->>'entities' ILIKE '%' || e.name || '%'
    )
    """
    await db.execute(text(stmt), {"collection_id": collection_id})
```

### Regeneración del grafo
Si se detecta que el grafo está desactualizado (nuevos documentos sin extracción):

```bash
# Endpoint para regenerar
POST /api/v1/collections/{id}/regenerate-graph
```

Esto re-procesa todos los chunks de la colección y extrae entidades nuevamente.
