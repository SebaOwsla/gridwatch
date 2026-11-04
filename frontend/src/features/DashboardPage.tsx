import { Activity, ArrowRight, Bell, Gauge, Waves, Zap } from 'lucide-react'
import { Link } from 'react-router'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useAuth } from '../app/AuthContext'
import { useData } from '../app/DataContext'
import { EmptyState, EquipmentSelect, Notice, PageHeader, SectionTitle, StatusBadge, Surface } from '../components/UI'
import { equipmentStatusLabels, formatDate, formatElectrical, formatNumber, formatTime, installationLabels, metricLabel } from '../lib/format'
import { useMeasurements } from './useMeasurements'
import { useTrend } from './useTrend'

const metricCards = [
  { label: 'Voltaje L1', key: 'voltage_l1_v' as const, unit: 'V' as const, icon: Waves, note: 'Medición por fase' },
  { label: 'Corriente L1', key: 'current_l1_a' as const, unit: 'A' as const, icon: Activity, note: 'Carga instantánea' },
  { label: 'Potencia activa', key: 'active_power_kw' as const, unit: 'kW' as const, icon: Zap, note: 'Flujo de energía' },
  { label: 'Frecuencia', key: 'frequency_hz' as const, unit: 'Hz' as const, icon: Gauge, note: 'Referencia nominal: 50 Hz' },
]

