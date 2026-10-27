import type { ReactNode } from 'react'

export function Badge({ tone, children }: { tone: string; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded border px-2 py-0.5 text-[13px] font-semibold ${tone}`}
    >
      {children}
    </span>
  )
}

export function Spinner({ label = 'Загрузка' }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-3 py-10 text-muted">
      <span aria-hidden className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-cobalt" />
      {label}…
    </div>
  )
}

export function ErrorNote({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : 'Не удалось загрузить данные'
  return (
    <div role="alert" className="rounded-md border border-danger/30 bg-danger/5 px-4 py-3 text-danger">
      {message}
    </div>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-line bg-white px-4 py-10 text-center sm:px-6 sm:py-12">
      <p className="font-semibold">{title}</p>
      {children && <div className="mx-auto mt-2 max-w-md text-muted">{children}</div>}
    </div>
  )
}

interface PaginationProps {
  page: number
  pageSize: number
  total: number
  onChange: (page: number) => void
}

export function Pagination({ page, pageSize, total, onChange }: PaginationProps) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  if (pages <= 1) return null
  return (
    <nav className="flex flex-wrap items-center justify-between gap-3 pt-4 text-[15px]" aria-label="Страницы">
      <span className="text-muted">
        Страница {page} из {pages}, всего {total}
      </span>
      <div className="flex w-full gap-2 xs:w-auto">
        <button className="btn-ghost flex-1 xs:flex-none" disabled={page <= 1} onClick={() => onChange(page - 1)}>
          Назад
        </button>
        <button className="btn-ghost flex-1 xs:flex-none" disabled={page >= pages} onClick={() => onChange(page + 1)}>
          Вперёд
        </button>
      </div>
    </nav>
  )
}

export function PageHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3 sm:mb-6 sm:gap-4">
      <h1 className="min-w-0 text-[clamp(1.375rem,5vw,1.625rem)] font-bold leading-tight">{title}</h1>
      {children && <div className="flex flex-wrap gap-2">{children}</div>}
    </div>
  )
}
