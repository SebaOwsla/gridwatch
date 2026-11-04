import type { AlertStatus, EquipmentKind, EquipmentStatus, InstallationKind, MetricKey } from './types'
import { METRICS } from './types'

const numberFormat = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 1 })
const dateFormat = new Intl.DateTimeFormat('es-CL', {
  day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
})
const timeFormat = new Intl.DateTimeFormat('es-CL', { hour: '2-digit', minute: '2-digit' })
const dayHourFormat = new Intl.DateTimeFormat('es-CL', { day: '2-digit', month: '2-digit', hour: '2-digit' })

export const formatNumber = (value: number | null | undefined, digits = 1) =>
  value == null ? '—' : new Intl.NumberFormat('es-CL', { maximumFractionDigits: digits }).format(value)

export const formatDate = (value: string) => dateFormat.format(new Date(value))
export const formatTime = (value: string) => timeFormat.format(new Date(value))
export const formatDayHour = (value: string) => dayHourFormat.format(new Date(value))

export function formatElectrical(value: number | null | undefined, unit: 'V' | 'A' | 'kW' | 'Hz') {
  if (value == null) return '—'
  if (unit === 'V' && Math.abs(value) >= 1000) return `${numberFormat.format(value / 1000)} kV`
  if (unit === 'kW' && Math.abs(value) >= 1000) return `${numberFormat.format(value / 1000)} MW`
  return `${numberFormat.format(value)} ${unit}`
}

export const metricLabel = (key: MetricKey) => METRICS.find((item) => item.key === key)?.label ?? key

export const installationLabels: Record<InstallationKind, string> = {
  mine: 'Minería', hydroelectric: 'Hidroeléctrica', substation: 'Subestación',
}

export const equipmentLabels: Record<EquipmentKind, string> = {
  meter: 'Medidor', transformer: 'Transformador', generator: 'Generador',
  feeder: 'Alimentador', breaker: 'Interruptor',
}

export const equipmentStatusLabels: Record<EquipmentStatus, string> = {
  online: 'En línea', offline: 'Fuera de línea', maintenance: 'Mantenimiento',
}

export const alertStatusLabels: Record<AlertStatus, string> = {
  open: 'Abierta', acknowledged: 'Reconocida', resolved: 'Resuelta',
}
