import { useState, type FormEvent } from 'react'
import { Bell, BellRing, CheckCheck, Clock3, Plus, SlidersHorizontal } from 'lucide-react'
import { canManage, useAuth } from '../app/AuthContext'
import { useData } from '../app/DataContext'
import { EmptyState, Notice, PageHeader, SectionTitle, StatusBadge, Surface } from '../components/UI'
import { acknowledgeAlert, createRule } from '../lib/api'
import { formatDate, formatNumber, metricLabel } from '../lib/format'
import { METRICS, type AlertStatus, type MetricKey } from '../lib/types'

export function AlertsPage() {
  const { auth } = useAuth()
  const { alerts, rules, equipment, refresh, error: loadError } = useData()
  const [statusFilter, setStatusFilter] = useState<AlertStatus | 'all'>('all')
  const [equipmentFilter, setEquipmentFilter] = useState('all')
  const [showRuleForm, setShowRuleForm] = useState(false)
  const [ruleForm, setRuleForm] = useState({ equipment_id: '', metric: 'voltage_l1_v' as MetricKey, min_value: '', max_value: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const editable = canManage(auth)
  const filtered = alerts.filter((item) => (statusFilter === 'all' || item.status === statusFilter) && (equipmentFilter === 'all' || item.equipment_id === equipmentFilter))
  const count = (status: AlertStatus) => alerts.filter((item) => item.status === status).length

  async function acknowledge(id: string) {
    if (auth?.mode !== 'api') return
    setBusy(true); setError(null)
    try { await acknowledgeAlert(auth.token, id); await refresh() }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'No se pudo reconocer la alerta.') }
    finally { setBusy(false) }
  }

  async function submitRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (auth?.mode !== 'api') return
    const min = ruleForm.min_value === '' ? null : Number(ruleForm.min_value)
    const max = ruleForm.max_value === '' ? null : Number(ruleForm.max_value)
    if (min === null && max === null) { setError('Ingresa al menos un límite.'); return }
    if (min !== null && max !== null && min >= max) { setError('El límite mínimo debe ser menor que el máximo.'); return }
    setBusy(true); setError(null)
    try {
      await createRule(auth.token, { equipment_id: ruleForm.equipment_id, metric: ruleForm.metric, min_value: min, max_value: max, is_enabled: true })
      await refresh()
      setShowRuleForm(false)
      setRuleForm({ equipment_id: '', metric: 'voltage_l1_v', min_value: '', max_value: '' })
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'No se pudo crear la regla.') }
    finally { setBusy(false) }
  }

  return <>
    <PageHeader eyebrow="Supervisión de umbrales" title="Alertas" description="Identifica desviaciones, reconoce eventos y revisa los límites configurados." action={editable && <button type="button" className="primary-button" onClick={() => setShowRuleForm(!showRuleForm)}><Plus size={16} /> Nueva regla</button>} />
    {(error || loadError) && <Notice message={error || loadError || ''} onRetry={() => { setError(null); void refresh() }} />}
    <div className="grid gap-4 sm:grid-cols-3">
      {[{ label: 'Abiertas', status: 'open' as const, icon: BellRing }, { label: 'Reconocidas', status: 'acknowledged' as const, icon: Clock3 }, { label: 'Resueltas', status: 'resolved' as const, icon: CheckCheck }].map(({ label, status, icon: Icon }) => <Surface key={status} className="flex items-center gap-4 p-5"><span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#edf6fb] text-[#6b9bb9]"><Icon size={20} strokeWidth={1.8} /></span><span><p className="text-xs text-muted">{label}</p><p className="mt-1 text-2xl font-semibold text-ink">{count(status)}</p></span></Surface>)}
    </div>

    {showRuleForm && editable && <Surface className="mt-6 p-5 sm:p-6"><SectionTitle title="Crear regla de alerta" subtitle="Los límites son inclusivos; la alerta se abre al salir del rango" /><form onSubmit={submitRule} className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <label><span className="field-label">Equipo</span><select className="field mt-1.5" value={ruleForm.equipment_id} onChange={(event) => setRuleForm({ ...ruleForm, equipment_id: event.target.value })} required><option value="">Selecciona un equipo</option>{equipment.map((item) => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}</select></label>
      <label><span className="field-label">Magnitud</span><select className="field mt-1.5" value={ruleForm.metric} onChange={(event) => setRuleForm({ ...ruleForm, metric: event.target.value as MetricKey })}>{METRICS.map((item) => <option key={item.key} value={item.key}>{item.label} ({item.unit})</option>)}</select></label>
      <label><span className="field-label">Límite mínimo</span><input className="field mt-1.5" type="number" step="any" value={ruleForm.min_value} onChange={(event) => setRuleForm({ ...ruleForm, min_value: event.target.value })} placeholder="Opcional" /></label>
      <label><span className="field-label">Límite máximo</span><input className="field mt-1.5" type="number" step="any" value={ruleForm.max_value} onChange={(event) => setRuleForm({ ...ruleForm, max_value: event.target.value })} placeholder="Opcional" /></label>
      <div className="flex justify-end gap-2 sm:col-span-2 xl:col-span-4"><button type="button" className="secondary-button" onClick={() => setShowRuleForm(false)}>Cancelar</button><button type="submit" className="primary-button" disabled={busy}>Guardar regla</button></div>
    </form></Surface>}

    <Surface className="mt-6 p-5 sm:p-6">
      <SectionTitle title="Eventos recientes" subtitle="Ordenados desde el más reciente" action={<div className="flex flex-wrap gap-2"><span className="sr-only" id="alert-filter-label">Filtros de alertas</span><select aria-label="Filtrar por estado" className="field w-auto min-w-[135px]" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as AlertStatus | 'all')}><option value="all">Todos los estados</option><option value="open">Abiertas</option><option value="acknowledged">Reconocidas</option><option value="resolved">Resueltas</option></select><select aria-label="Filtrar por equipo" className="field w-auto min-w-[150px]" value={equipmentFilter} onChange={(event) => setEquipmentFilter(event.target.value)}><option value="all">Todos los equipos</option>{equipment.map((item) => <option key={item.id} value={item.id}>{item.code}</option>)}</select></div>} />
      {filtered.length ? <div className="divide-y divide-line">{filtered.map((alert) => {
        const asset = equipment.find((item) => item.id === alert.equipment_id)
        const unit = METRICS.find((item) => item.key === alert.metric)?.unit ?? ''
        return <div key={alert.id} className="flex flex-col gap-3 py-4 first:pt-1 sm:flex-row sm:items-center sm:gap-5"><div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#f0f6fa] text-[#6d9bb7]"><Bell size={17} /></div><div className="min-w-0 flex-1"><p className="text-sm font-semibold text-ink">{metricLabel(alert.metric)} fuera de rango</p><p className="mt-1 text-xs text-muted">{asset?.name ?? 'Equipo'} · {asset?.code ?? alert.equipment_id} · {formatDate(alert.opened_at)}</p></div><span className="text-sm font-semibold text-ink">{formatNumber(alert.observed_value)} {unit}</span><StatusBadge status={alert.status} />{editable && alert.status === 'open' && <button type="button" className="secondary-button justify-center" onClick={() => { void acknowledge(alert.id) }} disabled={busy}>Reconocer</button>}</div>
      })}</div> : <EmptyState title="Sin eventos para este filtro" description="Prueba otro estado o equipo para ver alertas registradas." />}
    </Surface>

    <Surface className="mt-6 p-5 sm:p-6"><SectionTitle title="Reglas de alerta" subtitle="Umbrales activos por magnitud y equipo" action={<SlidersHorizontal size={17} className="text-[#8ba6b7]" />} />
      {rules.length ? <div className="soft-scroll overflow-x-auto"><table className="min-w-[650px] w-full text-left text-sm"><thead><tr className="border-b border-line text-xs text-muted"><th className="pb-3 pr-4">Equipo</th><th className="pb-3 pr-4">Magnitud</th><th className="pb-3 pr-4">Mínimo</th><th className="pb-3 pr-4">Máximo</th><th className="pb-3">Estado</th></tr></thead><tbody className="divide-y divide-line">{rules.map((rule) => <tr key={rule.id}><td className="py-3.5 pr-4 font-medium text-ink">{equipment.find((item) => item.id === rule.equipment_id)?.code ?? 'Equipo'}</td><td className="py-3.5 pr-4 text-muted">{metricLabel(rule.metric)}</td><td className="py-3.5 pr-4 text-muted">{formatNumber(rule.min_value)}</td><td className="py-3.5 pr-4 text-muted">{formatNumber(rule.max_value)}</td><td className="py-3.5"><span className={`rounded-full px-2.5 py-1 text-xs ${rule.is_enabled ? 'bg-[#edf7f3] text-[#4e8a72]' : 'bg-[#f3f5f6] text-[#8295a2]'}`}>{rule.is_enabled ? 'Activa' : 'Pausada'}</span></td></tr>)}</tbody></table></div> : <EmptyState title="Sin reglas configuradas" description="Crea un umbral para detectar desviaciones de las mediciones." />}
    </Surface>
  </>
}
