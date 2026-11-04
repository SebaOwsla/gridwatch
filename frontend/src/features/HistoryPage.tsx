import { useState } from 'react'
import { ArrowUpRight, CalendarDays, ChartNoAxesCombined } from 'lucide-react'
import { Link } from 'react-router'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useAuth } from '../app/AuthContext'
import { useData } from '../app/DataContext'
import { EmptyState, EquipmentSelect, Notice, PageHeader, SectionTitle, Surface } from '../components/UI'
import { formatDate, formatDayHour, formatElectrical, formatNumber, formatTime } from '../lib/format'
import { METRICS, type MetricKey } from '../lib/types'
import { useMeasurements } from './useMeasurements'
import { useTrend } from './useTrend'

export function HistoryPage() {
  const { auth } = useAuth()
  const { equipment, selectedEquipmentId, setSelectedEquipmentId } = useData()
  const [hours, setHours] = useState<24 | 168>(24)
  const [metric, setMetric] = useState<MetricKey>('voltage_l1_v')
  const { rows, loading, error, refresh } = useMeasurements(selectedEquipmentId, hours)
  const { trend, loading: trendLoading, error: trendError, refresh: refreshTrend } = useTrend(selectedEquipmentId, hours)
  const metricInfo = METRICS.find((item) => item.key === metric)!
  const statistics = trend?.statistics[metric]
  const chartData = trend?.buckets.map((bucket) => ({
    ...bucket, time: hours === 24 ? formatTime(bucket.bucket_start) : formatDayHour(bucket.bucket_start),
  })) ?? []
  const selected = equipment.find((item) => item.id === selectedEquipmentId)

  return <>
    <PageHeader eyebrow="Análisis temporal" title="Historial de mediciones" description="Explora el comportamiento de cada magnitud y consulta las muestras registradas." action={<Link to="/reports" className="secondary-button"><ArrowUpRight size={16} /> Exportar datos</Link>} />
    {error && <Notice message={error} onRetry={() => { void refresh() }} />}
    {trendError && <Notice message={trendError} onRetry={() => { void refreshTrend() }} />}
    <Surface className="mb-6 p-4 sm:p-5"><div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_180px_160px] md:items-end">
      <label><span className="field-label">Equipo</span><EquipmentSelect equipment={equipment} value={selectedEquipmentId} onChange={setSelectedEquipmentId} className="mt-1.5" /></label>
      <label><span className="field-label">Magnitud</span><select className="field mt-1.5" value={metric} onChange={(event) => setMetric(event.target.value as MetricKey)}>{METRICS.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label>
      <label><span className="field-label">Periodo</span><select className="field mt-1.5" value={hours} onChange={(event) => setHours(Number(event.target.value) as 24 | 168)}><option value={24}>Últimas 24 horas</option><option value={168}>Últimos 7 días</option></select></label>
    </div></Surface>

    <div className="grid gap-4 sm:grid-cols-3">
      {([['Mínimo', statistics?.minimum], ['Promedio', statistics?.average], ['Máximo', statistics?.maximum]] as const).map(([label, value]) => <Surface key={label} className="p-5"><p className="text-xs text-muted">{label}</p><p className="mt-3 text-2xl font-semibold tracking-tight text-ink">{formatElectrical(value, metricInfo.unit as 'V' | 'A' | 'kW' | 'Hz')}</p><p className="mt-2 text-xs text-muted">{metricInfo.label}</p></Surface>)}
    </div>

    <Surface className="mt-6 min-w-0 p-5 sm:p-6">
      <SectionTitle title={`${metricInfo.label} a lo largo del tiempo`} subtitle={selected ? `${selected.code} · ${trend?.valid_samples ?? 0} muestras válidas · promedio cada ${trend?.bucket_minutes ?? (hours === 24 ? 5 : 60)} min` : 'Selecciona un equipo'} action={<span className="inline-flex items-center gap-1.5 rounded-full bg-[#f1f7fb] px-3 py-1.5 text-xs text-[#6e91a8]"><CalendarDays size={14} />{hours === 24 ? '24 horas' : '7 días'}</span>} />
      {chartData.length ? <div className="h-[330px] w-full" role="img" aria-label={`Gráfico de ${metricInfo.label} del equipo seleccionado`}><ResponsiveContainer width="100%" height="100%"><LineChart data={chartData} margin={{ top: 15, right: 15, left: -15, bottom: 0 }}><CartesianGrid stroke="#edf2f7" vertical={false} /><XAxis dataKey="time" tickLine={false} axisLine={false} tick={{ fill: '#91a6b4', fontSize: 11 }} minTickGap={30} /><YAxis tickLine={false} axisLine={false} tick={{ fill: '#91a6b4', fontSize: 11 }} domain={['auto', 'auto']} tickFormatter={(value: number) => formatNumber(value, 0)} /><Tooltip contentStyle={{ border: '1px solid #e2ecf3', borderRadius: 12, fontSize: 12 }} formatter={(value) => `${formatNumber(Number(value))} ${metricInfo.unit}`} /><Line type="monotone" dataKey={metric} name={metricInfo.label} stroke="#6d9fbe" strokeWidth={2.7} dot={false} activeDot={{ r: 4 }} /></LineChart></ResponsiveContainer></div> : <EmptyState title={trendLoading ? 'Cargando historial…' : 'Sin muestras en este periodo'} description="Selecciona otro equipo o espera los primeros datos del simulador." />}
    </Surface>

    <Surface className="mt-6 p-5 sm:p-6"><SectionTitle title="Lecturas recientes" subtitle="Las fechas se presentan en tu zona horaria local" action={<span className="inline-flex items-center gap-2 text-xs text-muted"><ChartNoAxesCombined size={15} />{auth?.mode === 'demo' ? 'Muestras locales' : 'Hasta 1000 muestras por consulta'}</span>} />
      {rows.length ? <div className="soft-scroll overflow-x-auto"><table className="min-w-[780px] w-full text-left text-sm"><thead><tr className="border-b border-line text-xs text-muted"><th className="pb-3 pr-4">Fecha y hora</th><th className="pb-3 pr-4">Voltaje L1</th><th className="pb-3 pr-4">Corriente L1</th><th className="pb-3 pr-4">Potencia activa</th><th className="pb-3 pr-4">Frecuencia</th><th className="pb-3">Calidad</th></tr></thead><tbody className="divide-y divide-line">{[...rows].reverse().slice(0, 20).map((row) => <tr key={`${row.equipment_id}-${row.measured_at}`}><td className="py-3.5 pr-4 font-medium text-ink">{formatDate(row.measured_at)}</td><td className="py-3.5 pr-4 text-muted">{formatElectrical(row.voltage_l1_v, 'V')}</td><td className="py-3.5 pr-4 text-muted">{formatElectrical(row.current_l1_a, 'A')}</td><td className="py-3.5 pr-4 text-muted">{formatElectrical(row.active_power_kw, 'kW')}</td><td className="py-3.5 pr-4 text-muted">{formatElectrical(row.frequency_hz, 'Hz')}</td><td className="py-3.5"><span className={`rounded-full px-2.5 py-1 text-xs ${row.quality === 'valid' ? 'bg-[#edf7f3] text-[#4e8a72]' : 'bg-[#fff5f2] text-[#a76d59]'}`}>{row.quality === 'valid' ? 'Válida' : 'Inválida'}</span></td></tr>)}</tbody></table><p className="mt-4 text-xs text-muted">Mostrando las 20 lecturas más recientes de {rows.length} disponibles.</p></div> : <EmptyState title={loading ? 'Cargando lecturas…' : 'No hay lecturas'} description="Las mediciones registradas aparecerán aquí con su calidad y fecha." />}
    </Surface>
  </>
}
