import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuth } from '../app/AuthContext'
import { getTrend } from '../lib/api'
import { demoTrendFor } from '../lib/trend'
import type { TrendResponse } from '../lib/types'

export function useTrend(equipmentId: string, hours: 24 | 168) {
  const { auth } = useAuth()
  const [result, setResult] = useState<TrendResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const requestId = useRef(0)

  const refresh = useCallback(async () => {
    const currentRequest = ++requestId.current
    if (!auth || !equipmentId) {
      setResult(null)
      setLoading(false)
      setError(null)
      return
    }
    if (auth.mode === 'demo') {
      setResult(demoTrendFor(equipmentId, hours))
      setLoading(false)
      setError(null)
      return
    }
    setLoading(true)
    try {
      const trend = await getTrend(auth.token, equipmentId, hours)
      if (currentRequest === requestId.current) {
        setResult(trend)
        setError(null)
      }
    } catch (cause) {
      if (currentRequest === requestId.current) {
        setError(cause instanceof Error ? cause.message : 'No se pudo cargar la tendencia.')
      }
    } finally {
      if (currentRequest === requestId.current) setLoading(false)
    }
  }, [auth, equipmentId, hours])

  useEffect(() => {
    void refresh()
    if (auth?.mode !== 'api' || !equipmentId) return () => { requestId.current += 1 }
    const interval = window.setInterval(() => { void refresh() }, 15_000)
    return () => { window.clearInterval(interval); requestId.current += 1 }
  }, [auth, equipmentId, refresh])

  const trend = result?.equipment_id === equipmentId && result.hours === hours ? result : null
  return { trend, loading, error, refresh }
}
