import { useState } from 'react'
import { CalendarRange, Download, FileBarChart2, FileSpreadsheet, Info } from 'lucide-react'
import { useAuth } from '../app/AuthContext'
import { useData } from '../app/DataContext'
import { EmptyState, EquipmentSelect, Notice, PageHeader, SectionTitle, Surface } from '../components/UI'
import { downloadReport } from '../lib/api'
import { formatDate } from '../lib/format'
import { useMeasurements } from './useMeasurements'

function localInputValue(date: Date) {
  const shifted = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return shifted.toISOString().slice(0, 16)
}

export function ReportsPage() {
  const { auth } = useAuth()
  const { equipment, selectedEquipmentId, setSelectedEquipmentId } = useData()
  const [start, setStart] = useState(() => localInputValue(new Date(Date.now() - 24 * 3_600_000)))
  const [end, setEnd] = useState(() => localInputValue(new Date()))
  const [busy, setBusy] = useState<'pdf' | 'xlsx' | 'summary-xlsx' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { rows } = useMeasurements(selectedEquipmentId)
  const selected = equipment.find((item) => item.id === selectedEquipmentId)

  async function exportFile(format: 'pdf' | 'xlsx' | 'summary-xlsx') {
    if (auth?.mode !== 'api' || !selectedEquipmentId) return
    const from = new Date(start)
    const until = new Date(end)
    if (Number.isNaN(from.getTime()) || Number.isNaN(until.getTime()) || from >= until) { setError('Selecciona un periodo válido.'); return }
    if (until.getTime() - from.getTime() > 31 * 86_400_000) { setError('El periodo no puede superar 31 días.'); return }
    setBusy(format); setError(null)
    try { await downloadReport(auth.token, selectedEquipmentId, from.toISOString(), until.toISOString(), format) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'No se pudo generar el reporte.') }
    finally { setBusy(null) }
  }

  return <>
    <PageHeader eyebrow="Exportación de datos" title="Reportes" description="Descarga lecturas detalladas o un resumen eléctrico del periodo seleccionado." />
    {error && <Notice message={error} onRetry={() => setError(null)} />}
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(300px,.8fr)]">
      <Surface className="p-5 sm:p-7">
        <SectionTitle title="Configurar reporte" subtitle="Selecciona un equipo y un intervalo de hasta 31 días" />
        <div className="space-y-5">
          <label className="block"><span className="field-label">Equipo</span><EquipmentSelect equipment={equipment} value={selectedEquipmentId} onChange={setSelectedEquipmentId} className="mt-1.5" /></label>
          <div className="grid gap-4 sm:grid-cols-2"><label><span className="field-label">Desde</span><input className="field mt-1.5" type="datetime-local" value={start} onChange={(event) => setStart(event.target.value)} /></label><label><span className="field-label">Hasta</span><input className="field mt-1.5" type="datetime-local" value={end} onChange={(event) => setEnd(event.target.value)} /></label></div>
          <div className="rounded-xl border border-[#dfeaf2] bg-[#f5f9fc] px-4 py-3 text-xs leading-5 text-muted"><div className="flex items-start gap-2"><Info size={15} className="mt-0.5 shrink-0 text-[#78a2bb]" /><span>Las fechas se ingresan en tu zona horaria local y se consultan en UTC. El PDF y el Excel resumido admiten hasta 31 días; el Excel detallado admite hasta 5000 muestras.</span></div></div>
        </div>
      </Surface>
      <Surface className="p-5 sm:p-7"><SectionTitle title="Vista previa" subtitle="Datos del equipo seleccionado" />{selected ? <div className="space-y-4"><div className="rounded-xl border border-line bg-[#fbfdff] p-4"><p className="text-xs text-muted">Equipo</p><p className="mt-1 text-sm font-semibold text-ink">{selected.name}</p><p className="mt-1 text-xs text-muted">{selected.code}</p></div><div className="grid grid-cols-2 gap-3"><div className="rounded-xl bg-[#f1f7fb] p-4"><p className="text-xs text-muted">Muestras recientes</p><p className="mt-2 text-2xl font-semibold text-ink">{rows.length}</p></div><div className="rounded-xl bg-[#f1f7fb] p-4"><p className="text-xs text-muted">Última lectura</p><p className="mt-2 text-sm font-semibold text-ink">{rows.length ? formatDate(rows[rows.length - 1].measured_at) : 'Sin datos'}</p></div></div></div> : <EmptyState title="Selecciona un equipo" description="La vista previa estará disponible después de elegir un equipo." />}</Surface>
    </div>
    <div className="mt-6 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
      <Surface className="p-6"><span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#edf5fa] text-[#6095b5]"><FileBarChart2 size={21} strokeWidth={1.7} /></span><h2 className="mt-5 text-lg font-semibold text-ink">Resumen en PDF</h2><p className="mt-2 min-h-12 text-sm leading-6 text-muted">Mínimos, promedios y máximos de todas las muestras válidas del periodo, hasta 31 días.</p><button type="button" className="primary-button mt-5" onClick={() => { void exportFile('pdf') }} disabled={auth?.mode !== 'api' || busy !== null || !selected}><Download size={16} /> {busy === 'pdf' ? 'Preparando…' : 'Descargar PDF'}</button></Surface>
      <Surface className="p-6"><span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#edf5fa] text-[#6095b5]"><FileSpreadsheet size={21} strokeWidth={1.7} /></span><h2 className="mt-5 text-lg font-semibold text-ink">Resumen en Excel</h2><p className="mt-2 min-h-12 text-sm leading-6 text-muted">Estadísticas e intervalos de 5 minutos, 1 hora o 6 horas según el periodo.</p><button type="button" className="secondary-button mt-5" onClick={() => { void exportFile('summary-xlsx') }} disabled={auth?.mode !== 'api' || busy !== null || !selected}><Download size={16} /> {busy === 'summary-xlsx' ? 'Preparando…' : 'Descargar resumen'}</button></Surface>
      <Surface className="p-6"><span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#edf5fa] text-[#6095b5]"><FileSpreadsheet size={21} strokeWidth={1.7} /></span><h2 className="mt-5 text-lg font-semibold text-ink">Detalle en Excel</h2><p className="mt-2 min-h-12 text-sm leading-6 text-muted">Cada muestra con fecha UTC, magnitudes y calidad. Disponible hasta 5000 filas.</p><button type="button" className="secondary-button mt-5" onClick={() => { void exportFile('xlsx') }} disabled={auth?.mode !== 'api' || busy !== null || !selected}><Download size={16} /> {busy === 'xlsx' ? 'Preparando…' : 'Descargar detalle'}</button></Surface>
    </div>
    {auth?.mode === 'demo' && <div className="mt-5 flex items-center gap-2 rounded-xl border border-line bg-white px-4 py-3 text-xs text-muted"><CalendarRange size={16} className="text-[#80a6bd]" /> Las descargas requieren iniciar sesión y tener la API conectada a la base. Esta vista demo solo presenta datos de muestra.</div>}
  </>
}
