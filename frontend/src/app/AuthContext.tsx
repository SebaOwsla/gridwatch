import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { demoUser } from '../lib/demo'
import { getMe, login as apiLogin } from '../lib/api'
import type { User } from '../lib/types'

type AuthState =
  | { mode: 'demo'; user: User }
  | { mode: 'api'; user: User; token: string }

interface AuthContextValue {
  auth: AuthState | null
  checking: boolean
  login: (email: string, password: string) => Promise<void>
  enterDemo: () => void
  logout: () => void
}

const STORAGE_KEY = 'gridwatch-session'
const STATIC_DEMO = import.meta.env.VITE_STATIC_DEMO === 'true'
const AuthContext = createContext<AuthContextValue | null>(null)

function storedSession(): AuthState | null {
  if (STATIC_DEMO) return { mode: 'demo', user: demoUser }
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const value = JSON.parse(raw) as AuthState
    if (value.mode === 'demo') return { mode: 'demo', user: demoUser }
    if (value.mode === 'api' && typeof value.token === 'string' && value.user) return value
  } catch {
    sessionStorage.removeItem(STORAGE_KEY)
  }
  return null
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState | null>(storedSession)
  const [checking, setChecking] = useState(auth?.mode === 'api')

  useEffect(() => {
    if (auth?.mode !== 'api') return
    let active = true
    getMe(auth.token)
      .then((user) => {
        if (!active) return
        const next: AuthState = { mode: 'api', user, token: auth.token }
        setAuth(next)
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next))
      })
      .catch(() => {
        if (!active) return
        setAuth(null)
        sessionStorage.removeItem(STORAGE_KEY)
      })
      .finally(() => { if (active) setChecking(false) })
    return () => { active = false }
    // Check only the restored token, not every refresh of the user object.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function login(email: string, password: string) {
    const token = await apiLogin(email, password)
    const user = await getMe(token)
    const next: AuthState = { mode: 'api', user, token }
    setAuth(next)
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  }

  function enterDemo() {
    const next: AuthState = { mode: 'demo', user: demoUser }
    setAuth(next)
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  }

  function logout() {
    setAuth(null)
    sessionStorage.removeItem(STORAGE_KEY)
  }

  return <AuthContext.Provider value={{ auth, checking, login, enterDemo, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}

export const canManage = (auth: AuthState | null) =>
  auth?.mode === 'api' && (auth.user.role === 'admin' || auth.user.role === 'operator')
