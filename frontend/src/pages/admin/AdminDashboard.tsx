import { useState, useEffect } from 'react'
import { client } from '../../lib/client'
import { useAuth } from '../../context/AuthContext'
import { useNavigate, Link } from 'react-router-dom'
import {
  LayoutDashboard, Coins, Server, AlertTriangle, ClipboardList, Settings, Share2,
  Loader2, TrendingUp, TrendingDown, Activity, HardDrive, MemoryStick,
  Cpu, Database, FileText, CheckCircle2, XCircle, AlertCircle,
  Eye, EyeOff, Save, RefreshCw, Building2, Plus, Trash2, Key
} from 'lucide-react'
import EntityGraph from '../../components/EntityGraph'
import {
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar
} from 'recharts'

const tabs = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'sectors', label: 'Sectores', icon: Building2 },
  { id: 'tokens', label: 'Tokens', icon: Coins },
  { id: 'server', label: 'Servidor', icon: Server },
  { id: 'errors', label: 'Errores', icon: AlertTriangle },
  { id: 'executions', label: 'Ejecuciones', icon: ClipboardList },
  { id: 'graph', label: 'Grafo', icon: Share2 },
  { id: 'settings', label: 'Configuracion', icon: Settings },
]

const periods = [
  { id: '24h', label: '24h' },
  { id: '7d', label: '7 dias' },
  { id: '30d', label: '30 dias' },
  { id: 'all', label: 'Todo' },
]

