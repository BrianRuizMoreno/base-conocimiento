import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { client } from '../lib/client'
import { useAuth } from '../context/AuthContext'
import {
  ArrowLeft, Loader2, FileText, BarChart3, Globe,
  AlertCircle
} from 'lucide-react'

export default function Analysis() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()

  const [activeTab, setActiveTab] = useState<'summary' | 'analysis' | 'market'>('summary')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [data, setData] = useState<any>(null)

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/')
      return
    }
    if (id) {
      fetchData()
    }
  }, [id, activeTab, isAuthenticated])

  const fetchData = async () => {
    setLoading(true)
    setError('')
    try {
      let response
      if (activeTab === 'summary') {
        response = await client.get(`/v1/analysis/collections/${id}/summary`)
      } else if (activeTab === 'analysis') {
        response = await client.get(`/v1/analysis/collections/${id}/analysis`)
      } else {
        response = await client.post(`/v1/analysis/collections/${id}/market-compare`)
      }
      if (response.data.success) {
        setData(response.data.data)
      } else {
        setError(response.data.error || 'Error al obtener analisis')
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error de conexion')
    } finally {
      setLoading(false)
    }
  }

  if (!isAuthenticated) return null

  const tabs = [
    { id: 'summary', label: 'Resumen', icon: FileText },
    { id: 'analysis', label: 'Analisis Predictivo', icon: BarChart3 },
    { id: 'market', label: 'Comparativa', icon: Globe },
  ] as const

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-4">
          <button
            onClick={() => navigate(`/collection/${id}`)}
            className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-foreground hover:bg-accent"
          >
            <ArrowLeft className="h-4 w-4" />
            Volver
          </button>
          <h1 className="text-xl font-bold text-foreground">Analisis</h1>
        </div>
      </header>

      <main className="mx-auto max-w-7xl p-6">
        {/* Tabs */}
        <div className="mb-6 flex gap-1 border-b border-border">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'border-b-2 border-primary-600 text-primary-600'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            )
          })}
        </div>

        {error && (
          <div className="mb-6 flex items-center gap-2 rounded-lg bg-red-50 p-4 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
          </div>
        ) : (
          <div className="rounded-xl border border-border bg-card p-6">
            {activeTab === 'summary' && data && (
              <div className="space-y-6">
                <div>
                  <h2 className="mb-2 text-lg font-semibold text-foreground">Resumen de la coleccion</h2>
                  <p className="text-muted-foreground">{data.summary}</p>
                </div>
                {data.key_entities && data.key_entities.length > 0 && (
                  <div>
                    <h3 className="mb-2 text-sm font-medium text-foreground">Entidades clave</h3>
                    <div className="flex flex-wrap gap-2">
                      {data.key_entities.map((e: string, i: number) => (
                        <span key={i} className="rounded-full bg-primary-50 px-3 py-1 text-sm text-primary-700 dark:bg-primary-900/20 dark:text-primary-300">
                          {e}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {data.topics && data.topics.length > 0 && (
                  <div>
                    <h3 className="mb-2 text-sm font-medium text-foreground">Temas principales</h3>
                    <div className="flex flex-wrap gap-2">
                      {data.topics.map((t: string, i: number) => (
                        <span key={i} className="rounded-full bg-secondary px-3 py-1 text-sm text-secondary-foreground">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'analysis' && data && (
              <div className="space-y-6">
                <div>
                  <h2 className="mb-2 text-lg font-semibold text-foreground">Analisis Predictivo</h2>
                  <p className="text-muted-foreground">
                    Metricas y tendencias basadas en el contenido de la coleccion.
                  </p>
                </div>
                {data.metrics && Object.keys(data.metrics).length > 0 ? (
                  <div className="grid gap-4 md:grid-cols-3">
                    {Object.entries(data.metrics).map(([key, value]: [string, any]) => (
                      <div key={key} className="rounded-lg border border-border bg-background p-4">
                        <p className="text-sm text-muted-foreground">{key}</p>
                        <p className="mt-1 text-xl font-semibold text-foreground">{String(value)}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-lg bg-muted p-8 text-center text-sm text-muted-foreground">
                    No hay metricas disponibles todavia.
                  </div>
                )}
              </div>
            )}

            {activeTab === 'market' && data && (
              <div className="space-y-6">
                <div>
                  <h2 className="mb-2 text-lg font-semibold text-foreground">Comparativa de Mercado</h2>
                  <p className="text-muted-foreground">{data.comparison}</p>
                </div>
                {data.sources && data.sources.length > 0 && (
                  <div>
                    <h3 className="mb-2 text-sm font-medium text-foreground">Fuentes</h3>
                    <ul className="space-y-1">
                      {data.sources.map((s: string, i: number) => (
                        <li key={i} className="text-sm text-muted-foreground">{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {!data && !loading && !error && (
              <div className="py-12 text-center text-muted-foreground">
                No hay datos disponibles.
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
