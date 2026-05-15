import { createContext, useContext, useState, ReactNode } from 'react'

interface AuthContextType {
  isAuthenticated: boolean
  pin: string | null
  login: (pin: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [pin, setPin] = useState<string | null>(() => localStorage.getItem('pin'))
  const isAuthenticated = !!pin

  const login = (newPin: string) => {
    localStorage.setItem('pin', newPin)
    setPin(newPin)
  }

  const logout = () => {
    localStorage.removeItem('pin')
    setPin(null)
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, pin, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
