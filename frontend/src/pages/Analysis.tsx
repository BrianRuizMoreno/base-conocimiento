import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { client } from '../lib/client'
import { useAuth } from '../context/AuthContext'
import {
  ArrowLeft, Loader2, FileText, BarChart3, Globe,
  AlertCircle, TrendingUp, TrendingDown, Minus,
  Search, ExternalLink
} from 'lucide-react'
import {
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar
} from 'recharts'

interface SummaryData {
  summary: string
  key_entities: string[]
  topics: string[]
  document_count: number
  chunk_count: number
}

interface TrendItem {
  name: string
  value: number
  direction: 'up' | 'down' | 'stable'
  period: string
}

interface PredictionItem {
  statement: string
  confidence: string
  timeframe: string
}

interface AnalysisData {
  metrics: Record<string, string | number>
  trends: TrendItem[]
  predictions: PredictionItem[]
  document_count: number
  chunk_count: number
}

interface ComparisonRow {
  dimension: string
  internal_data: string
  external_data: string
  source_url?: string
}

interface MarketData {
  topic: string
  comparison_rows: ComparisonRow[]
  conclusion: string
  sources: { title: string; url: string }[]
}

export default function Analysis() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()

  const [activeTab, setActiveTab] = useState<'summary' | 'analysis' | 'market'>('summary')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [summaryData, setSummaryData] = useState<SummaryData | null>(null)
  const [analysisData, setAnalysisData] = useState<AnalysisData | null>(null)
  const [marketData, setMarketData] = useState<MarketData | null>(null)
  const [marketTopic, setMarketTopic] = useState('')
  const [marketDimensions, setMarketDimensions] = useState('')

  const fetchSummary = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError('')
    try {
      const response = await client.get(`/v1/analysis/collections/${id}/summary`)
      if (response.data.success) {
        setSummaryData(response.data.data)
      } else {
        setError(response.data.error || 'Error al obtener resumen')
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error de conexion')
    } finally {
      setLoading(false)
    }
  }, [id])

  const fetchAnalysis = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError('')
    try {
      const response = await client.get(`/v1/analysis/collections/${id}/analysis`)
      if (response.data.success) {
        setAnalysisData(response.data.data)
      } else {
        setError(response.data.error || 'Error al obtener analisis')
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error de conexion')
    } finally {
      setLoading(false)
    }
  }, [id])

  const fetchMarketCompare = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError('')
    try {
      const response = await client.post(`/v1/analysis/collections/${id}/market-compare`, {
        topic: marketTopic || 'comparativa general',
        dimensions: marketDimensions ? marketDimensions.split(',').map(s => s.trim()) : undefined
      })
      if (response.data.success) {
        setMarketData(response.data.data)
      } else {
        setError(response.data.error || 'Error al obtener comparativa')
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error de conexion')
    } finally {
      setLoading(false)
    }
  }, [id, marketTopic, marketDimensions])

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/')
      return
    }
    if (activeTab === 'summary') {
      if (!summaryData) fetchSummary()
    } else if (activeTab === 'analysis') {
      if (!analysisData) fetchAnalysis()
    }
  }, [id, activeTab, isAuthenticated, navigate, fetchSummary, fetchAnalysis, summaryData, analysisData])

  const handleTagClick = (tag: string) => {
    navigate(`/collection/${id}/chat`, { state: { initialQuestion: `Dime mas sobre ${tag}` } })
  }

  const tabs = [
    { id: 'summary' as const, label: 'Resumen', icon: FileText },
    { id: 'analysis' as const, label: 'Analisis Predictivo', icon: BarChart3 },
    { id: 'market' as const, label: 'Comparativa', icon: Globe },
  ]

  // Prepare trend chart data
  const trendChartData = analysisData?.trends?.map(t => ({
    name: t.name,
    valor: typeof t.value === 'number' ? t.value : 0,
  })) || []

  // Confidence color helper
  const getConfidenceColor = (c: string) => {
    switch (c.toLowerCase()) {
      case 'alta': return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
      case 'media': return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300'
      case 'baja': return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
      default: return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
    }
  }

  const getDirectionIcon = (dir: string) => {
    switch (dir) {
      case 'up': return <TrendingUp className="h-4 w-4 text-green-500" />
      case 'down': return <TrendingDown className="h-4 w-4 text-red-500" />
      default: return <Minus className="h-4 w-4 text-gray-400" />
    }
  }

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

      <main className="mx-auto max-w-7xl p-4 md:p-6">
        {/* Tabs */}
        <div className="mb-6 flex flex-wrap gap-1 border-b border-border">
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
          <div className="space-y-6">
            {/* ==================== RESUMEN ==================== */}
            {activeTab === 'summary' && summaryData && (
              <div className="space-y-6">
                {/* Stats */}
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="rounded-lg border border-border bg-card p-4">
                    <p className="text-sm text-muted-foreground">Documentos</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{summaryData.document_count}</p>
                  </div>
                  <div className="rounded-lg border border-border bg-card p-4">
                    <p className="text-sm text-muted-foreground">Chunks</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{summaryData.chunk_count}</p>
                  </div>
                  <div className="rounded-lg border border-border bg-card p-4">
                    <p className="text-sm text-muted-foreground">Entidades clave</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{summaryData.key_entities?.length || 0}</p>
                  </div>
                  <div className="rounded-lg border border-border bg-card p-4">
                    <p className="text-sm text-muted-foreground">Temas principales</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{summaryData.topics?.length || 0}</p>
                  </div>
                </div>

                {/* Summary text */}
                <div className="rounded-xl border border-border bg-card p-6">
                  <h2 className="mb-3 text-lg font-semibold text-foreground">Resumen ejecutivo</h2>
                  <p className="leading-relaxed text-muted-foreground">{summaryData.summary}</p>
                </div>

                {/* Key entities */}
                {summaryData.key_entities && summaryData.key_entities.length > 0 && (
                  <div className="rounded-xl border border-border bg-card p-6">
                    <h3 className="mb-3 text-sm font-medium text-foreground">Entidades clave</h3>
                    <div className="flex flex-wrap gap-2">
                      {summaryData.key_entities.map((entity, i) => (
                        <button
                          key={i}
                          onClick={() => handleTagClick(entity)}
                          className="group flex items-center gap-1 rounded-full bg-primary-50 px-3 py-1.5 text-sm text-primary-700 transition-colors hover:bg-primary-100 dark:bg-primary-900/20 dark:text-primary-300 dark:hover:bg-primary-900/40"
                        >
                          {entity}
                          <Search className="h-3 w-3 opacity-0 transition-opacity group-hover:opacity-100" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Topics */}
                {summaryData.topics && summaryData.topics.length > 0 && (
                  <div className="rounded-xl border border-border bg-card p-6">
                    <h3 className="mb-3 text-sm font-medium text-foreground">Temas principales</h3>
                    <div className="flex flex-wrap gap-2">
                      {summaryData.topics.map((topic, i) => (
                        <button
                          key={i}
                          onClick={() => handleTagClick(topic)}
                          className="group flex items-center gap-1 rounded-full bg-secondary px-3 py-1.5 text-sm text-secondary-foreground transition-colors hover:bg-secondary/80"
                        >
                          {topic}
                          <Search className="h-3 w-3 opacity-0 transition-opacity group-hover:opacity-100" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ==================== ANALISIS PREDICTIVO ==================== */}
            {activeTab === 'analysis' && analysisData && (
              <div className="space-y-6">
                {/* Metrics cards */}
                {analysisData.metrics && Object.keys(analysisData.metrics).length > 0 && (
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {Object.entries(analysisData.metrics).map(([key, value]) => (
                      <div key={key} className="rounded-lg border border-border bg-card p-4">
                        <p className="text-sm capitalize text-muted-foreground">{key.replace(/_/g, ' ')}</p>
                        <p className="mt-1 text-xl font-semibold text-foreground">{String(value)}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Trends chart */}
                {trendChartData.length > 0 && (
                  <div className="rounded-xl border border-border bg-card p-6">
                    <h3 className="mb-4 text-sm font-medium text-foreground">Tendencias</h3>
                    <div className="h-64 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={trendChartData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                          <YAxis tick={{ fontSize: 12 }} />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: 'var(--card)',
                              border: '1px solid var(--border)',
                              borderRadius: '8px',
                            }}
                          />
                          <Bar dataKey="valor" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}

                {/* Trends list */}
                {analysisData.trends && analysisData.trends.length > 0 && (
                  <div className="rounded-xl border border-border bg-card p-6">
                    <h3 className="mb-4 text-sm font-medium text-foreground">Detalle de tendencias</h3>
                    <div className="space-y-3">
                      {analysisData.trends.map((trend, i) => (
                        <div key={i} className="flex items-center justify-between rounded-lg bg-background p-3">
                          <div className="flex items-center gap-3">
                            {getDirectionIcon(trend.direction)}
                            <div>
                              <p className="text-sm font-medium text-foreground">{trend.name}</p>
                              <p className="text-xs text-muted-foreground">{trend.period}</p>
                            </div>
                          </div>
                          <span className="text-sm font-semibold text-foreground">
                            {typeof trend.value === 'number' ? trend.value.toFixed(1) : trend.value}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Predictions */}
                {analysisData.predictions && analysisData.predictions.length > 0 && (
                  <div className="rounded-xl border border-border bg-card p-6">
                    <h3 className="mb-4 text-sm font-medium text-foreground">Predicciones</h3>
                    <div className="space-y-3">
                      {analysisData.predictions.map((pred, i) => (
                        <div key={i} className="rounded-lg bg-background p-4">
                          <div className="mb-2 flex items-center gap-2">
                            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${getConfidenceColor(pred.confidence)}`}>
                              {pred.confidence}
                            </span>
                            <span className="text-xs text-muted-foreground">{pred.timeframe}</span>
                          </div>
                          <p className="text-sm text-foreground">{pred.statement}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {!analysisData.metrics || Object.keys(analysisData.metrics).length === 0 && (
                  <div className="rounded-lg bg-muted p-8 text-center text-sm text-muted-foreground">
                    No hay metricas disponibles. Indexa documentos con datos numericos para generar analisis.
                  </div>
                )}
              </div>
            )}

            {/* ==================== COMPARATIVA DE MERCADO ==================== */}
            {activeTab === 'market' && (
              <div className="space-y-6">
                {/* Input form */}
                <div className="rounded-xl border border-border bg-card p-6">
                  <h2 className="mb-4 text-lg font-semibold text-foreground">Comparativa de Mercado</h2>
                  <div className="space-y-4">
                    <div>
                      <label className="mb-1 block text-sm font-medium text-foreground">Tema o producto a comparar</label>
                      <input
                        type="text"
                        value={marketTopic}
                        onChange={(e) => setMarketTopic(e.target.value)}
                        placeholder="Ej: smartphone gama alta, servicios cloud..."
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-foreground">Dimensiones (opcional, separadas por coma)</label>
                      <input
                        type="text"
                        value={marketDimensions}
                        onChange={(e) => setMarketDimensions(e.target.value)}
                        placeholder="Ej: precio, calidad, soporte, mercado objetivo"
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                      />
                    </div>
                    <button
                      onClick={fetchMarketCompare}
                      disabled={loading || !marketTopic.trim()}
                      className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                      Comparar
                    </button>
                  </div>
                </div>

                {/* Results */}
                {marketData && (
                  <>
                    {/* Comparison table */}
                    {marketData.comparison_rows && marketData.comparison_rows.length > 0 && (
                      <div className="rounded-xl border border-border bg-card p-6">
                        <h3 className="mb-4 text-sm font-medium text-foreground">Tabla comparativa: {marketData.topic}</h3>
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-border">
                                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Dimension</th>
                                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Dato interno</th>
                                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Dato externo</th>
                                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Fuente</th>
                              </tr>
                            </thead>
                            <tbody>
                              {marketData.comparison_rows.map((row, i) => (
                                <tr key={i} className="border-b border-border last:border-0">
                                  <td className="px-4 py-3 font-medium text-foreground">{row.dimension}</td>
                                  <td className="px-4 py-3 text-muted-foreground">{row.internal_data}</td>
                                  <td className="px-4 py-3 text-muted-foreground">{row.external_data}</td>
                                  <td className="px-4 py-3">
                                    {row.source_url ? (
                                      <a
                                        href={row.source_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex items-center gap-1 text-primary-600 hover:underline"
                                      >
                                        Ver fuente
                                        <ExternalLink className="h-3 w-3" />
                                      </a>
                                    ) : (
                                      <span className="text-muted-foreground">-</span>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {/* Conclusion */}
                    {marketData.conclusion && (
                      <div className="rounded-xl border border-border bg-card p-6">
                        <h3 className="mb-2 text-sm font-medium text-foreground">Conclusion</h3>
                        <p className="text-muted-foreground">{marketData.conclusion}</p>
                      </div>
                    )}

                    {/* Sources */}
                    {marketData.sources && marketData.sources.length > 0 && (
                      <div className="rounded-xl border border-border bg-card p-6">
                        <h3 className="mb-3 text-sm font-medium text-foreground">Fuentes externas</h3>
                        <ul className="space-y-2">
                          {marketData.sources.map((source, i) => (
                            <li key={i}>
                              <a
                                href={source.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-2 text-sm text-primary-600 hover:underline"
                              >
                                <ExternalLink className="h-3 w-3" />
                                {source.title || source.url}
                              </a>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                )}

                {!marketData && !loading && !error && (
                  <div className="rounded-lg bg-muted p-8 text-center text-sm text-muted-foreground">
                    Ingresa un tema y presiona Comparar para ver los resultados.
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
