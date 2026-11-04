import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../app/AuthContext'
import { useData } from '../app/DataContext'
import { getMeasurements } from '../lib/api'
import { demoMeasurementsFor } from '../lib/demo'
import type { Measurement } from '../lib/types'

export function useMeasurements(equipmentId: string, hours = 24) {
  const { auth } = useAuth()
  const { liveMeasurement } = useData()
  const [rows, setRows] = useState<Measurement[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!auth || !equipmentId) {
      setRows([])
      return
    }
    if (auth.mode === 'demo') {
      const cutoff = Date.now() - hours * 3_600_000
      setRows(demoMeasurementsFor(equipmentId).filter((row) => new Date(row.measured_at).getTime() >= cutoff))
      setError(null)
      return
    }
    setLoading(true)
    try {
      const end = new Date()
      const start = new Date(end.getTime() - hours * 3_600_000)
      const measurements = await getMeasurements(auth.token, equipmentId, start.toISOString(), end.toISOString())
      setRows((previous) => [
        ...measurements,
        ...previous.filter((row) => row.equipment_id === equipmentId && Date.parse(row.measured_at) > end.getTime()),
      ].sort((a, b) => a.measured_at.localeCompare(b.measured_at)).slice(-1000))
      setError(null)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudieron cargar las mediciones.')
    } finally {
      setLoading(false)
    }
  }, [auth, equipmentId, hours])

  useEffect(() => {
    void refresh()
    if (auth?.mode !== 'api' || !equipmentId) return
    const interval = window.setInterval(() => { void refresh() }, 15_000)
    return () => window.clearInterval(interval)
  }, [auth, equipmentId, refresh])

  useEffect(() => {
    if (auth?.mode !== 'api' || !liveMeasurement || liveMeasurement.equipment_id !== equipmentId) return
    if (Date.parse(liveMeasurement.measured_at) < Date.now() - hours * 3_600_000) return
    setRows((previous) => {
      const withoutDuplicate = previous.filter((row) => row.measured_at !== liveMeasurement.measured_at)
      return [...withoutDuplicate, liveMeasurement].sort((a, b) => a.measured_at.localeCompare(b.measured_at)).slice(-1000)
    })
  }, [auth, equipmentId, hours, liveMeasurement])

  return { rows, loading, error, refresh }
}
