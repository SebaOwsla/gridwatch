import type { ReactNode } from 'react'
import { AlertCircle, ChevronDown, DatabaseZap, RefreshCw } from 'lucide-react'
import type { AlertStatus, Equipment, EquipmentStatus } from '../lib/types'
import { alertStatusLabels, equipmentStatusLabels } from '../lib/format'

export function Surface({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`surface ${className}`}>{children}</section>
}

export function PageHeader({ eyebrow, title, description, action }: {
  eyebrow: string; title: string; description?: string; action?: ReactNode
}) {
  return (
    <div className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="eyebrow mb-2">{eyebrow}</p>
        <h1 className="text-[1.75rem] font-semibold tracking-tight text-ink sm:text-[2rem]">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{description}</p>}
      </div>
      {action}
    </div>
  )
}

export function SectionTitle({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 className="text-base font-semibold text-ink">{title}</h2>
        {subtitle && <p className="mt-1 text-xs text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

export function StatusBadge({ status }: { status: EquipmentStatus | AlertStatus }) {
  const label = status in equipmentStatusLabels
    ? equipmentStatusLabels[status as EquipmentStatus]
    : alertStatusLabels[status as AlertStatus]
  const color = status === 'online' || status === 'resolved'
    ? 'bg-[#eef7f3] text-[#3e806a] ring-[#d9ebdf]'
    : status === 'open' || status === 'offline'
      ? 'bg-[#fff5f2] text-[#a76856] ring-[#f3e2da]'
      : 'bg-[#eef4fa] text-[#537b98] ring-[#dce9f3]'
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${color}`}>
    <span className="h-1.5 w-1.5 rounded-full bg-current" />{label}
  </span>
}

export function EquipmentSelect({ equipment, value, onChange, className = '' }: {
  equipment: Equipment[]; value: string; onChange: (id: string) => void; className?: string
}) {
  return (
    <div className={`relative ${className}`}>
      <select className="field min-w-[210px] appearance-none pr-9" value={value} onChange={(event) => onChange(event.target.value)} aria-label="Seleccionar equipo">
        {equipment.length === 0 && <option value="">Sin equipos</option>}
        {equipment.map((item) => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
    </div>
  )
}

export function Notice({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div className="mb-6 flex items-start gap-3 rounded-2xl border border-[#e8d8d5] bg-[#fff9f7] px-4 py-3 text-sm text-[#985f54]">
    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
    <span className="flex-1">{message}</span>
    {onRetry && <button type="button" onClick={onRetry} className="inline-flex items-center gap-1 font-semibold underline underline-offset-2"><RefreshCw className="h-3.5 w-3.5" /> Reintentar</button>}
  </div>
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return <div className="flex min-h-48 flex-col items-center justify-center rounded-xl border border-dashed border-line bg-[#fbfdff] px-6 py-8 text-center">
    <DatabaseZap className="mb-3 h-7 w-7 text-[#a5c6da]" strokeWidth={1.5} />
    <p className="font-medium text-ink">{title}</p>
    <p className="mt-1 max-w-sm text-sm text-muted">{description}</p>
  </div>
}
