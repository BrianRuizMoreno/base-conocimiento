import { useState, useRef, useEffect, useCallback } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { client } from '../lib/client'
import { useAuth } from '../context/AuthContext'
import {
  ArrowLeft, Send, Loader2, User, Bot,
  AlertCircle, SlidersHorizontal, Image as ImageIcon,
  Plus, MoreVertical, Pencil, Trash2, Globe,
  PanelLeftClose, PanelLeft, MessageSquare
} from 'lucide-react'

interface RelatedMedia {
  type: string
  url: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
  related_media?: RelatedMedia[]
  model?: string
  tokens_used?: number
}

interface Conversation {
  id: string
  collection_id: string
  title: string
  created_at: string
  updated_at: string
}

export default function Chat() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated } = useAuth()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showSettings, setShowSettings] = useState(false)
  const [temperature, setTemperature] = useState(0.2)
  const [topP, setTopP] = useState(0.6)

  // Conversations sidebar
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [loadingConversations, setLoadingConversations] = useState(false)

  // Rename modal
  const [renameModalOpen, setRenameModalOpen] = useState(false)
  const [renameConversationId, setRenameConversationId] = useState<string | null>(null)
  const [renameTitle, setRenameTitle] = useState('')

  // Web search toggle
  const [webSearch, setWebSearch] = useState(false)

  // Active menu for conversation actions
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/')
    }
  }, [isAuthenticated, navigate])

  // Handle initial question from navigation state (e.g. clicking a tag in Analysis)
  useEffect(() => {
    const initialQuestion = (location.state as any)?.initialQuestion
    if (initialQuestion && id) {
      // Create a new conversation first if none selected
      if (!selectedConversationId) {
        client.post('/v1/conversations', {
          collection_id: id,
          title: null
        }).then(response => {
          if (response.data.success) {
            const newConv = response.data.data
            setConversations(prev => [newConv, ...prev])
            setSelectedConversationId(newConv.id)
            sendMessage(initialQuestion)
          }
        }).catch(err => {
          console.error('Error creating conversation:', err)
        })
      } else {
        sendMessage(initialQuestion)
      }
      // Clear the state so it doesn't re-trigger
      navigate(location.pathname, { replace: true, state: {} })
    }
  }, [location.state, id]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Load conversations when collection changes
  const loadConversations = useCallback(async () => {
    if (!id) return
    setLoadingConversations(true)
    try {
      const response = await client.get('/v1/conversations', {
        params: { collection_id: id }
      })
      if (response.data.success) {
        setConversations(response.data.data || [])
      }
    } catch (err: any) {
      console.error('Error loading conversations:', err)
    } finally {
      setLoadingConversations(false)
    }
  }, [id])

  useEffect(() => {
    loadConversations()
  }, [loadConversations])

  // Close sidebar when selecting a conversation on mobile
  const handleSelectConversation = async (conversationId: string) => {
    setSelectedConversationId(conversationId)
    setSidebarOpen(false)
    setMessages([])
    setError('')

    try {
      const response = await client.get(`/v1/conversations/${conversationId}`)
      if (response.data.success) {
        const data = response.data.data
        const loadedMessages: Message[] = (data.messages || []).map((m: any) => ({
          role: m.role as 'user' | 'assistant',
          content: m.content,
          sources: m.sources,
          related_media: m.related_media,
          model: m.model,
          tokens_used: m.tokens_used,
        }))
        setMessages(loadedMessages)
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error cargando conversacion')
    }
  }

  const handleNewConversation = async () => {
    if (!id) return
    try {
      const response = await client.post('/v1/conversations', {
        collection_id: id,
        title: null
      })
      if (response.data.success) {
        const newConv: Conversation = response.data.data
        setConversations(prev => [newConv, ...prev])
        setSelectedConversationId(newConv.id)
        setMessages([])
        setSidebarOpen(false)
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error creando conversacion')
    }
  }

  const handleDeleteConversation = async (conversationId: string) => {
    if (!confirm('¿Eliminar esta conversacion?')) return
    try {
      const response = await client.delete(`/v1/conversations/${conversationId}`)
      if (response.data.success) {
        setConversations(prev => prev.filter(c => c.id !== conversationId))
        if (selectedConversationId === conversationId) {
          setSelectedConversationId(null)
          setMessages([])
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error eliminando conversacion')
    }
    setActiveMenuId(null)
  }

  const openRenameModal = (conversationId: string, currentTitle: string) => {
    setRenameConversationId(conversationId)
    setRenameTitle(currentTitle || '')
    setRenameModalOpen(true)
    setActiveMenuId(null)
  }

  const handleRenameConversation = async () => {
    if (!renameConversationId || !renameTitle.trim()) return
    try {
      const response = await client.patch(`/v1/conversations/${renameConversationId}`, {
        title: renameTitle.trim()
      })
      if (response.data.success) {
        setConversations(prev => prev.map(c =>
          c.id === renameConversationId ? { ...c, title: renameTitle.trim() } : c
        ))
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error renombrando conversacion')
    }
    setRenameModalOpen(false)
    setRenameConversationId(null)
    setRenameTitle('')
  }

  const sendMessage = async (overrideQuestion?: string) => {
    const question = overrideQuestion?.trim() || input.trim()
    if (!question || loading || !id) return

    setInput('')
    setError('')
    setLoading(true)

    const userMsg: Message = { role: 'user', content: question }
    setMessages(prev => [...prev, userMsg])

    try {
      const payload: any = {
        question,
        temperature,
        top_p: topP,
        web_search: webSearch,
      }
      if (selectedConversationId) {
        payload.conversation_id = selectedConversationId
      }

      const response = await client.post(`/v1/collections/${id}/chat`, payload)

      if (response.data.success) {
        const data = response.data.data
        const assistantMsg: Message = {
          role: 'assistant',
          content: data.answer || 'Sin respuesta',
          sources: data.sources || [],
          related_media: data.related_media || [],
          model: data.model,
          tokens_used: data.tokens_used
        }
        setMessages(prev => [...prev, assistantMsg])

        // Update conversation title if auto-generated
        if (data.conversation_id && data.conversation_title) {
          setConversations(prev => prev.map(c =>
            c.id === data.conversation_id
              ? { ...c, title: data.conversation_title }
              : c
          ))
        }
      } else {
        setError(response.data.error || 'Error en la respuesta')
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error de conexion')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('es-ES', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (!isAuthenticated) return null

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-72 transform border-r border-border bg-card transition-transform duration-200 ease-in-out md:relative md:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-full flex-col">
          {/* Sidebar header */}
          <div className="flex items-center gap-2 border-b border-border p-4">
            <button
              onClick={() => navigate(`/collection/${id}`)}
              className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-foreground hover:bg-accent"
            >
              <ArrowLeft className="h-4 w-4" />
              Volver
            </button>
            <button
              onClick={() => setSidebarOpen(false)}
              className="ml-auto rounded-lg p-2 text-muted-foreground hover:bg-accent md:hidden"
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>
          </div>

          {/* New conversation button */}
          <div className="p-3">
            <button
              onClick={handleNewConversation}
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-border bg-background px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-accent"
            >
              <Plus className="h-4 w-4" />
              Nueva conversacion
            </button>
          </div>

          {/* Conversations list */}
          <div className="flex-1 overflow-y-auto px-3 pb-3">
            {loadingConversations ? (
              <div className="flex justify-center py-4">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : conversations.length === 0 ? (
              <div className="py-8 text-center text-sm text-muted-foreground">
                <MessageSquare className="mx-auto mb-2 h-8 w-8 opacity-50" />
                No hay conversaciones
              </div>
            ) : (
              <div className="space-y-1">
                {conversations.map((conv) => (
                  <div
                    key={conv.id}
                    className={`group relative flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                      selectedConversationId === conv.id
                        ? 'bg-primary-100 text-primary-900 dark:bg-primary-900/20 dark:text-primary-100'
                        : 'text-foreground hover:bg-accent'
                    }`}
                    onClick={() => handleSelectConversation(conv.id)}
                  >
                    <MessageSquare className="h-4 w-4 shrink-0 opacity-70" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">{conv.title || 'Nueva conversacion'}</p>
                      <p className="text-xs text-muted-foreground">{formatDate(conv.updated_at)}</p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setActiveMenuId(activeMenuId === conv.id ? null : conv.id)
                      }}
                      className="rounded p-1 opacity-0 transition-opacity hover:bg-muted group-hover:opacity-100"
                    >
                      <MoreVertical className="h-3.5 w-3.5" />
                    </button>

                    {/* Action menu */}
                    {activeMenuId === conv.id && (
                      <>
                        <div
                          className="fixed inset-0 z-30"
                          onClick={() => setActiveMenuId(null)}
                        />
                        <div className="absolute right-2 top-10 z-40 w-40 rounded-lg border border-border bg-card p-1 shadow-lg">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              openRenameModal(conv.id, conv.title)
                            }}
                            className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-foreground hover:bg-accent"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                            Renombrar
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleDeleteConversation(conv.id)
                            }}
                            className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Eliminar
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col">
        {/* Header */}
        <header className="border-b border-border bg-card">
          <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="rounded-lg border border-border p-2 text-foreground hover:bg-accent md:hidden"
            >
              <PanelLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="hidden rounded-lg border border-border p-2 text-foreground hover:bg-accent md:block"
            >
              <PanelLeft className="h-4 w-4" />
            </button>
            <h1 className="flex-1 text-lg font-bold text-foreground">
              {selectedConversationId
                ? conversations.find(c => c.id === selectedConversationId)?.title || 'Chat'
                : 'Chat'}
            </h1>

            {/* Web search toggle */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setWebSearch(!webSearch)}
                className={`flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${
                  webSearch
                    ? 'border-primary-500 bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-300'
                    : 'border-border bg-background text-muted-foreground hover:bg-accent'
                }`}
                title="Buscar en internet"
              >
                <Globe className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Buscar en internet</span>
                <span className="sm:hidden">Web</span>
              </button>
              <button
                onClick={() => setShowSettings(!showSettings)}
                className="rounded-lg border border-border px-3 py-2 text-sm text-foreground hover:bg-accent"
              >
                <SlidersHorizontal className="h-4 w-4" />
              </button>
            </div>
          </div>
        </header>

        {/* Settings panel */}
        {showSettings && (
          <div className="border-b border-border bg-card px-4 py-3">
            <div className="mx-auto max-w-5xl">
              <div className="flex flex-wrap items-center gap-6">
                <div className="flex items-center gap-3">
                  <label className="text-sm font-medium text-foreground">Temperatura</label>
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    value={temperature}
                    onChange={(e) => setTemperature(parseFloat(e.target.value))}
                    className="w-32"
                  />
                  <span className="w-10 text-sm text-muted-foreground">{temperature}</span>
                </div>
                <div className="flex items-center gap-3">
                  <label className="text-sm font-medium text-foreground">Top P</label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={topP}
                    onChange={(e) => setTopP(parseFloat(e.target.value))}
                    className="w-32"
                  />
                  <span className="w-10 text-sm text-muted-foreground">{topP}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="mx-auto max-w-5xl space-y-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <Bot className="h-12 w-12 text-muted-foreground" />
                <h2 className="mt-4 text-xl font-semibold text-foreground">
                  {selectedConversationId ? 'Continua la conversacion' : 'Inicia la conversacion'}
                </h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  Haz preguntas sobre los documentos de esta coleccion.
                  {webSearch && (
                    <span className="block mt-1 text-primary-600 dark:text-primary-400">
                      La busqueda en internet esta activada.
                    </span>
                  )}
                </p>
              </div>
            )}

            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/20">
                    <Bot className="h-4 w-4 text-primary-600" />
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-3 sm:max-w-[80%] ${
                    msg.role === 'user'
                      ? 'bg-primary-600 text-white'
                      : 'border border-border bg-card text-foreground'
                  }`}
                >
                  <p className="whitespace-pre-wrap text-sm">{msg.content}</p>

                  {/* Related images */}
                  {msg.role === 'assistant' && msg.related_media && msg.related_media.length > 0 && (
                    <div className="mt-3 space-y-2">
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <ImageIcon className="h-3 w-3" />
                        <span>Imagenes relacionadas:</span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {msg.related_media.map((media, idx) => (
                          <a
                            key={idx}
                            href={media.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="group relative overflow-hidden rounded-lg border border-border hover:border-primary-500"
                          >
                            <img
                              src={media.url}
                              alt="Imagen relacionada"
                              className="h-24 w-24 object-cover transition-transform group-hover:scale-105"
                              onError={(e) => {
                                (e.target as HTMLImageElement).style.display = 'none'
                              }}
                            />
                          </a>
                        ))}
                      </div>
                    </div>
                  )}

                  {msg.role === 'assistant' && (
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      {msg.model && <span className="rounded bg-muted px-1.5 py-0.5">{msg.model}</span>}
                      {msg.tokens_used && <span>{msg.tokens_used} tokens</span>}
                    </div>
                  )}
                </div>
                {msg.role === 'user' && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary">
                    <User className="h-4 w-4 text-secondary-foreground" />
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/20">
                  <Bot className="h-4 w-4 text-primary-600" />
                </div>
                <div className="rounded-2xl border border-border bg-card px-4 py-3">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              </div>
            )}

            {error && (
              <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
                <AlertCircle className="h-4 w-4" />
                {error}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <div className="border-t border-border bg-card p-4">
          <div className="mx-auto flex max-w-5xl gap-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Escribe tu pregunta..."
              rows={1}
              className="max-h-32 min-h-[44px] flex-1 resize-none rounded-lg border border-input bg-background px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <button
              onClick={() => sendMessage()}
              disabled={loading || !input.trim()}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-primary-600 text-white transition-colors hover:bg-primary-700 disabled:opacity-50"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* Overlay for mobile sidebar */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Rename modal */}
      {renameModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-sm rounded-lg border border-border bg-card p-6 shadow-lg">
            <h3 className="mb-4 text-lg font-semibold text-foreground">Renombrar conversacion</h3>
            <input
              type="text"
              value={renameTitle}
              onChange={(e) => setRenameTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleRenameConversation()
                if (e.key === 'Escape') setRenameModalOpen(false)
              }}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary-500"
              autoFocus
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setRenameModalOpen(false)}
                className="rounded-lg border border-border px-4 py-2 text-sm text-foreground hover:bg-accent"
              >
                Cancelar
              </button>
              <button
                onClick={handleRenameConversation}
                className="rounded-lg bg-primary-600 px-4 py-2 text-sm text-white hover:bg-primary-700"
              >
                Guardar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
