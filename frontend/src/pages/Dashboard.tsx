import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { client } from '../lib/client'
import {
  Database, Settings, BookOpen, Plus, MessageSquare, BarChart3,
  Loader2, Trash2, Server, CheckCircle2
} from 'lucide-react'

interface CollectionItem {
  id: string
  name: string
  description: string | null
  created_at: string
}

export default function Dashboard() {
  const { isAuthenticated, login, logout } = useAuth()
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [collections, setCollections] = useState<CollectionItem[]>([])
  const [collectionsLoading, setCollectionsLoading] = useState(false)
  const [health, setHealth] = useState<any>(null)

  useEffect(() => {
    if (isAuthenticated) {
      fetchCollections()
      fetchHealth()
    }
  }, [isAuthenticated])

  const fetchCollections = async () => {
    setCollectionsLoading(true)
    try {
      const response = await client.get('/v1/collections')
      if (response.data.success) {
        setCollections(response.data.data || [])
      }
    } catch (err) {
      console.error('Error fetching collections:', err)
    } finally {
      setCollectionsLoading(false)
    }
  }

  const fetchHealth = async () => {
    try {
      const response = await client.get('/v1/health')
      setHealth(response.data)
    } catch (err) {
      console.error('Error fetching health:', err)
    }
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const response = await client.post('/v1/auth/verify', { pin })
      if (response.data.success) {
        login(pin)
      } else {
        setError(response.data.error || 'PIN invalido')
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error de conexion')
    } finally {
      setLoading(false)
    }
  }

  const deleteCollection = async (id: string) => {
    if (!confirm('Eliminar esta coleccion?')) return
    try {
      await client.delete(`/v1/collections/${id}`)
      fetchCollections()
    } catch (err) {
      console.error('Error deleting collection:', err)
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="w-full max-w-sm space-y-6 p-8">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-foreground">RAG System</h1>
            <p className="mt-2 text-muted-foreground">Sistema de conocimiento empresarial</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label htmlFor="pin-input" className="sr-only">PIN de acceso</label>
              <input
                id="pin-input"
                type="password"
                value={pin}
                onChange={(e) => setPin(e.target.value)}
                placeholder="Ingresa tu PIN"
                aria-describedby="pin-error"
                className="w-full rounded-lg border border-input bg-background px-4 py-3 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary-500"
                maxLength={10}
              />
            </div>
            <div id="pin-error" aria-live="polite" className="sr-only">
              {error}
            </div>

            {error && (
              <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !pin}
              className="w-full rounded-lg bg-primary-600 px-4 py-3 font-medium text-white transition-colors hover:bg-primary-700 disabled:opacity-50"
            >
              {loading ? 'Verificando...' : 'Entrar'}
            </button>
          </form>

          <div className="text-center text-xs text-muted-foreground">
            <p>V 1.0.0 - Fase 6</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
          <h1 className="text-xl font-bold text-foreground">RAG System</h1>
          <div className="flex items-center gap-4">
            <Link
              to="/admin"
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
            >
              Admin
            </Link>
            <button
              onClick={logout}
              className="rounded-lg border border-border px-4 py-2 text-sm text-foreground hover:bg-accent"
            >
              Salir
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="mx-auto max-w-7xl p-6">
        {/* Quick Actions */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Link
            to="/collection/new"
            className="group rounded-xl border border-border bg-card p-6 transition-colors hover:border-primary-500"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100 text-primary-600 dark:bg-primary-900/20">
              <Plus className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-lg font-semibold text-foreground">Nueva Coleccion</h3>
            <p className="mt-2 text-sm text-muted-foreground">Crear una base de conocimiento</p>
          </Link>

          <Link
            to="/admin"
            className="group rounded-xl border border-border bg-card p-6 transition-colors hover:border-primary-500"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100 text-primary-600 dark:bg-primary-900/20">
              <Settings className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-lg font-semibold text-foreground">Configuracion</h3>
            <p className="mt-2 text-sm text-muted-foreground">API keys, modelos, parametros</p>
          </Link>

          <Link
            to="/docs"
            className="group rounded-xl border border-border bg-card p-6 transition-colors hover:border-primary-500"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100 text-primary-600 dark:bg-primary-900/20">
              <BookOpen className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-lg font-semibold text-foreground">Documentacion</h3>
            <p className="mt-2 text-sm text-muted-foreground">Guia de uso y API</p>
          </Link>
        </div>

        {/* Collections */}
        <div className="mt-8 rounded-xl border border-border bg-card p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-foreground">Colecciones</h2>
            {collectionsLoading && <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />}
          </div>

          {collections.length === 0 && !collectionsLoading ? (
            <div className="rounded-lg bg-muted p-8 text-center">
              <Database className="mx-auto h-10 w-10 text-muted-foreground" />
              <p className="mt-3 text-sm text-muted-foreground">No hay colecciones. Crea una nueva para comenzar.</p>
              <Link
                to="/collection/new"
                className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
              >
                <Plus className="h-4 w-4" />
                Nueva Coleccion
              </Link>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {collections.map((c) => (
                <div
                  key={c.id}
                  className="group relative rounded-lg border border-border bg-background p-4 transition-colors hover:border-primary-500"
                >
                  <div className="flex items-start justify-between">
                    <Link to={`/collection/${c.id}`} className="flex-1">
                      <h3 className="font-semibold text-foreground">{c.name}</h3>
                      {c.description && (
                        <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{c.description}</p>
                      )}
                      <p className="mt-2 text-xs text-muted-foreground">
                        {new Date(c.created_at).toLocaleDateString()}
                      </p>
                    </Link>
                    <button
                      onClick={() => deleteCollection(c.id)}
                      className="ml-2 rounded p-1 text-muted-foreground hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="mt-3 flex gap-2">
                    <Link
                      to={`/collection/${c.id}/chat`}
                      className="inline-flex items-center gap-1 rounded-md bg-primary-50 px-2 py-1 text-xs font-medium text-primary-700 dark:bg-primary-900/20 dark:text-primary-300"
                    >
                      <MessageSquare className="h-3 w-3" />
                      Chat
                    </Link>
                    <Link
                      to={`/collection/${c.id}/analysis`}
                      className="inline-flex items-center gap-1 rounded-md bg-secondary px-2 py-1 text-xs font-medium text-secondary-foreground"
                    >
                      <BarChart3 className="h-3 w-3" />
                      Analisis
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Status */}
        <div className="mt-8 rounded-xl border border-border bg-card p-6">
          <h2 className="text-lg font-semibold text-foreground">Estado del Sistema</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div className="rounded-lg bg-green-50 p-4 dark:bg-green-900/20">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
                <p className="text-sm text-green-600 dark:text-green-400">Backend</p>
              </div>
              <p className="mt-1 text-lg font-semibold text-green-700 dark:text-green-300">
                {health?.status === 'ok' ? 'Online' : 'Offline'}
              </p>
            </div>
            <div className="rounded-lg bg-blue-50 p-4 dark:bg-blue-900/20">
              <div className="flex items-center gap-2">
                <Database className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                <p className="text-sm text-blue-600 dark:text-blue-400">Base de Datos</p>
              </div>
              <p className="mt-1 text-lg font-semibold text-blue-700 dark:text-blue-300">
                {health?.database === 'connected' ? 'Conectada' : 'Desconectada'}
              </p>
            </div>
            <div className="rounded-lg bg-purple-50 p-4 dark:bg-purple-900/20">
              <div className="flex items-center gap-2">
                <Server className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                <p className="text-sm text-purple-600 dark:text-purple-400">Version</p>
              </div>
              <p className="mt-1 text-lg font-semibold text-purple-700 dark:text-purple-300">
                {health?.version || '1.0.0'}
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