export default function AdminDashboard() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const [activeTab, setActiveTab] = useState('dashboard')
  const [period, setPeriod] = useState('24h')

  // Data states
  const [metrics, setMetrics] = useState<any>(null)
  const [tokens, setTokens] = useState<any[]>([])
  const [serverStatus, setServerStatus] = useState<any>(null)
  const [errors, setErrors] = useState<any[]>([])
  const [executions, setExecutions] = useState<any[]>([])
  const [keysData, setKeysData] = useState<any>(null)

  // Sectors
  const [sectors, setSectors] = useState<any[]>([])
  const [newSectorName, setNewSectorName] = useState('')
  const [newSectorSlug, setNewSectorSlug] = useState('')
  const [newSectorDesc, setNewSectorDesc] = useState('')
  const [newTokenName, setNewTokenName] = useState('')
  const [sectorTokens, setSectorTokens] = useState<any[]>([])

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Settings form states
  const [newKeyProvider, setNewKeyProvider] = useState('gemini')
  const [newKeyValue, setNewKeyValue] = useState('')
  const [newKeyLabel, setNewKeyLabel] = useState('')
  const [newKeyPriority, setNewKeyPriority] = useState(0)
  const [showKeys, setShowKeys] = useState(false)

  const [chatConfig, setChatConfig] = useState({
    provider: 'gemini',
    model: 'gemini-2.0-flash',
    temperature: 0.2,
    top_p: 0.6,
    max_tokens: 2048
  })
  const [savingSettings, setSavingSettings] = useState(false)
  const [settingsMsg, setSettingsMsg] = useState('')

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/')
      return
    }
    fetchTabData(activeTab)
  }, [activeTab, period, isAuthenticated])

  const fetchTabData = async (tab: string) => {
    setLoading(true)
    setError('')
    try {
      switch (tab) {
        case 'dashboard': {
          const res = await client.get(`/v1/admin/metrics?period=${period}`)
          if (res.data.success) setMetrics(res.data.data)
          break
        }
        case 'tokens': {
          const res = await client.get(`/v1/admin/tokens?period=${period}`)
          if (res.data.success) setTokens(res.data.data || [])
          break
        }
        case 'server': {
          const res = await client.get('/v1/admin/server')
          if (res.data.success) setServerStatus(res.data.data)
          break
        }
        case 'errors': {
          const res = await client.get(`/v1/admin/errors?period=${period}`)
          if (res.data.success) setErrors(res.data.data || [])
          break
        }
        case 'executions': {
          const res = await client.get(`/v1/admin/executions?period=${period}`)
          if (res.data.success) setExecutions(res.data.data || [])
          break
        }
        case 'sectors': {
          const [sRes, tRes] = await Promise.all([
            client.get('/v1/admin/sectors'),
            client.get('/v1/admin/tokens')
          ])
          if (sRes.data.success) setSectors(sRes.data.data || [])
          if (tRes.data.success) setSectorTokens(tRes.data.data || [])
          break
        }
        case 'settings': {
          const [sRes, kRes] = await Promise.all([
            client.get('/v1/settings'),
            client.get('/v1/settings/keys')
          ])
          if (sRes.data.success && sRes.data.data.chat_config) {
            setChatConfig(sRes.data.data.chat_config)
          }
          if (kRes.data.success) setKeysData(kRes.data.data)
          break
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error al cargar datos')
    } finally {
      setLoading(false)
    }
  }

  const saveApiKey = async () => {
    if (!newKeyValue.trim()) return
    setSavingSettings(true)
    setSettingsMsg('')
    try {
      const res = await client.post('/v1/settings/keys', {
        provider: newKeyProvider,
        api_key: newKeyValue,
        label: newKeyLabel || undefined,
        priority: newKeyPriority,
      })
      if (res.data.success) {
        setSettingsMsg('API key agregada')
        setNewKeyValue('')
        setNewKeyLabel('')
        setNewKeyPriority(0)
        fetchTabData('settings')
      } else {
        setSettingsMsg(res.data.error || 'Error al guardar')
      }
    } catch (err: any) {
      setSettingsMsg(err.response?.data?.error || 'Error al guardar')
    } finally {
      setSavingSettings(false)
    }
  }

  const deleteApiKey = async (keyId: string) => {
    setSavingSettings(true)
    try {
      const res = await client.delete(`/v1/settings/keys/${keyId}`)
      if (res.data.success) {
        setSettingsMsg('API key eliminada')
        fetchTabData('settings')
      } else {
        setSettingsMsg(res.data.error || 'Error al eliminar')
      }
    } catch (err: any) {
      setSettingsMsg(err.response?.data?.error || 'Error al eliminar')
    } finally {
      setSavingSettings(false)
    }
  }

  const toggleApiKey = async (keyId: string) => {
    setSavingSettings(true)
    try {
      const res = await client.post(`/v1/settings/keys/${keyId}/toggle`)
      if (res.data.success) {
        setSettingsMsg(res.data.data.is_active ? 'API key activada' : 'API key desactivada')
        fetchTabData('settings')
      } else {
        setSettingsMsg(res.data.error || 'Error al cambiar estado')
      }
    } catch (err: any) {
      setSettingsMsg(err.response?.data?.error || 'Error al cambiar estado')
    } finally {
      setSavingSettings(false)
    }
  }

  const saveChatConfig = async () => {
    setSavingSettings(true)
    setSettingsMsg('')
    try {
      const res = await client.put('/v1/settings/chat-config', chatConfig)
      if (res.data.success) {
        setSettingsMsg('Configuracion de chat guardada')
      } else {
        setSettingsMsg(res.data.error || 'Error al guardar')
      }
    } catch (err: any) {
      setSettingsMsg(err.response?.data?.error || 'Error al guardar')
    } finally {
      setSavingSettings(false)
    }
  }

  // Sector CRUD
  const createSector = async () => {
    if (!newSectorName.trim() || !newSectorSlug.trim()) return
    setLoading(true)
    try {
      const res = await client.post('/v1/admin/sectors', {
        name: newSectorName.trim(),
        slug: newSectorSlug.trim(),
        description: newSectorDesc.trim() || undefined,
      })
      if (res.data.success) {
        setNewSectorName('')
        setNewSectorSlug('')
        setNewSectorDesc('')
        fetchTabData('sectors')
      } else {
        setError(res.data.error || 'Error al crear sector')
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error al crear sector')
    } finally {
      setLoading(false)
    }
  }

  const deleteSector = async (id: string) => {
    if (!confirm('Eliminar este sector?')) return
    try {
      await client.delete(`/v1/admin/sectors/${id}`)
      fetchTabData('sectors')
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error al eliminar')
    }
  }

  const createSectorToken = async (sectorId: string) => {
    if (!newTokenName.trim()) return
    setLoading(true)
    try {
      const res = await client.post(`/v1/admin/sectors/${sectorId}/tokens`, {
        name: newTokenName.trim(),
      })
      if (res.data.success) {
        alert(`Token generado: ${res.data.data.token}\n\nGuardalo ahora, no se mostrara de nuevo.`)
        setNewTokenName('')
        fetchTabData('sectors')
      } else {
        setError(res.data.error || 'Error al generar token')
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error al generar token')
    } finally {
      setLoading(false)
    }
  }

  const revokeToken = async (tokenId: string) => {
    if (!confirm('Revocar este token?')) return
    try {
      await client.delete(`/v1/admin/tokens/${tokenId}`)
      fetchTabData('sectors')
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error al revocar')
    }
  }

  if (!isAuthenticated) return null

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-4">
            <Link to="/" className="text-xl font-bold text-foreground hover:text-primary-600">
              RAG System
            </Link>
            <span className="text-sm text-muted-foreground">/ Admin</span>
          </div>
          <Link
            to="/"
            className="rounded-lg border border-border px-4 py-2 text-sm text-foreground hover:bg-accent"
          >
            Volver
          </Link>
        </div>
      </header>

      {/* Tabs */}
      <div className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-7xl gap-1 px-4 overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors whitespace-nowrap ${
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
      </div>

      {/* Period selector */}
      {['dashboard', 'tokens', 'errors', 'executions'].includes(activeTab) && (
        <div className="mx-auto max-w-7xl px-4 pt-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Periodo:</span>
            <div className="flex gap-1">
              {periods.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setPeriod(p.id)}
                  className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                    period === p.id
                      ? 'bg-primary-600 text-white'
                      : 'border border-border text-foreground hover:bg-accent'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
            <button
              onClick={() => fetchTabData(activeTab)}
              className="ml-2 rounded-md p-1 text-muted-foreground hover:bg-accent"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Content */}
      <main className="mx-auto max-w-7xl p-6">
        {error && (
          <div className="mb-6 flex items-center gap-2 rounded-lg bg-red-50 p-4 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
          </div>
        )}

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && metrics && !loading && (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <StatCard label="Colecciones" value={metrics.stats?.collections ?? 0} icon={Database} color="blue" />
              <StatCard label="Documentos" value={metrics.stats?.documents ?? 0} icon={FileText} color="green" />
              <StatCard label="Chunks" value={metrics.stats?.chunks ?? 0} icon={Activity} color="purple" />
              <StatCard label="Entidades" value={metrics.stats?.entities ?? 0} icon={Database} color="orange" />
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              <StatCard label="Tokens Entrada" value={metrics.tokens?.total_in ?? 0} icon={TrendingUp} color="blue" />
              <StatCard label="Tokens Salida" value={metrics.tokens?.total_out ?? 0} icon={TrendingDown} color="green" />
              <StatCard label="Costo USD" value={`$${(metrics.tokens?.cost_usd ?? 0).toFixed(4)}`} icon={Coins} color="purple" />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <StatCard label="Errores" value={metrics.errors ?? 0} icon={AlertTriangle} color="red" />
              <StatCard label="Ejecuciones" value={metrics.executions ?? 0} icon={ClipboardList} color="orange" />
            </div>

            {/* Charts */}
            <div className="grid gap-6 md:grid-cols-2">
              <div className="rounded-xl border border-border bg-card p-6">
                <h3 className="mb-4 text-sm font-medium text-foreground">Recursos del sistema</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={[
                      { name: 'Colecciones', valor: metrics.stats?.collections ?? 0 },
                      { name: 'Documentos', valor: metrics.stats?.documents ?? 0 },
                      { name: 'Chunks', valor: metrics.stats?.chunks ?? 0 },
                      { name: 'Entidades', valor: metrics.stats?.entities ?? 0 },
                    ]}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid var(--border)', background: 'var(--card)' }} />
                      <Bar dataKey="valor" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="rounded-xl border border-border bg-card p-6">
                <h3 className="mb-4 text-sm font-medium text-foreground">Uso de tokens</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={[
                      { name: 'Entrada', valor: metrics.tokens?.total_in ?? 0 },
                      { name: 'Salida', valor: metrics.tokens?.total_out ?? 0 },
                    ]}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid var(--border)', background: 'var(--card)' }} />
                      <Bar dataKey="valor" fill="#8884d8" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tokens Tab */}
        {activeTab === 'tokens' && !loading && (
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Fecha</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Proveedor</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Modelo</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Operacion</th>
                    <th className="px-4 py-3 text-right font-medium text-muted-foreground">In</th>
                    <th className="px-4 py-3 text-right font-medium text-muted-foreground">Out</th>
                    <th className="px-4 py-3 text-right font-medium text-muted-foreground">Costo</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {tokens.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">
                        No hay registros de tokens en este periodo
                      </td>
                    </tr>
                  ) : (
                    tokens.map((t, i) => (
                      <tr key={i} className="hover:bg-muted/50">
                        <td className="px-4 py-3 text-foreground">{new Date(t.created_at).toLocaleString()}</td>
                        <td className="px-4 py-3 text-foreground">{t.provider}</td>
                        <td className="px-4 py-3 text-foreground">{t.model}</td>
                        <td className="px-4 py-3 text-foreground">{t.operation}</td>
                        <td className="px-4 py-3 text-right text-foreground">{t.tokens_in}</td>
                        <td className="px-4 py-3 text-right text-foreground">{t.tokens_out}</td>
                        <td className="px-4 py-3 text-right text-foreground">${t.cost_usd?.toFixed(6)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Sectors Tab */}
        {activeTab === 'sectors' && !loading && (
          <div className="space-y-6">
            {/* Create sector */}
            <div className="rounded-xl border border-border bg-card p-6">
              <h2 className="mb-4 text-lg font-semibold text-foreground">Crear Sector</h2>
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <label className="mb-1 block text-sm font-medium text-foreground">Nombre</label>
                  <input
                    type="text"
                    value={newSectorName}
                    onChange={(e) => setNewSectorName(e.target.value)}
                    placeholder="Ej: Ventas"
                    className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-foreground">Slug</label>
                  <input
                    type="text"
                    value={newSectorSlug}
                    onChange={(e) => setNewSectorSlug(e.target.value)}
                    placeholder="Ej: ventas"
                    className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-foreground">Descripcion</label>
                  <input
                    type="text"
                    value={newSectorDesc}
                    onChange={(e) => setNewSectorDesc(e.target.value)}
                    placeholder="Opcional"
                    className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
              </div>
              <button
                onClick={createSector}
                disabled={loading || !newSectorName.trim() || !newSectorSlug.trim()}
                className="mt-4 flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                <Plus className="h-4 w-4" />
                Crear Sector
              </button>
            </div>

            {/* Sectors list */}
            <div className="rounded-xl border border-border bg-card p-6">
              <h2 className="mb-4 text-lg font-semibold text-foreground">Sectores</h2>
              {sectors.length === 0 ? (
                <p className="text-sm text-muted-foreground">No hay sectores creados.</p>
              ) : (
                <div className="space-y-4">
                  {sectors.map((sector) => (
                    <div key={sector.id} className="rounded-lg border border-border bg-background p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-foreground">{sector.name}</p>
                          <p className="text-xs text-muted-foreground">{sector.slug}</p>
                          {sector.description && <p className="text-sm text-muted-foreground">{sector.description}</p>}
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => deleteSector(sector.id)}
                            className="rounded-lg p-2 text-muted-foreground hover:bg-red-50 hover:text-red-600"
                            aria-label={`Eliminar sector ${sector.name}`}
                          >
                            <Trash2 className="h-4 w-4" aria-hidden="true" />
                          </button>
                        </div>
                      </div>
                      {/* Tokens for this sector */}
                      <div className="mt-3">
                        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Tokens</p>
                        <div className="space-y-2">
                          {sectorTokens.filter((t: any) => t.sector_id === sector.id).map((token: any) => (
                            <div key={token.id} className="flex items-center justify-between rounded-md bg-muted px-3 py-2 text-sm">
                              <div className="flex items-center gap-2">
                                <Key className="h-3.5 w-3.5 text-muted-foreground" />
                                <span className="text-foreground">{token.name}</span>
                                <span className={`rounded-full px-1.5 py-0.5 text-xs ${token.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                                  {token.is_active ? 'Activo' : 'Revocado'}
                                </span>
                              </div>
                              <button
                                onClick={() => revokeToken(token.id)}
                                disabled={!token.is_active}
                                className="text-xs text-red-600 hover:underline disabled:opacity-50"
                              >
                                Revocar
                              </button>
                            </div>
                          ))}
                          <div className="flex items-center gap-2">
                            <input
                              type="text"
                              value={newTokenName}
                              onChange={(e) => setNewTokenName(e.target.value)}
                              placeholder="Nombre del token"
                              className="flex-1 rounded-md border border-input bg-background px-2 py-1 text-xs"
                            />
                            <button
                              onClick={() => createSectorToken(sector.id)}
                              disabled={!newTokenName.trim()}
                              className="rounded-md bg-primary-600 px-2 py-1 text-xs text-white hover:bg-primary-700 disabled:opacity-50"
                            >
                              Generar
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Server Tab */}
        {activeTab === 'server' && serverStatus && !loading && (
          <div className="space-y-6">
            <div className="grid gap-6 md:grid-cols-3">
              <ResourceCard
                label="CPU"
                value={serverStatus.cpu?.percent ?? 0}
                icon={Cpu}
                color="blue"
              />
              <ResourceCard
                label="RAM"
                value={serverStatus.ram?.percent ?? 0}
                used={serverStatus.ram?.used_gb}
                total={serverStatus.ram?.total_gb}
                unit="GB"
                icon={MemoryStick}
                color="purple"
              />
              <ResourceCard
                label="Disco"
                value={serverStatus.disk?.percent ?? 0}
                used={serverStatus.disk?.used_gb}
                total={serverStatus.disk?.total_gb}
                unit="GB"
                icon={HardDrive}
                color="green"
              />
            </div>
            <div className="rounded-xl border border-border bg-card p-6">
              <h3 className="mb-4 text-lg font-semibold text-foreground">Base de datos</h3>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-lg bg-muted p-4">
                  <p className="text-sm text-muted-foreground">Archivos</p>
                  <p className="mt-1 text-2xl font-bold text-foreground">{serverStatus.database?.files ?? 0}</p>
                </div>
                <div className="rounded-lg bg-muted p-4">
                  <p className="text-sm text-muted-foreground">Chunks</p>
                  <p className="mt-1 text-2xl font-bold text-foreground">{serverStatus.database?.chunks ?? 0}</p>
                </div>
                <div className="rounded-lg bg-muted p-4">
                  <p className="text-sm text-muted-foreground">Entidades</p>
                  <p className="mt-1 text-2xl font-bold text-foreground">{serverStatus.database?.entities ?? 0}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Errors Tab */}
        {activeTab === 'errors' && !loading && (
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Nivel</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Fuente</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Mensaje</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Fecha</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {errors.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                        No hay errores en este periodo
                      </td>
                    </tr>
                  ) : (
                    errors.map((e, i) => (
                      <tr key={i} className="hover:bg-muted/50">
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                            e.level === 'error'
                              ? 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300'
                              : e.level === 'warning'
                              ? 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-300'
                              : 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300'
                          }`}>
                            {e.level}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-foreground">{e.source}</td>
                        <td className="px-4 py-3 text-foreground max-w-md truncate">{e.message}</td>
                        <td className="px-4 py-3 text-muted-foreground">{new Date(e.created_at).toLocaleString()}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Executions Tab */}
        {activeTab === 'executions' && !loading && (
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Operacion</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Estado</th>
                    <th className="px-4 py-3 text-right font-medium text-muted-foreground">Duracion (ms)</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Fecha</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {executions.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                        No hay ejecuciones en este periodo
                      </td>
                    </tr>
                  ) : (
                    executions.map((e, i) => (
                      <tr key={i} className="hover:bg-muted/50">
                        <td className="px-4 py-3 text-foreground">{e.operation}</td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                            e.status === 'success'
                              ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300'
                              : e.status === 'failed'
                              ? 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300'
                              : 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-300'
                          }`}>
                            {e.status === 'success' && <CheckCircle2 className="h-3 w-3" />}
                            {e.status === 'failed' && <XCircle className="h-3 w-3" />}
                            {e.status === 'running' && <Loader2 className="h-3 w-3 animate-spin" />}
                            {e.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right text-foreground">{e.duration_ms}</td>
                        <td className="px-4 py-3 text-muted-foreground">{new Date(e.created_at).toLocaleString()}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && !loading && (
          <div className="space-y-6">
            {/* API Keys Management */}
            <div className="rounded-xl border border-border bg-card p-6">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-foreground">API Keys</h2>
                <button
                  onClick={() => setShowKeys(!showKeys)}
                  className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
                >
                  {showKeys ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  {showKeys ? 'Ocultar' : 'Mostrar'}
                </button>
              </div>

              {/* Add new key form */}
              <div className="mb-6 space-y-3 rounded-lg bg-muted/50 p-4">
                <div className="grid gap-3 md:grid-cols-3">
                  <div>
                    <label className="mb-1 block text-sm font-medium text-foreground">Proveedor</label>
                    <select
                      value={newKeyProvider}
                      onChange={(e) => setNewKeyProvider(e.target.value)}
                      className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
                    >
                      <option value="gemini">Gemini</option>
                      <option value="openai">OpenAI</option>
                      <option value="anthropic">Anthropic</option>
                      <option value="tavily">Tavily</option>
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-foreground">Label</label>
                    <input
                      type="text"
                      value={newKeyLabel}
                      onChange={(e) => setNewKeyLabel(e.target.value)}
                      placeholder="Ej: Key principal"
                      className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-foreground">Prioridad</label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={newKeyPriority}
                      onChange={(e) => setNewKeyPriority(parseInt(e.target.value))}
                      className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
                    />
                  </div>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-foreground">API Key</label>
                  <div className="flex gap-2">
                    <input
                      type={showKeys ? 'text' : 'password'}
                      value={newKeyValue}
                      onChange={(e) => setNewKeyValue(e.target.value)}
                      placeholder="Pega la API key aqui"
                      className="flex-1 rounded-lg border border-input bg-background px-3 py-2 text-sm"
                    />
                    <button
                      onClick={saveApiKey}
                      disabled={savingSettings || !newKeyValue.trim()}
                      className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
                    >
                      {savingSettings && <Loader2 className="h-4 w-4 animate-spin" />}
                      <Save className="h-4 w-4" />
                      Agregar
                    </button>
                  </div>
                </div>
              </div>

              {/* Existing keys list */}
              <div className="space-y-4">
                {keysData && Object.entries(keysData.providers || {}).map(([provider, keys]: [string, any]) => (
                  keys.length > 0 && (
                    <div key={provider}>
                      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                        {provider}
                      </h3>
                      <div className="space-y-2">
                        {keys.map((key: any) => (
                          <div key={key.id} className="flex items-center justify-between rounded-lg border border-border bg-background px-4 py-3">
                            <div className="flex items-center gap-3">
                              <div className={`h-2 w-2 rounded-full ${key.is_active ? 'bg-green-500' : 'bg-gray-400'}`} />
                              <div>
                                <p className="text-sm font-medium text-foreground">{key.label}</p>
                                <p className="text-xs text-muted-foreground">
                                  Prioridad: {key.priority}
                                  {key.failure_count > 0 && ` · Fallos: ${key.failure_count}`}
                                  {key.last_used_at && ` · Usada: ${new Date(key.last_used_at).toLocaleDateString()}`}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => toggleApiKey(key.id)}
                                className={`rounded-md px-2 py-1 text-xs font-medium ${
                                  key.is_active
                                    ? 'bg-yellow-50 text-yellow-700 hover:bg-yellow-100 dark:bg-yellow-900/20'
                                    : 'bg-green-50 text-green-700 hover:bg-green-100 dark:bg-green-900/20'
                                }`}
                              >
                                {key.is_active ? 'Desactivar' : 'Activar'}
                              </button>
                              <button
                                onClick={() => deleteApiKey(key.id)}
                                className="rounded-md bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100 dark:bg-red-900/20"
                              >
                                Eliminar
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                ))}
                {(!keysData || Object.values(keysData.providers || {}).every((k: any) => k.length === 0)) && (
                  <p className="text-sm text-muted-foreground">No hay API keys configuradas.</p>
                )}
              </div>
            </div>

            {/* Chat Config */}
            <div className="rounded-xl border border-border bg-card p-6">
              <h2 className="mb-4 text-lg font-semibold text-foreground">Configuracion de Chat</h2>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium text-foreground">Proveedor</label>
                  <select
                    value={chatConfig.provider}
                    onChange={(e) => setChatConfig(prev => ({ ...prev, provider: e.target.value }))}
                    className="w-full rounded-lg border border-input bg-background px-4 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="gemini">Gemini</option>
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-foreground">Modelo</label>
                  <input
                    type="text"
                    value={chatConfig.model}
                    onChange={(e) => setChatConfig(prev => ({ ...prev, model: e.target.value }))}
                    className="w-full rounded-lg border border-input bg-background px-4 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-foreground">Temperatura ({chatConfig.temperature})</label>
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    value={chatConfig.temperature}
                    onChange={(e) => setChatConfig(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-foreground">Top P ({chatConfig.top_p})</label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={chatConfig.top_p}
                    onChange={(e) => setChatConfig(prev => ({ ...prev, top_p: parseFloat(e.target.value) }))}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-foreground">Max Tokens</label>
                  <input
                    type="number"
                    min="1"
                    max="8192"
                    value={chatConfig.max_tokens}
                    onChange={(e) => setChatConfig(prev => ({ ...prev, max_tokens: parseInt(e.target.value) }))}
                    className="w-full rounded-lg border border-input bg-background px-4 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
              <button
                onClick={saveChatConfig}
                disabled={savingSettings}
                className="mt-4 flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                {savingSettings && <Loader2 className="h-4 w-4 animate-spin" />}
                <Save className="h-4 w-4" />
                Guardar Configuracion
              </button>
            </div>

            {settingsMsg && (
              <div className={`rounded-lg p-3 text-sm ${
                settingsMsg.includes('Error')
                  ? 'bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400'
                  : 'bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400'
              }`}>
                {settingsMsg}
              </div>
            )}
          </div>
        )}

        {/* Graph Tab */}
        {activeTab === 'graph' && !loading && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-foreground">Grafo de Entidades Global</h2>
            <EntityGraph />
          </div>
        )}
      </main>
    </div>
  )
}

function StatCard({ label, value, icon: Icon, color }: { label: string; value: string | number; icon: any; color: string }) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400',
    green: 'bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400',
    purple: 'bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400',
    orange: 'bg-orange-50 text-orange-600 dark:bg-orange-900/20 dark:text-orange-400',
    red: 'bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400',
  }
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{label}</p>
        <div className={`rounded-lg p-2 ${colors[color] || colors.blue}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <p className="mt-2 text-2xl font-bold text-foreground">{value}</p>
    </div>
  )
}

function ResourceCard({ label, value, used, total, unit, icon: Icon, color }: {
  label: string; value: number; used?: number; total?: number; unit?: string; icon: any; color: string
}) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-500',
    purple: 'bg-purple-500',
    green: 'bg-green-500',
    red: 'bg-red-500',
    orange: 'bg-orange-500',
  }
  const barColor = colors[color] || colors.blue
  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="flex items-center gap-3">
        <div className={`rounded-lg p-2 ${color === 'blue' ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20' : color === 'purple' ? 'bg-purple-50 text-purple-600 dark:bg-purple-900/20' : 'bg-green-50 text-green-600 dark:bg-green-900/20'}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm font-medium text-foreground">{label}</p>
          <p className="text-xs text-muted-foreground">
            {used !== undefined && total !== undefined ? `${used.toFixed(1)} / ${total.toFixed(1)} ${unit || ''}` : ''}
          </p>
        </div>
      </div>
      <div className="mt-4 h-2 w-full rounded-full bg-muted">
        <div
          className={`h-2 rounded-full transition-all ${barColor}`}
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
      <p className="mt-2 text-right text-sm font-medium text-foreground">{value.toFixed(1)}%</p>
    </div>
  )
}
