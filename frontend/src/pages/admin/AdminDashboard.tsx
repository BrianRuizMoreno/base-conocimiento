import { useState } from 'react'

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('dashboard')

  const tabs = [
    { id: 'dashboard', label: '📊 Dashboard' },
    { id: 'tokens', label: '🪙 Tokens' },
    { id: 'server', label: '💾 Servidor' },
    { id: 'errors', label: '❌ Errores' },
    { id: 'executions', label: '📋 Ejecuciones' },
    { id: 'settings', label: '⚙️ Configuración' },
  ]

  return (
    <div className="min-h-screen bg-background">
      <div className="border-b">
        <div className="flex gap-1 px-4 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-b-2 border-primary-600 text-primary-600'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      <div className="p-6">
        {/* TODO: Render active tab content */}
        <div className="text-muted-foreground">
          Pestaña activa: <strong>{tabs.find(t => t.id === activeTab)?.label}</strong>
        </div>
      </div>
    </div>
  )
}
