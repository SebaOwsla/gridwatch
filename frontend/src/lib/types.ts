export type Role = 'admin' | 'operator' | 'viewer'

export interface User {
  id: string
  email: string
  full_name: string
  role: Role
  is_active: boolean
  created_at: string
}

export type InstallationKind = 'mine' | 'hydroelectric' | 'substation'

export interface Installation {
  id: string
  code: string
  name: string
  kind: InstallationKind
  timezone: string
  location: string | null
  is_active: boolean
  created_at: string
}

export type EquipmentKind = 'meter' | 'transformer' | 'generator' | 'feeder' | 'breaker'
export type EquipmentStatus = 'online' | 'offline' | 'maintenance'

export interface Equipment {
  id: string
  installation_id: string
  code: string
  name: string
  kind: EquipmentKind
  status: EquipmentStatus
  nominal_voltage_v: number | null
  created_at: string
}

export type MetricKey =
  | 'voltage_l1_v' | 'voltage_l2_v' | 'voltage_l3_v'
  | 'current_l1_a' | 'current_l2_a' | 'current_l3_a'
  | 'active_power_kw' | 'frequency_hz'

export interface Measurement {
  equipment_id: string
  measured_at: string
  received_at: string
  voltage_l1_v: number | null
  voltage_l2_v: number | null
  voltage_l3_v: number | null
  current_l1_a: number | null
  current_l2_a: number | null
  current_l3_a: number | null
  active_power_kw: number | null
  frequency_hz: number | null
  quality: 'valid' | 'invalid'
  source: 'simulator'
}

export type TrendBucket = Pick<Measurement, MetricKey> & {
  bucket_start: string
  sample_count: number
}

export interface MetricStatistics {
  minimum: number | null
  average: number | null
  maximum: number | null
}

export interface TrendResponse {
  equipment_id: string
  hours: 24 | 168
  bucket_minutes: number
  valid_samples: number
  buckets: TrendBucket[]
  statistics: Record<MetricKey, MetricStatistics>
}

export interface AlertRule {
  id: string
  equipment_id: string
  metric: MetricKey
  min_value: number | null
  max_value: number | null
  is_enabled: boolean
  created_at: string
}

export type AlertStatus = 'open' | 'acknowledged' | 'resolved'

export interface AlertEvent {
  id: string
  rule_id: string
  equipment_id: string
  metric: MetricKey
  measurement_at: string
  observed_value: number
  status: AlertStatus
  opened_at: string
  acknowledged_at: string | null
  acknowledged_by: string | null
  resolved_at: string | null
}

export interface AuditEvent {
  id: string
  actor_id: string | null
  action: string
  entity_type: string
  entity_id: string | null
  details: Record<string, unknown>
  created_at: string
}

export const METRICS: { key: MetricKey; label: string; unit: string }[] = [
  { key: 'voltage_l1_v', label: 'Voltaje L1', unit: 'V' },
  { key: 'voltage_l2_v', label: 'Voltaje L2', unit: 'V' },
  { key: 'voltage_l3_v', label: 'Voltaje L3', unit: 'V' },
  { key: 'current_l1_a', label: 'Corriente L1', unit: 'A' },
  { key: 'current_l2_a', label: 'Corriente L2', unit: 'A' },
  { key: 'current_l3_a', label: 'Corriente L3', unit: 'A' },
  { key: 'active_power_kw', label: 'Potencia activa', unit: 'kW' },
  { key: 'frequency_hz', label: 'Frecuencia', unit: 'Hz' },
]
