import { useState } from 'react'
import { useAuth } from '../context/AuthContext'

export default function Dashboard() {
  const { login, isAuthenticated } = useAuth()
  const [pin, setPin] = useState('')

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    // TODO: Verify PIN with API
    login(pin)
  }

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <form onSubmit={handleLogin} className="w-full max-w-sm space-y-4 p-6">
          <h1 className="text-2xl font-bold text-center">RAG System</h1>
          <input
            type="password"
            value={pin}
            onChange={(e) => setPin(e.target.value)}
            placeholder="Ingresa tu PIN"
            className="w-full rounded-lg border px-4 py-2"
          />
          <button type="submit" className="w-full rounded-lg bg-primary-600 px-4 py-2 text-white">
            Entrar
          </button>
        </form>
      </div>
    )
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <p className="text-muted-foreground">Bienvenido al sistema RAG</p>
      {/* TODO: Collection list, stats */}
    </div>
  )
}
