import { useEffect, useRef, useState, useCallback } from 'react'
import CytoscapeComponent from 'react-cytoscapejs'
import cytoscape from 'cytoscape'
import { client } from '../lib/client'
import { Loader2, AlertCircle, ZoomIn, ZoomOut, Maximize, Info } from 'lucide-react'

interface GraphNode {
  data: {
    id: string
    label: string
    type: string
  }
}

interface GraphEdge {
  data: {
    source: string
    target: string
    label: string
    weight?: number
  }
}

interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

const TYPE_COLORS: Record<string, string> = {
  company: '#3b82f6',
  person: '#22c55e',
  product: '#f97316',
  metric: '#a855f7',
  date: '#eab308',
  location: '#06b6d4',
  technology: '#ec4899',
  industry: '#6366f1',
  other: '#9ca3af',
}

function getNodeColor(type: string) {
  return TYPE_COLORS[type?.toLowerCase()] || TYPE_COLORS.other
}

interface EntityGraphProps {
  collectionId?: string
  height?: string
}

export default function EntityGraph({ collectionId, height = '600px' }: EntityGraphProps) {
  const cyRef = useRef<cytoscape.Core | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] })
  const [selectedNode, setSelectedNode] = useState<GraphNode['data'] | null>(null)

  const fetchGraph = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const url = collectionId
        ? `/v1/collections/${collectionId}/graph`
        : `/v1/collections/global/graph`
      const res = await client.get(url)
      if (res.data.success) {
        setGraphData(res.data.data || { nodes: [], edges: [] })
      } else {
        setError(res.data.error || 'Error al cargar el grafo')
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error al cargar el grafo')
    } finally {
      setLoading(false)
    }
  }, [collectionId])

  useEffect(() => {
    fetchGraph()
  }, [fetchGraph])

  useEffect(() => {
    if (cyRef.current && graphData.nodes.length > 0) {
      const cy = cyRef.current
      cy.layout({
        name: 'cose',
        animate: true,
        animationDuration: 500,
        padding: 20,
        nodeRepulsion: 4500,
        idealEdgeLength: 100,
        componentSpacing: 100,
      } as any).run()
      cy.fit()
    }
  }, [graphData])

  const elements = [
    ...graphData.nodes.map((n) => ({
      data: n.data,
      classes: `node-${n.data.type || 'other'}`,
    })),
    ...graphData.edges.map((e) => ({
      data: e.data,
    })),
  ]

  const stylesheet = [
    {
      selector: 'node',
      style: {
        label: 'data(label)',
        width: 40,
        height: 40,
        'background-color': (ele: any) => getNodeColor(ele.data('type')),
        color: '#fff',
        'text-outline-color': '#000',
        'text-outline-width': 1,
        'font-size': '12px',
        'text-valign': 'center',
        'text-halign': 'center',
        'border-width': 2,
        'border-color': '#fff',
      },
    },
    {
      selector: 'edge',
      style: {
        width: 2,
        'line-color': '#94a3b8',
        'target-arrow-color': '#94a3b8',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        label: 'data(label)',
        'font-size': '10px',
        color: '#64748b',
        'text-background-color': '#fff',
        'text-background-opacity': 0.8,
        'text-background-padding': '2px',
      },
    },
    {
      selector: ':selected',
      style: {
        'border-width': 4,
        'border-color': '#f59e0b',
        'background-color': '#f59e0b',
      },
    },
  ] as any

  const handleZoomIn = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 1.2)
    }
  }

  const handleZoomOut = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() / 1.2)
    }
  }

  const handleFit = () => {
    if (cyRef.current) {
      cyRef.current.fit()
    }
  }

  return (
    <div className="w-full">
      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <button
            onClick={fetchGraph}
            disabled={loading}
            className="flex items-center gap-1 rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground hover:bg-accent disabled:opacity-50"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            Actualizar
          </button>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleZoomIn}
            className="rounded-lg border border-border bg-card p-2 text-foreground hover:bg-accent"
            title="Acercar"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
          <button
            onClick={handleZoomOut}
            className="rounded-lg border border-border bg-card p-2 text-foreground hover:bg-accent"
            title="Alejar"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <button
            onClick={handleFit}
            className="rounded-lg border border-border bg-card p-2 text-foreground hover:bg-accent"
            title="Ajustar"
          >
            <Maximize className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="relative rounded-xl border border-border bg-card" style={{ height }}>
        {elements.length === 0 && !loading ? (
          <div className="flex h-full flex-col items-center justify-center text-sm text-muted-foreground">
            <Info className="mb-2 h-8 w-8" />
            No hay datos de grafo disponibles
          </div>
        ) : (
          <CytoscapeComponent
            elements={elements}
            style={{ width: '100%', height: '100%' }}
            stylesheet={stylesheet}
            cy={(cy) => {
              cyRef.current = cy
              cy.on('tap', 'node', (evt) => {
                setSelectedNode(evt.target.data())
              })
              cy.on('tap', (evt) => {
                if (evt.target === cy) {
                  setSelectedNode(null)
                }
              })
            }}
          />
        )}

        {selectedNode && (
          <div className="absolute bottom-4 left-4 z-10 max-w-xs rounded-lg border border-border bg-card p-3 shadow-lg">
            <p className="text-sm font-semibold text-foreground">{selectedNode.label}</p>
            <p className="text-xs text-muted-foreground capitalize">{selectedNode.type}</p>
            <button
              onClick={() => setSelectedNode(null)}
              className="mt-2 text-xs text-primary-600 hover:underline"
            >
              Cerrar
            </button>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="mt-4 flex flex-wrap gap-3">
        {Object.entries(TYPE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
            <span className="capitalize">{type}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
