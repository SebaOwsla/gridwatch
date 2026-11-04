import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Plus, ShieldCheck, UserRound } from 'lucide-react'
import { Navigate } from 'react-router'
import { useAuth } from '../app/AuthContext'
import { EmptyState, Notice, PageHeader, SectionTitle, Surface } from '../components/UI'
import { createUser, getAudit, getUsers } from '../lib/api'
import { formatDate } from '../lib/format'
import type { AuditEvent, Role, User } from '../lib/types'

const roleLabels: Record<Role, string> = { admin: 'Administrador', operator: 'Operador', viewer: 'Observador' }

export function AdminPage() {
  const { auth } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [audit, setAudit] = useState<AuditEvent[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ email: '', full_name: '', password: '', role: 'viewer' as Role })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const token = auth?.mode === 'api' && auth.user.role === 'admin' ? auth.token : null

  const refresh = useCallback(async () => {
    if (!token) return
    try {
      const [people, events] = await Promise.all([getUsers(token), getAudit(token)])
      setUsers(people)
      setAudit(events)
      setError(null)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'No se pudo cargar la administración.') }
  }, [token])

  useEffect(() => { void refresh() }, [refresh])

  if (auth?.user.role !== 'admin') return <Navigate to="/dashboard" replace />

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!token) return
    setBusy(true); setError(null)
    try {
      await createUser(token, form)
      await refresh()
      setForm({ email: '', full_name: '', password: '', role: 'viewer' })
      setShowForm(false)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'No se pudo crear el usuario.') }
    finally { setBusy(false) }
  }

  return <>
    <PageHeader eyebrow="Control de acceso" title="Administración" description="Gestiona usuarios y consulta las acciones registradas por la plataforma." action={<button type="button" className="primary-button" onClick={() => setShowForm(!showForm)}><Plus size={16} /> Nuevo usuario</button>} />
    {error && <Notice message={error} onRetry={() => { void refresh() }} />}
    {showForm && <Surface className="mb-6 p-5 sm:p-6"><SectionTitle title="Crear usuario" subtitle="El acceso queda sujeto al rol asignado" /><form onSubmit={submit} className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <label><span className="field-label">Nombre completo</span><input className="field mt-1.5" value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} required maxLength={120} /></label>
      <label><span className="field-label">Correo electrónico</span><input className="field mt-1.5" type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required /></label>
      <label><span className="field-label">Contraseña inicial</span><input className="field mt-1.5" type="password" minLength={12} value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} required autoComplete="new-password" /></label>
      <label><span className="field-label">Rol</span><select className="field mt-1.5" value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value as Role })}><option value="viewer">Observador</option><option value="operator">Operador</option><option value="admin">Administrador</option></select></label>
      <div className="flex justify-end gap-2 sm:col-span-2 xl:col-span-4"><button type="button" className="secondary-button" onClick={() => setShowForm(false)}>Cancelar</button><button type="submit" className="primary-button" disabled={busy}>Crear usuario</button></div>
    </form></Surface>}
    <Surface className="p-5 sm:p-6"><SectionTitle title="Usuarios" subtitle={`${users.length} cuentas registradas`} action={<UserRound size={17} className="text-[#88a7b9]" />} />{users.length ? <div className="soft-scroll overflow-x-auto"><table className="min-w-[590px] w-full text-left text-sm"><thead><tr className="border-b border-line text-xs text-muted"><th className="pb-3 pr-4">Nombre</th><th className="pb-3 pr-4">Correo</th><th className="pb-3 pr-4">Rol</th><th className="pb-3">Estado</th></tr></thead><tbody className="divide-y divide-line">{users.map((user) => <tr key={user.id}><td className="py-3.5 pr-4 font-medium text-ink">{user.full_name}</td><td className="py-3.5 pr-4 text-muted">{user.email}</td><td className="py-3.5 pr-4 text-muted">{roleLabels[user.role]}</td><td className="py-3.5"><span className={`rounded-full px-2.5 py-1 text-xs ${user.is_active ? 'bg-[#edf7f3] text-[#4e8a72]' : 'bg-[#f3f5f6] text-[#8295a2]'}`}>{user.is_active ? 'Activo' : 'Inactivo'}</span></td></tr>)}</tbody></table></div> : <EmptyState title="Sin usuarios" description="Las cuentas creadas se mostrarán en esta sección." />}</Surface>
    <Surface className="mt-6 p-5 sm:p-6"><SectionTitle title="Auditoría reciente" subtitle="Operaciones registradas con fecha y actor" action={<ShieldCheck size={18} className="text-[#88a7b9]" />} />{audit.length ? <div className="soft-scroll overflow-x-auto"><table className="min-w-[680px] w-full text-left text-sm"><thead><tr className="border-b border-line text-xs text-muted"><th className="pb-3 pr-4">Fecha</th><th className="pb-3 pr-4">Acción</th><th className="pb-3 pr-4">Entidad</th><th className="pb-3">Actor</th></tr></thead><tbody className="divide-y divide-line">{audit.map((event) => <tr key={event.id}><td className="py-3.5 pr-4 text-muted">{formatDate(event.created_at)}</td><td className="py-3.5 pr-4 font-medium text-ink">{event.action.replaceAll('.', ' · ')}</td><td className="py-3.5 pr-4 text-muted">{event.entity_type}</td><td className="py-3.5 text-muted">{users.find((user) => user.id === event.actor_id)?.full_name ?? 'Sistema'}</td></tr>)}</tbody></table></div> : <EmptyState title="Sin eventos de auditoría" description="Las acciones de los usuarios aparecerán aquí cuando se registren." />}</Surface>
  </>
}
