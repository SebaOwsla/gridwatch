import type { AlertEvent, AlertRule, AuditEvent, Equipment, Installation, Measurement, TrendResponse, User } from './types'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '/api/v1').replace(/\/$/, '')

export function measurementsSocket(): WebSocket {
  const url = new URL(`${BASE_URL}/ws/measurements`, window.location.href)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return new WebSocket(url, 'gridwatch')
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

async function parseError(response: Response): Promise<ApiError> {
  let message = `Error ${response.status}`
  try {
    const body = await response.json() as { detail?: string | unknown[] }
    if (typeof body.detail === 'string') message = body.detail
    if (Array.isArray(body.detail)) message = 'Revisa los datos ingresados.'
  } catch {
    // Keep the HTTP status when the response is not JSON.
  }
  return new ApiError(response.status, message)
}

async function request<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...init.headers,
    },
  })
  if (!response.ok) throw await parseError(response)
  return response.json() as Promise<T>
}

const params = (data: Record<string, string>) => new URLSearchParams(data).toString()

export async function login(email: string, password: string): Promise<string> {
  const response = await fetch(`${BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: params({ username: email, password }),
  })
  if (!response.ok) throw await parseError(response)
  const body = await response.json() as { access_token: string }
  return body.access_token
}

export const getMe = (token: string) => request<User>('/auth/me', token)
export const getInstallations = (token: string) => request<Installation[]>('/installations?limit=100', token)
export const getEquipment = (token: string) => request<Equipment[]>('/equipment?limit=100', token)
export const getAlerts = (token: string) => request<AlertEvent[]>('/alert-events?limit=100', token)
export const getRules = (token: string) => request<AlertRule[]>('/alert-rules?limit=100', token)
export const getAudit = (token: string) => request<AuditEvent[]>('/audit-events?limit=100', token)
export const getUsers = (token: string) => request<User[]>('/auth/users?limit=100', token)

export const getMeasurements = (token: string, equipmentId: string, start: string, end: string) =>
  request<Measurement[]>(`/measurements?${params({ equipment_id: equipmentId, start, end, limit: '1000' })}`, token)

export const getTrend = (token: string, equipmentId: string, hours: 24 | 168) =>
  request<TrendResponse>(`/measurements/trend?${params({ equipment_id: equipmentId, hours: String(hours) })}`, token)

export const createInstallation = (token: string, data: Omit<Installation, 'id' | 'created_at'>) =>
  request<Installation>('/installations', token, { method: 'POST', body: JSON.stringify(data) })

export const updateInstallation = (token: string, data: Installation) => {
  const { code, name, kind, timezone, location, is_active } = data
  return request<Installation>(`/installations/${data.id}`, token, { method: 'PUT', body: JSON.stringify({ code, name, kind, timezone, location, is_active }) })
}

export const createEquipment = (token: string, data: Omit<Equipment, 'id' | 'created_at'>) =>
  request<Equipment>('/equipment', token, { method: 'POST', body: JSON.stringify(data) })

export const updateEquipment = (token: string, data: Equipment) => {
  const { code, name, kind, status, nominal_voltage_v } = data
  return request<Equipment>(`/equipment/${data.id}`, token, { method: 'PUT', body: JSON.stringify({ code, name, kind, status, nominal_voltage_v }) })
}

export const createRule = (token: string, data: Omit<AlertRule, 'id' | 'created_at'>) =>
  request<AlertRule>('/alert-rules', token, { method: 'POST', body: JSON.stringify(data) })

export const acknowledgeAlert = (token: string, id: string) =>
  request<AlertEvent>(`/alert-events/${id}/acknowledge`, token, { method: 'POST' })

export const createUser = (token: string, data: { email: string; full_name: string; password: string; role: User['role'] }) =>
  request<User>('/auth/users', token, { method: 'POST', body: JSON.stringify(data) })

export async function downloadReport(token: string, equipmentId: string, start: string, end: string, format: 'pdf' | 'xlsx' | 'summary-xlsx') {
  const route = format === 'summary-xlsx' ? '/reports/summary.xlsx' : `/reports/measurements.${format}`
  const response = await fetch(`${BASE_URL}${route}?${params({ equipment_id: equipmentId, start, end })}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) throw await parseError(response)
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = format === 'summary-xlsx' ? `gridwatch-resumen-${equipmentId}.xlsx` : `gridwatch-${equipmentId}.${format}`
  document.body.append(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
