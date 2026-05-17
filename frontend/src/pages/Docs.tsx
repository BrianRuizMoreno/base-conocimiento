export default function Docs() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-7xl items-center px-4 py-4">
          <a href="/" className="text-xl font-bold text-foreground hover:text-primary-600">
            RAG System
          </a>
        </div>
      </header>
      <main className="mx-auto max-w-4xl p-6">
        <h1 className="mb-6 text-3xl font-bold text-foreground">Documentacion</h1>
        <div className="space-y-8">
          <section className="rounded-xl border border-border bg-card p-6">
            <h2 className="mb-3 text-xl font-semibold text-foreground">Que es RAG System?</h2>
            <p className="text-muted-foreground">
              Sistema de Recuperacion Aumentada por Generacion (RAG) para gestionar conocimiento empresarial.
              Permite subir documentos, procesarlos con IA y consultarlos mediante chat inteligente.
            </p>
          </section>

          <section className="rounded-xl border border-border bg-card p-6">
            <h2 className="mb-3 text-xl font-semibold text-foreground">Endpoints de API</h2>
            <div className="space-y-3">
              <div className="rounded-lg bg-muted p-3">
                <code className="text-sm font-semibold text-primary-600">POST /api/v1/auth/verify</code>
                <p className="mt-1 text-sm text-muted-foreground">Verificar PIN de administrador</p>
              </div>
              <div className="rounded-lg bg-muted p-3">
                <code className="text-sm font-semibold text-primary-600">GET /api/v1/collections</code>
                <p className="mt-1 text-sm text-muted-foreground">Listar colecciones</p>
              </div>
              <div className="rounded-lg bg-muted p-3">
                <code className="text-sm font-semibold text-primary-600">POST /api/v1/collections</code>
                <p className="mt-1 text-sm text-muted-foreground">Crear coleccion</p>
              </div>
              <div className="rounded-lg bg-muted p-3">
                <code className="text-sm font-semibold text-primary-600">POST /api/v1/documents/collections/&#123;id&#125;/upload</code>
                <p className="mt-1 text-sm text-muted-foreground">Subir documento</p>
              </div>
              <div className="rounded-lg bg-muted p-3">
                <code className="text-sm font-semibold text-primary-600">POST /api/v1/chat/collections/&#123;id&#125;/chat</code>
                <p className="mt-1 text-sm text-muted-foreground">Chat con coleccion</p>
              </div>
              <div className="rounded-lg bg-muted p-3">
                <code className="text-sm font-semibold text-primary-600">GET /api/v1/admin/metrics</code>
                <p className="mt-1 text-sm text-muted-foreground">Metricas del sistema</p>
              </div>
            </div>
          </section>

          <section className="rounded-xl border border-border bg-card p-6">
            <h2 className="mb-3 text-xl font-semibold text-foreground">Formatos soportados</h2>
            <ul className="list-inside list-disc space-y-1 text-muted-foreground">
              <li>PDF</li>
              <li>Word (DOCX)</li>
              <li>Markdown (MD)</li>
              <li>JSON / XML</li>
              <li>Imagenes (JPEG, PNG)</li>
              <li>Audio (MP3)</li>
              <li>Video (MP4)</li>
            </ul>
          </section>
        </div>
      </main>
    </div>
  )
}
