import { useEffect, useState, type FormEvent } from 'react'
import { Building2, Factory, Landmark, MapPin, Plus, Power, Settings2, Waves } from 'lucide-react'
import { canManage, useAuth } from '../app/AuthContext'
import { useData } from '../app/DataContext'
import { EmptyState, Notice, PageHeader, SectionTitle, StatusBadge, Surface } from '../components/UI'
import { createEquipment, createInstallation, updateEquipment, updateInstallation } from '../lib/api'
import { equipmentLabels, formatElectrical, installationLabels } from '../lib/format'
import type { EquipmentKind, EquipmentStatus, InstallationKind } from '../lib/types'

const siteIcons = { mine: Factory, hydroelectric: Waves, substation: Landmark }

export function InstallationsPage() {
  const { auth } = useAuth()
  const { installations, equipment, error: loadError, refresh } = useData()
  const [siteId, setSiteId] = useState('')
  const [showSiteForm, setShowSiteForm] = useState(false)
  const [showEquipmentForm, setShowEquipmentForm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [siteForm, setSiteForm] = useState({ code: '', name: '', kind: 'mine' as InstallationKind, location: '' })
  const [assetForm, setAssetForm] = useState({ code: '', name: '', kind: 'meter' as EquipmentKind, nominal_voltage_v: '' })

  useEffect(() => {
    if (installations.length && !installations.some((site) => site.id === siteId)) setSiteId(installations[0].id)
  }, [installations, siteId])

  const selected = installations.find((site) => site.id === siteId)
  const assets = equipment.filter((item) => item.installation_id === siteId)
  const editable = canManage(auth)

  async function submitSite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (auth?.mode !== 'api') return
    setBusy(true); setError(null)
    try {
      const created = await createInstallation(auth.token, {
        ...siteForm, location: siteForm.location || null,
        timezone: 'America/Santiago', is_active: true,
      })
      await refresh()
      setSiteId(created.id)
      setSiteForm({ code: '', name: '', kind: 'mine', location: '' })
      setShowSiteForm(false)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudo crear la instalación.')
    } finally { setBusy(false) }
  }

  async function submitEquipment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (auth?.mode !== 'api' || !selected) return
    setBusy(true); setError(null)
    try {
      await createEquipment(auth.token, {
        installation_id: selected.id, code: assetForm.code, name: assetForm.name,
        kind: assetForm.kind, status: 'offline',
        nominal_voltage_v: assetForm.nominal_voltage_v ? Number(assetForm.nominal_voltage_v) : null,
      })
      await refresh()
      setAssetForm({ code: '', name: '', kind: 'meter', nominal_voltage_v: '' })
      setShowEquipmentForm(false)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudo crear el equipo.')
    } finally { setBusy(false) }
  }

  async function toggleSite() {
    if (auth?.mode !== 'api' || !selected) return
    setBusy(true); setError(null)
    try { await updateInstallation(auth.token, { ...selected, is_active: !selected.is_active }); await refresh() }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'No se pudo actualizar la instalación.') }
    finally { setBusy(false) }
  }

  async function changeStatus(id: string, status: EquipmentStatus) {
    if (auth?.mode !== 'api') return
    const asset = equipment.find((item) => item.id === id)
    if (!asset) return
    setBusy(true); setError(null)
    try { await updateEquipment(auth.token, { ...asset, status }); await refresh() }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'No se pudo actualizar el equipo.') }
    finally { setBusy(false) }
  }

  return <>
    <PageHeader eyebrow="Inventario eléctrico" title="Instalaciones y equipos" description="Organiza los sitios monitoreados y revisa el estado de cada activo." action={editable && <button className="primary-button" type="button" onClick={() => setShowSiteForm(!showSiteForm)}><Plus size={16} /> Nueva instalación</button>} />
    {(error || loadError) && <Notice message={error || loadError || ''} onRetry={() => { setError(null); void refresh() }} />}
    {auth?.mode === 'demo' && <p className="mb-5 text-xs text-muted">Vista demo de solo lectura. Inicia sesión con la API para administrar instalaciones.</p>}
    {showSiteForm && editable && <Surface className="mb-6 p-5 sm:p-6"><SectionTitle title="Nueva instalación" subtitle="Ingresa los datos básicos del sitio" /><form onSubmit={submitSite} className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <label><span className="field-label">Código</span><input className="field mt-1.5" value={siteForm.code} onChange={(event) => setSiteForm({ ...siteForm, code: event.target.value })} placeholder="MIN-NORTE" required maxLength={32} /></label>
      <label><span className="field-label">Nombre</span><input className="field mt-1.5" value={siteForm.name} onChange={(event) => setSiteForm({ ...siteForm, name: event.target.value })} placeholder="Complejo Minero Norte" required maxLength={120} /></label>
      <label><span className="field-label">Tipo</span><select className="field mt-1.5" value={siteForm.kind} onChange={(event) => setSiteForm({ ...siteForm, kind: event.target.value as InstallationKind })}><option value="mine">Minería</option><option value="hydroelectric">Hidroeléctrica</option><option value="substation">Subestación</option></select></label>
      <label><span className="field-label">Ubicación</span><input className="field mt-1.5" value={siteForm.location} onChange={(event) => setSiteForm({ ...siteForm, location: event.target.value })} placeholder="Región, ciudad o referencia" maxLength={160} /></label>
      <div className="sm:col-span-2 xl:col-span-4 flex justify-end gap-2"><button type="button" className="secondary-button" onClick={() => setShowSiteForm(false)}>Cancelar</button><button type="submit" className="primary-button" disabled={busy}>Guardar instalación</button></div>
    </form></Surface>}

    {installations.length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {installations.map((site) => {
        const Icon = siteIcons[site.kind]
        const count = equipment.filter((item) => item.installation_id === site.id).length
        return <button key={site.id} type="button" onClick={() => setSiteId(site.id)} className={`surface p-5 text-left transition-colors hover:border-[#bdd6e5] ${site.id === siteId ? 'border-[#a9cde1] bg-[#fbfdff] ring-2 ring-[#e4f2fa]' : ''}`}>
          <div className="flex items-start justify-between"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#edf6fb] text-[#6798b6]"><Icon size={19} strokeWidth={1.7} /></span><span className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${site.is_active ? 'bg-[#edf7f3] text-[#4e8a72]' : 'bg-[#f4f5f6] text-[#8c9ba4]'}`}>{site.is_active ? 'Activa' : 'Inactiva'}</span></div>
          <p className="mt-4 text-[10px] font-semibold uppercase tracking-[.12em] text-[#82a6bd]">{installationLabels[site.kind]} · {site.code}</p><h2 className="mt-1 text-base font-semibold text-ink">{site.name}</h2><p className="mt-2 flex items-center gap-1 text-xs text-muted"><MapPin size={13} />{site.location ?? 'Sin ubicación definida'}</p><div className="mt-5 flex items-center justify-between border-t border-line pt-3 text-xs text-muted"><span>{count} {count === 1 ? 'equipo' : 'equipos'}</span><span className="font-medium text-[#4e86a7]">Ver detalle →</span></div>
        </button>
      })}
    </div> : <Surface className="p-5"><EmptyState title="Sin instalaciones" description="Crea tu primer sitio para comenzar a registrar equipos." /></Surface>}

    {selected && <Surface className="mt-6 p-5 sm:p-6">
      <SectionTitle title={selected.name} subtitle={`${installationLabels[selected.kind]} · ${selected.code}`} action={<div className="flex flex-wrap gap-2">{editable && <><button type="button" className="secondary-button" onClick={toggleSite} disabled={busy}><Power size={15} />{selected.is_active ? 'Desactivar' : 'Activar'}</button><button type="button" className="primary-button" onClick={() => setShowEquipmentForm(!showEquipmentForm)}><Plus size={15} /> Agregar equipo</button></>}</div>} />
      {showEquipmentForm && editable && <form onSubmit={submitEquipment} className="mb-6 grid gap-4 rounded-2xl border border-line bg-[#f9fcfe] p-4 sm:grid-cols-2 xl:grid-cols-4">
        <label><span className="field-label">Código</span><input className="field mt-1.5" value={assetForm.code} onChange={(event) => setAssetForm({ ...assetForm, code: event.target.value })} placeholder="TR-01" required maxLength={32} /></label>
        <label><span className="field-label">Nombre</span><input className="field mt-1.5" value={assetForm.name} onChange={(event) => setAssetForm({ ...assetForm, name: event.target.value })} placeholder="Transformador principal" required maxLength={120} /></label>
        <label><span className="field-label">Tipo</span><select className="field mt-1.5" value={assetForm.kind} onChange={(event) => setAssetForm({ ...assetForm, kind: event.target.value as EquipmentKind })}>{Object.entries(equipmentLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label><span className="field-label">Voltaje nominal (V)</span><input className="field mt-1.5" type="number" min="0.01" step="any" value={assetForm.nominal_voltage_v} onChange={(event) => setAssetForm({ ...assetForm, nominal_voltage_v: event.target.value })} placeholder="13800" /></label>
        <div className="flex justify-end gap-2 sm:col-span-2 xl:col-span-4"><button type="button" className="secondary-button" onClick={() => setShowEquipmentForm(false)}>Cancelar</button><button type="submit" className="primary-button" disabled={busy}>Guardar equipo</button></div>
      </form>}
      {assets.length ? <div className="soft-scroll overflow-x-auto"><table className="min-w-full text-left text-sm"><thead><tr className="border-b border-line text-xs font-medium text-muted"><th className="pb-3 pr-4">Equipo</th><th className="pb-3 pr-4">Tipo</th><th className="pb-3 pr-4">Voltaje nominal</th><th className="pb-3 pr-4">Estado</th>{editable && <th className="pb-3 text-right">Gestionar</th>}</tr></thead><tbody className="divide-y divide-line">{assets.map((asset) => <tr key={asset.id}><td className="py-4 pr-4"><div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#f0f6fa] text-[#7399b2]"><Settings2 size={17} /></span><span><strong className="block font-semibold text-ink">{asset.name}</strong><small className="text-xs text-muted">{asset.code}</small></span></div></td><td className="py-4 pr-4 text-muted">{equipmentLabels[asset.kind]}</td><td className="py-4 pr-4 text-ink">{formatElectrical(asset.nominal_voltage_v, 'V')}</td><td className="py-4 pr-4"><StatusBadge status={asset.status} /></td>{editable && <td className="py-4 text-right"><select className="field min-w-[145px]" value={asset.status} onChange={(event) => { void changeStatus(asset.id, event.target.value as EquipmentStatus) }} disabled={busy} aria-label={`Estado de ${asset.name}`}><option value="online">En línea</option><option value="offline">Fuera de línea</option><option value="maintenance">Mantenimiento</option></select></td>}</tr>)}</tbody></table></div> : <EmptyState title="Sin equipos registrados" description="Agrega un equipo para asociar mediciones y reglas de alerta a esta instalación." />}
    </Surface>}
    {!selected && installations.length === 0 && <div className="mt-6 flex items-center gap-2 text-xs text-muted"><Building2 size={15} /> No hay equipos disponibles para mostrar.</div>}
  </>
}
