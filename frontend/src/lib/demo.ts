import type { AlertEvent, AlertRule, AuditEvent, Equipment, Installation, Measurement, User } from './types'

const NOW = Date.now()
const isoAgo = (minutes: number) => new Date(NOW - minutes * 60_000).toISOString()

const IDS = {
  mine: '10000000-0000-4000-8000-000000000001',
  hydro: '10000000-0000-4000-8000-000000000002',
  substation: '10000000-0000-4000-8000-000000000003',
  feeder: '20000000-0000-4000-8000-000000000001',
  transformer: '20000000-0000-4000-8000-000000000002',
  generator: '20000000-0000-4000-8000-000000000003',
  meter: '20000000-0000-4000-8000-000000000004',
  rule1: '30000000-0000-4000-8000-000000000001',
  rule2: '30000000-0000-4000-8000-000000000002',
  rule3: '30000000-0000-4000-8000-000000000003',
}

export const demoUser: User = {
  id: '40000000-0000-4000-8000-000000000001',
  email: 'demo@gridwatch.local',
  full_name: 'Vista de demostración',
  role: 'viewer',
  is_active: true,
  created_at: isoAgo(20_000),
}

export const demoInstallations: Installation[] = [
  { id: IDS.mine, code: 'MIN-NORTE', name: 'Complejo Minero Norte', kind: 'mine', timezone: 'America/Santiago', location: 'Región de Antofagasta', is_active: true, created_at: isoAgo(50_000) },
  { id: IDS.hydro, code: 'CH-RIO', name: 'Central Río Claro', kind: 'hydroelectric', timezone: 'America/Santiago', location: 'Región del Biobío', is_active: true, created_at: isoAgo(48_000) },
  { id: IDS.substation, code: 'SE-VALLE', name: 'Subestación Valle', kind: 'substation', timezone: 'America/Santiago', location: 'Región Metropolitana', is_active: true, created_at: isoAgo(46_000) },
]

export const demoEquipment: Equipment[] = [
  { id: IDS.feeder, installation_id: IDS.mine, code: 'AL-01', name: 'Alimentador principal', kind: 'feeder', status: 'online', nominal_voltage_v: 13_800, created_at: isoAgo(40_000) },
  { id: IDS.meter, installation_id: IDS.mine, code: 'MED-02', name: 'Medidor de chancado', kind: 'meter', status: 'online', nominal_voltage_v: 13_800, created_at: isoAgo(39_000) },
  { id: IDS.generator, installation_id: IDS.hydro, code: 'GEN-01', name: 'Generador unidad 1', kind: 'generator', status: 'online', nominal_voltage_v: 13_800, created_at: isoAgo(38_000) },
  { id: IDS.transformer, installation_id: IDS.substation, code: 'TR-01', name: 'Transformador principal', kind: 'transformer', status: 'maintenance', nominal_voltage_v: 110_000, created_at: isoAgo(37_000) },
]

export const demoRules: AlertRule[] = [
  { id: IDS.rule1, equipment_id: IDS.feeder, metric: 'voltage_l1_v', min_value: 13_400, max_value: 14_200, is_enabled: true, created_at: isoAgo(30_000) },
  { id: IDS.rule2, equipment_id: IDS.generator, metric: 'current_l1_a', min_value: null, max_value: 310, is_enabled: true, created_at: isoAgo(29_000) },
  { id: IDS.rule3, equipment_id: IDS.transformer, metric: 'frequency_hz', min_value: 49.5, max_value: 50.5, is_enabled: true, created_at: isoAgo(28_000) },
]

export const demoAlerts: AlertEvent[] = [
  { id: '50000000-0000-4000-8000-000000000001', rule_id: IDS.rule1, equipment_id: IDS.feeder, metric: 'voltage_l1_v', measurement_at: isoAgo(18), observed_value: 14_260, status: 'open', opened_at: isoAgo(18), acknowledged_at: null, acknowledged_by: null, resolved_at: null },
  { id: '50000000-0000-4000-8000-000000000002', rule_id: IDS.rule2, equipment_id: IDS.generator, metric: 'current_l1_a', measurement_at: isoAgo(65), observed_value: 318, status: 'acknowledged', opened_at: isoAgo(65), acknowledged_at: isoAgo(43), acknowledged_by: demoUser.id, resolved_at: null },
  { id: '50000000-0000-4000-8000-000000000003', rule_id: IDS.rule3, equipment_id: IDS.transformer, metric: 'frequency_hz', measurement_at: isoAgo(400), observed_value: 49.3, status: 'resolved', opened_at: isoAgo(400), acknowledged_at: null, acknowledged_by: null, resolved_at: isoAgo(320) },
]

export const demoAudit: AuditEvent[] = [
  { id: '60000000-0000-4000-8000-000000000001', actor_id: demoUser.id, action: 'installation.created', entity_type: 'installation', entity_id: IDS.mine, details: {}, created_at: isoAgo(600) },
  { id: '60000000-0000-4000-8000-000000000002', actor_id: null, action: 'measurement.ingested', entity_type: 'equipment', entity_id: IDS.feeder, details: { source: 'simulator' }, created_at: isoAgo(10) },
]

export function demoMeasurementsFor(equipmentId: string): Measurement[] {
  const equipment = demoEquipment.find((item) => item.id === equipmentId) ?? demoEquipment[0]
  const baseVoltage = equipment.nominal_voltage_v ?? 13_800
  const baseCurrent = equipment.kind === 'transformer' ? 112 : equipment.kind === 'generator' ? 286 : 248
  const basePower = equipment.kind === 'generator' ? 6_350 : equipment.kind === 'transformer' ? 4_780 : 5_720

  return Array.from({ length: 49 }, (_, index) => {
    const phase = index / 4
    const voltage = baseVoltage + Math.sin(phase) * baseVoltage * 0.009 + Math.cos(index * 0.65) * baseVoltage * 0.002
    const current = baseCurrent + Math.sin(phase * 0.8) * 13 + Math.cos(index * 0.4) * 4
    const power = basePower + Math.sin(phase * 0.65) * 260 + Math.cos(index * 0.35) * 90
    const measuredAt = isoAgo((48 - index) * 30)
    return {
      equipment_id: equipment.id,
      measured_at: measuredAt,
      received_at: measuredAt,
      voltage_l1_v: Math.round(voltage),
      voltage_l2_v: Math.round(voltage * 1.003),
      voltage_l3_v: Math.round(voltage * 0.997),
      current_l1_a: Math.round(current * 10) / 10,
      current_l2_a: Math.round(current * 1.018 * 10) / 10,
      current_l3_a: Math.round(current * 0.984 * 10) / 10,
      active_power_kw: Math.round(power),
      frequency_hz: Math.round((50 + Math.sin(phase * 1.4) * 0.08) * 100) / 100,
      quality: index === 13 ? 'invalid' as const : 'valid' as const,
      source: 'simulator' as const,
    }
  })
}
