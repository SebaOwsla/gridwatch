import { act, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { DataProvider, useData } from '../app/DataContext'
import { useMeasurements } from '../features/useMeasurements'

const equipmentId = '20000000-0000-4000-8000-000000000001'
const authState = vi.hoisted(() => ({ mode: 'api', token: 'test-token', user: { role: 'viewer' } }))
const socket = vi.hoisted(() => ({
  onopen: null as (() => void) | null,
  onmessage: null as ((event: { data: string }) => void) | null,
  onclose: null as (() => void) | null,
  onerror: null as (() => void) | null,
  close: vi.fn(),
  send: vi.fn(),
}))

vi.mock('../app/AuthContext', () => ({
  useAuth: () => ({ auth: authState }),
}))

vi.mock('../lib/api', () => ({
  getAlerts: vi.fn().mockResolvedValue([]),
  getEquipment: vi.fn().mockResolvedValue([]),
  getInstallations: vi.fn().mockResolvedValue([]),
  getRules: vi.fn().mockResolvedValue([]),
  getMeasurements: vi.fn().mockResolvedValue([]),
  measurementsSocket: vi.fn(() => socket),
}))

function Readout() {
  const { liveStatus } = useData()
  const { rows } = useMeasurements(equipmentId)
  return <div><span>{liveStatus}</span><span>{rows.at(-1)?.voltage_l1_v ?? 'sin lectura'}</span></div>
}

describe('telemetría en vivo', () => {
  it('agrega la muestra del WebSocket al historial visible', async () => {
    render(<DataProvider><Readout /></DataProvider>)
    await waitFor(() => expect(socket.onmessage).toBeTypeOf('function'))
    act(() => {
      socket.onopen?.()
      socket.onmessage?.({ data: JSON.stringify({ type: 'ready' }) })
      socket.onmessage?.({ data: JSON.stringify({
        type: 'measurement',
        measurement: { equipment_id: equipmentId, measured_at: new Date().toISOString(), voltage_l1_v: 14_300 },
      }) })
    })
    expect(await screen.findByText('14300')).toBeTruthy()
    expect(screen.getByText('connected')).toBeTruthy()
    expect(socket.send).toHaveBeenCalledWith(JSON.stringify({ type: 'auth', token: 'test-token' }))
  })
})
