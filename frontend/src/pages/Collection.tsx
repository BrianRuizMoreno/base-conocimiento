import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { client } from '../lib/client'
import { useAuth } from '../context/AuthContext'
import {
  ArrowLeft, Upload, FileText, Trash2, MessageSquare, BarChart3, Share2,
  Loader2, AlertCircle, CheckCircle2, Clock, File, Image, Music, Video
} from 'lucide-react'
import EntityGraph from '../components/EntityGraph'

interface DocumentItem {
  id: string
  filename: string
  file_type: string
  file_size: number
  status: string
  created_at: string
}

const fileTypeIcons: Record<string, any> = {
  pdf: FileText,
  docx: FileText,
  md: FileText,
  json: FileText,
  xml: FileText,
  image: Image,
  audio: Music,
  video: Video,
}

function formatBytes(bytes: number) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export default function Collection() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [collection, setCollection] = useState<any>(null)
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [uploadSuccess, setUploadSuccess] = useState('')
  const [activeTab, setActiveTab] = useState('documents')

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/')
      return
    }
    if (id) {
      fetchData()
    }
  }, [id, isAuthenticated])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [colRes, docsRes] = await Promise.all([
        client.get(`/v1/collections/${id}`),
        client.get(`/v1/documents/collections/${id}/documents`)
      ])
      if (colRes.data.success) {
        setCollection(colRes.data.data)
      }
      if (docsRes.data.success) {
        setDocuments(docsRes.data.data || [])
      }
    } catch (err) {
      console.error('Error fetching collection:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setUploadError('')
    setUploadSuccess('')

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await client.post(`/v1/documents/collections/${id}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      if (response.data.success) {
        setUploadSuccess(`"${file.name}" subido correctamente`)
        fetchData()
      } else {
        setUploadError(response.data.error || 'Error al subir archivo')
      }
    } catch (err: any) {
      setUploadError(err.response?.data?.error || 'Error al subir archivo')
    } finally {
      setUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const deleteDocument = async (docId: string) => {
    if (!confirm('Eliminar este documento?')) return
    try {
      await client.delete(`/v1/documents/${docId}`)
      fetchData()
    } catch (err) {
      console.error('Error deleting document:', err)
    }
  }

  if (!isAuthenticated) return null

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-4">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-foreground hover:bg-accent"
          >
            <ArrowLeft className="h-4 w-4" />
            Volver
          </button>
          {loading ? (
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          ) : (
            <div className="flex-1">
              <h1 className="text-xl font-bold text-foreground">{collection?.name || 'Coleccion'}</h1>
              {collection?.description && (
                <p className="text-sm text-muted-foreground">{collection.description}</p>
              )}
            </div>
          )}
          <div className="flex gap-2">
            <a
              href={`/collection/${id}/chat`}
              className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
            >
              <MessageSquare className="h-4 w-4" />
              Chat
            </a>
            <a
              href={`/collection/${id}/analysis`}
              className="flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm text-foreground hover:bg-accent"
            >
              <BarChart3 className="h-4 w-4" />
              Analisis
            </a>
          </div>
        </div>
        <div className="mx-auto flex max-w-7xl gap-1 px-4">
          <button
            onClick={() => setActiveTab('documents')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'documents'
                ? 'border-b-2 border-primary-600 text-primary-600'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <FileText className="h-4 w-4" />
            Documentos
          </button>
          <button
            onClick={() => setActiveTab('graph')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'graph'
                ? 'border-b-2 border-primary-600 text-primary-600'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Share2 className="h-4 w-4" />
            Grafo de Entidades
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl p-6">
        {activeTab === 'documents' && (
          <>
            {/* Upload */}
            <div className="rounded-xl border border-border bg-card p-6">
              <h2 className="mb-4 text-lg font-semibold text-foreground">Subir Documento</h2>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
                <input
                  ref={fileInputRef}
                  type="file"
                  onChange={handleFileChange}
                  className="block w-full text-sm text-foreground file:mr-4 file:rounded-lg file:border-0 file:bg-primary-600 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-primary-700"
                  disabled={uploading}
                />
                {uploading && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Subiendo...
                  </div>
                )}
              </div>
              {uploadError && (
                <div className="mt-3 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
                  <AlertCircle className="h-4 w-4" />
                  {uploadError}
                </div>
              )}
              {uploadSuccess && (
                <div className="mt-3 flex items-center gap-2 rounded-lg bg-green-50 p-3 text-sm text-green-600 dark:bg-green-900/20 dark:text-green-400">
                  <CheckCircle2 className="h-4 w-4" />
                  {uploadSuccess}
                </div>
              )}
            </div>

            {/* Documents */}
            <div className="mt-6 rounded-xl border border-border bg-card p-6">
              <h2 className="mb-4 text-lg font-semibold text-foreground">
                Documentos ({documents.length})
              </h2>

              {documents.length === 0 ? (
                <div className="rounded-lg bg-muted p-8 text-center">
                  <Upload className="mx-auto h-10 w-10 text-muted-foreground" />
                  <p className="mt-3 text-sm text-muted-foreground">No hay documentos en esta coleccion.</p>
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {documents.map((doc) => {
                    const Icon = fileTypeIcons[doc.file_type] || File
                    return (
                      <div key={doc.id} className="flex items-center justify-between py-4">
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                            <Icon className="h-5 w-5 text-muted-foreground" />
                          </div>
                          <div>
                            <p className="font-medium text-foreground">{doc.filename}</p>
                            <div className="flex items-center gap-3 text-xs text-muted-foreground">
                              <span>{formatBytes(doc.file_size)}</span>
                              <span className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                {new Date(doc.created_at).toLocaleDateString()}
                              </span>
                              <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                                doc.status === 'completed'
                                  ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300'
                                  : doc.status === 'processing'
                                  ? 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-300'
                                  : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300'
                              }`}>
                                {doc.status === 'completed' && <CheckCircle2 className="h-3 w-3" />}
                                {doc.status === 'processing' && <Loader2 className="h-3 w-3 animate-spin" />}
                                {doc.status === 'error' && <AlertCircle className="h-3 w-3" />}
                                {doc.status}
                              </span>
                            </div>
                          </div>
                        </div>
                        <button
                          onClick={() => deleteDocument(doc.id)}
                          className="rounded-lg p-2 text-muted-foreground hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </>
        )}

        {activeTab === 'graph' && id && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-foreground">Grafo de Entidades</h2>
            <EntityGraph collectionId={id} />
          </div>
        )}
      </main>
    </div>
  )
}
