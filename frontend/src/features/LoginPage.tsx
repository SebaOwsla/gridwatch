import { useState, type FormEvent } from 'react'
import { ArrowRight, LockKeyhole, Radio, Zap } from 'lucide-react'
import { Navigate, useNavigate } from 'react-router'
import { useAuth } from '../app/AuthContext'

export function LoginPage() {
  const { auth, login, enterDemo } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (auth) return <Navigate to="/dashboard" replace />

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No fue posible iniciar sesión.')
    } finally {
      setBusy(false)
    }
  }

  function showDemo() {
    enterDemo()
    navigate('/dashboard')
  }

  return <div className="grid min-h-screen lg:grid-cols-[1.05fr_0.95fr]">
    <div className="relative hidden overflow-hidden bg-[#eaf4fa] px-10 py-12 lg:flex lg:flex-col xl:px-20">
      <div className="absolute inset-0 opacity-40" style={{ backgroundImage: 'linear-gradient(#c9e0ed 1px, transparent 1px), linear-gradient(90deg, #c9e0ed 1px, transparent 1px)', backgroundSize: '48px 48px' }} />
      <div className="relative z-10 flex items-center gap-3"><span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/85 text-[#3d7b9f]"><Zap size={23} /></span><span className="text-xl font-bold tracking-tight text-ink">GridWatch</span></div>
      <div className="relative z-10 my-auto max-w-xl py-16">
        <span className="eyebrow">Plataforma de monitoreo</span>
        <h1 className="mt-5 text-4xl font-semibold leading-[1.17] tracking-tight text-ink xl:text-[3.25rem]">Energía bajo una<br />mirada más clara.</h1>
        <p className="mt-6 max-w-lg text-base leading-8 text-[#5e7c91]">Visualiza el comportamiento eléctrico de tus instalaciones, revisa alertas y consulta el historial en un solo lugar.</p>
        <div className="mt-12 grid max-w-md grid-cols-3 gap-3">
          {[['24/7', 'Visibilidad'], ['3', 'Tipos de sitio'], ['100%', 'Simulado']].map(([value, label]) => <div key={label} className="rounded-2xl border border-white/80 bg-white/65 p-4"><p className="text-xl font-semibold text-[#3b7396]">{value}</p><p className="mt-1 text-xs text-muted">{label}</p></div>)}
        </div>
      </div>
      <p className="relative z-10 text-xs text-muted">Proyecto demostrativo · Sin conexión con equipos eléctricos reales</p>
    </div>
    <div className="flex min-h-screen flex-col bg-white px-6 py-8 sm:px-12 lg:px-16 xl:px-24">
      <div className="flex items-center gap-2 lg:justify-end"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#e7f1f8] text-[#477f9f] lg:hidden"><Zap size={19} /></span><span className="text-sm font-semibold text-ink lg:hidden">GridWatch</span><span className="ml-auto rounded-full border border-line bg-[#f8fbfd] px-3 py-1.5 text-[11px] font-medium text-muted lg:ml-0">Acceso seguro</span></div>
      <div className="my-auto w-full max-w-[410px] self-center py-12">
        <div className="mb-10 flex h-12 w-12 items-center justify-center rounded-2xl bg-[#e7f1f8] text-[#4d86a8]"><LockKeyhole size={22} /></div>
        <p className="eyebrow">Bienvenido de nuevo</p>
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-ink">Inicia sesión</h2>
        <p className="mt-3 text-sm leading-6 text-muted">Accede a los indicadores de tus instalaciones eléctricas.</p>
        <form onSubmit={submit} className="mt-9 space-y-5">
          <label className="block"><span className="field-label">Correo electrónico</span><input className="field mt-2" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="nombre@empresa.cl" autoComplete="username" required /></label>
          <label className="block"><span className="field-label">Contraseña</span><input className="field mt-2" type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Ingresa tu contraseña" autoComplete="current-password" required /></label>
          {error && <p role="alert" className="rounded-xl border border-[#f0ddd8] bg-[#fff8f6] px-3 py-2 text-sm text-[#a56858]">{error}</p>}
          <button className="primary-button w-full justify-center py-3" type="submit" disabled={busy}>{busy ? 'Ingresando…' : 'Entrar a GridWatch'}<ArrowRight size={17} /></button>
        </form>
        <div className="my-7 flex items-center gap-3"><span className="h-px flex-1 bg-line" /><span className="text-xs text-[#9bacb9]">o explorar sin cuenta</span><span className="h-px flex-1 bg-line" /></div>
        <button type="button" className="secondary-button w-full justify-center py-3" onClick={showDemo}><Radio size={17} /> Ver demostración</button>
        <p className="mt-5 text-center text-xs leading-5 text-muted">La vista demo contiene datos de muestra y es de solo lectura.</p>
      </div>
      <p className="text-center text-xs text-[#9aaebb]">© GridWatch · Portafolio de Analista Programador</p>
    </div>
  </div>
}