export function DashboardPage() {
  const { auth } = useAuth()
  const { installations, equipment, alerts, selectedEquipmentId, setSelectedEquipmentId, loading, error, refresh } = useData()
  const { rows, loading: readingsLoading, error: readingsError, refresh: refreshReadings } = useMeasurements(selectedEquipmentId)
  const { trend, loading: trendLoading, error: trendError, refresh: refreshTrend } = useTrend(selectedEquipmentId, 24)
  const selected = equipment.find((item) => item.id === selectedEquipmentId)
  const latest = [...rows].reverse().find((item) => item.quality === 'valid')
  const activeAlerts = alerts.filter((item) => item.status !== 'resolved')
  const chartData = trend?.buckets.map((bucket) => ({ ...bucket, time: formatTime(bucket.bucket_start) })) ?? []

  return <>
    <PageHeader eyebrow="Vista general" title="Resumen eléctrico" description="Indicadores esenciales de tus instalaciones y equipos en un solo lugar." action={<EquipmentSelect equipment={equipment} value={selectedEquipmentId} onChange={setSelectedEquipmentId} />} />
    {error && <Notice message={`No se pudieron actualizar los datos: ${error}`} onRetry={() => { void refresh() }} />}
    {readingsError && <Notice message={`No se pudieron cargar las mediciones: ${readingsError}`} onRetry={() => { void refreshReadings() }} />}
    {trendError && <Notice message={`No se pudo cargar la tendencia: ${trendError}`} onRetry={() => { void refreshTrend() }} />}
    <div className="mb-6 flex flex-wrap items-center gap-2 text-xs text-muted">
      <span className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 ring-1 ring-line"><span className="h-1.5 w-1.5 rounded-full bg-[#85b39d]" />{selected ? equipmentStatusLabels[selected.status] : 'Sin equipo seleccionado'}</span>
      <span>{auth?.mode === 'demo' ? 'Datos de muestra, sin actualización automática' : 'Lecturas en vivo con respaldo cada 15 segundos'}</span>
      {latest && <span>· Última muestra {formatDate(latest.measured_at)}</span>}
    </div>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {metricCards.map(({ label, key, unit, icon: Icon, note }) => <Surface key={key} className="p-5 sm:p-6">
        <div className="flex items-start justify-between"><span className="text-xs font-medium text-muted">{label}</span><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#edf6fb] text-[#6c9fbd]"><Icon size={18} strokeWidth={1.8} /></span></div>
        <p className="mt-5 text-[1.65rem] font-semibold tracking-tight text-ink">{formatElectrical(latest?.[key], unit)}</p>
        <p className="mt-2 text-xs text-muted">{note}</p>
      </Surface>)}
    </div>

    <div className="mt-6 grid gap-5 xl:grid-cols-[minmax(0,1.65fr)_minmax(300px,1fr)]">
      <Surface className="min-w-0 p-5 sm:p-6">
        <SectionTitle title="Tendencia de voltaje" subtitle={selected ? `${selected.code} · últimas 24 horas · promedio cada 5 min` : 'Selecciona un equipo'} action={<Link to="/history" className="inline-flex items-center gap-1 text-xs font-semibold text-[#4a82a4] hover:underline">Ver historial <ArrowRight size={14} /></Link>} />
        {chartData.length ? <div className="h-[280px] w-full" role="img" aria-label="Gráfico de voltaje por fase en las últimas 24 horas">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 12, right: 7, bottom: 0, left: -20 }}>
              <CartesianGrid stroke="#edf2f7" vertical={false} />
              <XAxis dataKey="time" tickLine={false} axisLine={false} tick={{ fill: '#92a6b4', fontSize: 11 }} minTickGap={28} />
              <YAxis tickLine={false} axisLine={false} tick={{ fill: '#92a6b4', fontSize: 11 }} tickFormatter={(value: number) => formatNumber(value / 1000, 1) + 'k'} domain={['auto', 'auto']} />
              <Tooltip contentStyle={{ border: '1px solid #e2ecf3', borderRadius: 12, boxShadow: '0 10px 28px #233d5614', fontSize: 12 }} formatter={(value) => `${formatNumber(Number(value), 0)} V`} />
              <Line type="monotone" dataKey="voltage_l1_v" name="L1" stroke="#78a9c6" strokeWidth={2.6} dot={false} activeDot={{ r: 4 }} />
              <Line type="monotone" dataKey="voltage_l2_v" name="L2" stroke="#a8c8d9" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="voltage_l3_v" name="L3" stroke="#557f9b" strokeWidth={1.8} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div> : <EmptyState title={loading || readingsLoading || trendLoading ? 'Cargando lecturas…' : 'Sin mediciones disponibles'} description="Cuando el simulador envíe datos, aparecerán las tendencias del equipo seleccionado." />}
        <div className="mt-4 flex flex-wrap gap-5 border-t border-line pt-4 text-xs text-muted"><span><i className="mr-1.5 inline-block h-2 w-2 rounded-full bg-[#78a9c6]" />Fase L1</span><span><i className="mr-1.5 inline-block h-2 w-2 rounded-full bg-[#a8c8d9]" />Fase L2</span><span><i className="mr-1.5 inline-block h-2 w-2 rounded-full bg-[#557f9b]" />Fase L3</span></div>
      </Surface>
      <Surface className="p-5 sm:p-6">
        <SectionTitle title="Alertas recientes" subtitle={`${activeAlerts.length} requieren seguimiento`} action={<Link to="/alerts" className="inline-flex items-center gap-1 text-xs font-semibold text-[#4a82a4] hover:underline">Ver todas <ArrowRight size={14} /></Link>} />
        {alerts.length ? <div className="divide-y divide-line">
          {alerts.slice(0, 4).map((alert) => {
            const asset = equipment.find((item) => item.id === alert.equipment_id)
            return <div key={alert.id} className="py-4 first:pt-1 last:pb-0">
              <div className="flex items-start gap-3"><span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-[#f0f6fa] text-[#6e9bb7]"><Bell size={15} /></span><div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-ink">{metricLabel(alert.metric)} · {asset?.code ?? 'Equipo'}</p><p className="mt-1 text-xs text-muted">{formatDate(alert.opened_at)} · {formatNumber(alert.observed_value)} {alert.metric.endsWith('_v') ? 'V' : alert.metric.endsWith('_a') ? 'A' : alert.metric.endsWith('_kw') ? 'kW' : 'Hz'}</p></div><StatusBadge status={alert.status} /></div>
            </div>
          })}
        </div> : <EmptyState title="Sin alertas" description="Las alertas de umbral aparecerán aquí cuando se registren eventos." />}
      </Surface>
    </div>

    <Surface className="mt-6 p-5 sm:p-6">
      <SectionTitle title="Instalaciones" subtitle="Estado general de los sitios de la demostración" action={<Link to="/installations" className="inline-flex items-center gap-1 text-xs font-semibold text-[#4a82a4] hover:underline">Ver instalaciones <ArrowRight size={14} /></Link>} />
      {installations.length ? <div className="grid gap-3 md:grid-cols-3">
        {installations.map((site) => {
          const siteEquipment = equipment.filter((item) => item.installation_id === site.id)
          return <div key={site.id} className="rounded-2xl border border-line bg-[#fbfdff] p-4"><p className="text-[10px] font-semibold uppercase tracking-[.12em] text-[#86a6ba]">{installationLabels[site.kind]}</p><p className="mt-2 text-sm font-semibold text-ink">{site.name}</p><p className="mt-1 text-xs text-muted">{site.location ?? site.code}</p><div className="mt-5 flex items-center justify-between border-t border-line pt-3 text-xs text-muted"><span>{siteEquipment.length} {siteEquipment.length === 1 ? 'equipo' : 'equipos'}</span><span className="font-medium text-[#4d806e]">{siteEquipment.filter((item) => item.status === 'online').length} en línea</span></div></div>
        })}
      </div> : <EmptyState title="Aún no hay instalaciones" description="Agrega una instalación para comenzar el monitoreo." />}
    </Surface>
  </>
}
