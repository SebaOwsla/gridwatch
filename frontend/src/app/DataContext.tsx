import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { getAlerts, getEquipment, getInstallations, getRules, measurementsSocket } from '../lib/api'
import { demoAlerts, demoEquipment, demoInstallations, demoRules } from '../lib/demo'
import type { AlertEvent, AlertRule, Equipment, Installation, Measurement } from '../lib/types'
import { useAuth } from './AuthContext'

interface DataContextValue {
  installations: Installation[]
  equipment: Equipment[]
  alerts: AlertEvent[]
  rules: AlertRule[]
  selectedEquipmentId: string
  setSelectedEquipmentId: (id: string) => void
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
  liveMeasurement: Measurement | null
  liveStatus: 'demo' | 'connecting' | 'connected' | 'offline'
}

const DataContext = createContext<DataContextValue | null>(null)

export function DataProvider({ children }: { children: ReactNode }) {
  const { auth } = useAuth()
  const [installations, setInstallations] = useState<Installation[]>([])
  const [equipment, setEquipment] = useState<Equipment[]>([])
  const [alerts, setAlerts] = useState<AlertEvent[]>([])
  const [rules, setRules] = useState<AlertRule[]>([])
  const [selectedEquipmentId, setSelectedEquipmentId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [liveMeasurement, setLiveMeasurement] = useState<Measurement | null>(null)
  const [liveStatus, setLiveStatus] = useState<DataContextValue['liveStatus']>('demo')

  const refresh = useCallback(async () => {
    if (!auth) return
    if (auth.mode === 'demo') {
      setInstallations(demoInstallations)
      setEquipment(demoEquipment)
      setAlerts(demoAlerts)
      setRules(demoRules)
      setError(null)
      setLoading(false)
      return
    }
    try {
      const [sites, assets, events, thresholds] = await Promise.all([
        getInstallations(auth.token), getEquipment(auth.token), getAlerts(auth.token), getRules(auth.token),
      ])
      setInstallations(sites)
      setEquipment(assets)
      setAlerts(events)
      setRules(thresholds)
      setError(null)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudieron cargar los datos.')
    } finally {
      setLoading(false)
    }
  }, [auth])

  useEffect(() => {
    void refresh()
    if (auth?.mode !== 'api') return
    const interval = window.setInterval(() => { void refresh() }, 15_000)
    return () => window.clearInterval(interval)
  }, [auth, refresh])

  useEffect(() => {
    if (equipment.length && !equipment.some((item) => item.id === selectedEquipmentId)) {
      setSelectedEquipmentId(equipment[0].id)
    }
  }, [equipment, selectedEquipmentId])

  useEffect(() => {
    if (auth?.mode !== 'api') {
      setLiveStatus('demo')
      setLiveMeasurement(null)
      return
    }
    let active = true
    let socket: WebSocket | null = null
    let retry: number | undefined
    const connect = () => {
      setLiveStatus('connecting')
      const connection = measurementsSocket()
      socket = connection
      connection.onopen = () => {
        if (active) connection.send(JSON.stringify({ type: 'auth', token: auth.token }))
      }
      connection.onmessage = (message) => {
        if (!active) return
        try {
          const event = JSON.parse(message.data as string) as { type: string; measurement?: Measurement; alerts_changed?: boolean }
          if (event.type === 'ready') {
            setLiveStatus('connected')
            return
          }
          if (event.type === 'measurement' && event.measurement) {
            setLiveMeasurement(event.measurement)
            if (event.alerts_changed) void getAlerts(auth.token).then(setAlerts).catch(() => undefined)
          }
        } catch { /* Ignore malformed frames; polling still refreshes the view. */ }
      }
      connection.onclose = (event) => {
        if (!active) return
        setLiveStatus('offline')
        if (event.code !== 1008) retry = window.setTimeout(connect, 5_000)
      }
      connection.onerror = () => connection.close()
    }
    connect()
    return () => {
      active = false
      if (retry) window.clearTimeout(retry)
      socket?.close()
    }
  }, [auth])

  return (
    <DataContext.Provider value={{
      installations, equipment, alerts, rules, selectedEquipmentId,
      setSelectedEquipmentId, loading, error, refresh, liveMeasurement, liveStatus,
    }}>
      {children}
    </DataContext.Provider>
  )
}

export function useData() {
  const context = useContext(DataContext)
  if (!context) throw new Error('useData must be used inside DataProvider')
  return context
}
