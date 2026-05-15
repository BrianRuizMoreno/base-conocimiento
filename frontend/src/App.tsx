import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Collection from './pages/Collection'
import Chat from './pages/Chat'
import Analysis from './pages/Analysis'
import AdminDashboard from './pages/admin/AdminDashboard'
import Docs from './pages/Docs'

function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/collection/:id" element={<Collection />} />
        <Route path="/collection/:id/chat" element={<Chat />} />
        <Route path="/collection/:id/analysis" element={<Analysis />} />
        <Route path="/admin/*" element={<AdminDashboard />} />
        <Route path="/docs" element={<Docs />} />
      </Routes>
    </div>
  )
}

export default App
