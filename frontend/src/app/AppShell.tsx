import { useState } from 'react'
import { Activity, Bell, Building2, ChevronRight, FileBarChart2, LayoutDashboard, LogOut, Menu, Radio, ShieldCheck, Users, X, Zap } from 'lucide-react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router'
import { useAuth } from './AuthContext'
import { useData } from './DataContext'

const navigation = [
  { to: '/dashboard', label: 'Resumen', icon: LayoutDashboard },
  { to: '/installations', label: 'Instalaciones', icon: Building2 },
  { to: '/history', label: 'Historial', icon: Activity },
  { to: '/alerts', label: 'Alertas', icon: Bell },
  { to: '/reports', label: 'Reportes', icon: FileBarChart2 },
]

const headings: Record<string, string> = {
  '/dashboard': 'Panel eléctrico', '/installations': 'Instalaciones', '/history': 'Historial',
  '/alerts': 'Alertas', '/reports': 'Reportes', '/admin': 'Administración',
}

export function AppShell() {
  const { auth, logout } = useAuth()
  const { alerts, liveStatus } = useData()
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const openAlerts = alerts.filter((alert) => alert.status !== 'resolved').length

  function signOut() {
    logout()
    navigate('/login')
  }

  const navItems = [...navigation, ...(auth?.user.role === 'admin' ? [{ to: '/admin', label: 'Administración', icon: Users }] : [])]

  const sidebar = <>
    <div className="flex items-center justify-between px-6 pt-7 pb-9">
      <NavLink to="/dashboard" onClick={() => setMenuOpen(false)} className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-[#dcecf7] text-[#3b779c]"><Zap size={21} strokeWidth={2.2} /></span>
        <span><span className="block text-[1.18rem] font-bold leading-none tracking-tight text-ink">GridWatch</span><span className="mt-1 block text-[10px] font-medium uppercase tracking-[0.17em] text-muted">Monitoreo eléctrico</span></span>
      </NavLink>
      <button className="rounded-lg p-1 text-muted md:hidden" onClick={() => setMenuOpen(false)} aria-label="Cerrar menú"><X size={20} /></button>
    </div>
    <div className="px-4">
      <p className="px-3 pb-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-[#95a9b8]">Plataforma</p>
      <nav className="space-y-1" aria-label="Navegación principal">
        {navItems.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} onClick={() => setMenuOpen(false)} className={({ isActive }) => `nav-item ${isActive ? 'nav-item-active' : ''}`}>
          <Icon size={18} strokeWidth={1.8} /> <span className="flex-1">{label}</span>
          {to === '/alerts' && openAlerts > 0 && <span className="rounded-md bg-[#e4f0f8] px-1.5 py-0.5 text-[10px] font-semibold text-[#3c7599]">{openAlerts}</span>}
        </NavLink>)}
      </nav>
    </div>
    <div className="mt-auto px-4 pb-5">
      <div className="mx-2 mb-5 rounded-2xl border border-[#dcebf5] bg-[#f1f7fb] p-4">
        <div className="mb-2 flex items-center gap-2 text-[#4a83a6]"><Radio size={16} /><span className="text-xs font-semibold">Entorno de demostración</span></div>
        <p className="text-xs leading-5 text-muted">Telemetría simulada. Sin conexión de control a equipos reales.</p>
      </div>
      <div className="flex items-center gap-3 rounded-xl px-3 py-2">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#dbeaf4] text-xs font-semibold text-[#4b7896]">{auth?.user.full_name.charAt(0).toUpperCase()}</div>
        <div className="min-w-0 flex-1"><p className="truncate text-xs font-semibold text-ink">{auth?.user.full_name}</p><p className="truncate text-[11px] text-muted">{auth?.mode === 'demo' ? 'Vista de muestra' : auth?.user.role === 'admin' ? 'Administrador' : auth?.user.role === 'operator' ? 'Operador' : 'Observador'}</p></div>
        {import.meta.env.VITE_STATIC_DEMO !== 'true' && <button type="button" onClick={signOut} className="rounded-lg p-2 text-muted hover:bg-powder hover:text-ink" aria-label="Cerrar sesión" title="Cerrar sesión"><LogOut size={17} /></button>}
      </div>
    </div>
  </>

  return <div className="min-h-screen md:grid md:grid-cols-[250px_minmax(0,1fr)]">
    {menuOpen && <button className="fixed inset-0 z-30 bg-[#1d3e54]/30 md:hidden" onClick={() => setMenuOpen(false)} aria-label="Cerrar menú" />}
    <aside className={`fixed inset-y-0 left-0 z-40 flex w-[260px] flex-col border-r border-line bg-white transition-transform md:sticky md:top-0 md:h-screen md:w-auto md:translate-x-0 ${menuOpen ? 'translate-x-0' : '-translate-x-full'}`}>{sidebar}</aside>
    <div className="min-w-0">
      <header className="flex h-[72px] items-center justify-between border-b border-line bg-white/80 px-4 backdrop-blur-sm sm:px-6 xl:px-10">
        <div className="flex items-center gap-3">
          <button type="button" className="rounded-lg p-2 text-ink hover:bg-powder md:hidden" onClick={() => setMenuOpen(true)} aria-label="Abrir menú"><Menu size={20} /></button>
          <span className="hidden text-xs text-muted sm:inline">Plataforma</span><ChevronRight size={14} className="hidden text-[#a2b7c6] sm:inline" /><span className="text-sm font-medium text-ink">{headings[location.pathname] ?? 'GridWatch'}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-2 rounded-full border border-[#d7e8f3] bg-[#f1f8fc] px-3 py-1.5 text-[11px] font-semibold text-[#4b7896]"><span className="h-1.5 w-1.5 rounded-full bg-[#87b4cd]" />{auth?.mode === 'demo' ? (import.meta.env.VITE_STATIC_DEMO === 'true' ? 'Vista demo pública' : 'Vista demo local') : liveStatus === 'connected' ? 'En vivo · simulador' : liveStatus === 'connecting' ? 'Conectando…' : 'Sin conexión en vivo'}</span>
          <span className="hidden h-8 w-8 items-center justify-center rounded-full bg-[#eff5f9] text-[#6a8aa0] sm:flex"><ShieldCheck size={16} /></span>
        </div>
      </header>
      <main className="mx-auto max-w-[1500px] px-4 py-7 sm:px-6 sm:py-9 xl:px-10"><Outlet /></main>
    </div>
  </div>
}
