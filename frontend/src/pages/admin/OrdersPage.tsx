import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { api, buildQuery, downloadFile } from '@/api/client'
import type { OrderListItem, OrderSource, OrderStatus, Page } from '@/api/types'
import { Badge, EmptyState, ErrorNote, PageHeader, Pagination, Spinner } from '@/components/ui/misc'
import {
  contactChannels,
  formatDateTime,
  formatMoney,
  orderSourceLabels,
  orderStatusLabels,
  orderStatusTone,
  serviceLabels,
} from '@/lib/labels'

const FILTER_KEYS = ['status', 'source', 'date_from', 'date_to', 'q', 'sort', 'direction', 'page'] as const

export default function OrdersPage() {
  const [params, setParams] = useSearchParams()
  const filters = Object.fromEntries(FILTER_KEYS.map((k) => [k, params.get(k) ?? ''])) as Record<
    (typeof FILTER_KEYS)[number],
    string
  >
  const page = Number(filters.page) || 1
  const [search, setSearch] = useState(filters.q)
  const [exportError, setExportError] = useState<string | null>(null)

  const update = (patch: Partial<typeof filters>) => {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(patch)) {
      if (value) next.set(key, value)
      else next.delete(key)
    }
    if (!('page' in patch)) next.delete('page')
    setParams(next, { replace: true })
  }

  // Поиск с небольшой задержкой, чтобы не дёргать API на каждую букву
  useEffect(() => {
    const id = window.setTimeout(() => {
      if (search !== filters.q) update({ q: search })
    }, 350)
    return () => window.clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search])

  const query = { ...filters, page, page_size: 20 }
  const orders = useQuery({
    queryKey: ['orders', query],
    queryFn: () => api<Page<OrderListItem>>(`/api/admin/orders${buildQuery(query)}`),
    placeholderData: keepPreviousData,
  })

  const sortBy = (field: 'created_at' | 'budget') => {
    const current = filters.sort || 'created_at'
    const direction = current === field && (filters.direction || 'desc') === 'desc' ? 'asc' : 'desc'
    update({ sort: field, direction })
  }
  const sortMark = (field: string) =>
    (filters.sort || 'created_at') === field ? ((filters.direction || 'desc') === 'desc' ? ' ↓' : ' ↑') : ''

  const exportCsv = async () => {
    setExportError(null)
    const { status, source, date_from, date_to, q } = filters
    try {
      await downloadFile(
        `/api/admin/orders/export.csv${buildQuery({ status, source, date_from, date_to, q })}`,
        'orders.csv',
      )
    } catch (e) {
      setExportError(e instanceof Error ? e.message : 'Не удалось выгрузить файл')
    }
  }

  return (
    <>
      <PageHeader title="Заказы">
        <button className="btn-ghost" onClick={exportCsv}>
          Выгрузить в CSV
        </button>
      </PageHeader>

      <div className="panel mb-5 grid gap-3 p-3 xs:p-4 sm:grid-cols-2 xl:grid-cols-[minmax(0,2fr)_repeat(4,minmax(0,1fr))]">
        <label className="min-w-0 sm:col-span-2 xl:col-span-1">
          <span className="mb-1 block text-[13px] text-muted">Поиск</span>
          <input
            className="input"
            type="search"
            placeholder="Имя, почта или текст заявки"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <label className="min-w-0">
          <span className="mb-1 block text-[13px] text-muted">Статус</span>
          <select className="input" value={filters.status} onChange={(e) => update({ status: e.target.value })}>
            <option value="">Все статусы</option>
            {(Object.keys(orderStatusLabels) as OrderStatus[]).map((s) => (
              <option key={s} value={s}>
                {orderStatusLabels[s]}
              </option>
            ))}
          </select>
        </label>
        <label className="min-w-0">
          <span className="mb-1 block text-[13px] text-muted">Источник</span>
          <select className="input" value={filters.source} onChange={(e) => update({ source: e.target.value })}>
            <option value="">Все источники</option>
            {(Object.keys(orderSourceLabels) as OrderSource[]).map((s) => (
              <option key={s} value={s}>
                {orderSourceLabels[s]}
              </option>
            ))}
          </select>
        </label>
        <label className="min-w-0">
          <span className="mb-1 block text-[13px] text-muted">С даты</span>
          <input
            className="input"
            type="date"
            value={filters.date_from}
            max={filters.date_to || undefined}
            onChange={(e) => update({ date_from: e.target.value })}
          />
        </label>
        <label className="min-w-0">
          <span className="mb-1 block text-[13px] text-muted">По дату</span>
          <input
            className="input"
            type="date"
            value={filters.date_to}
            min={filters.date_from || undefined}
            onChange={(e) => update({ date_to: e.target.value })}
          />
        </label>
      </div>

      {exportError && <ErrorNote error={new Error(exportError)} />}
      {orders.isLoading && <Spinner />}
      {orders.isError && <ErrorNote error={orders.error} />}
      {orders.data && orders.data.items.length === 0 && (
        <EmptyState title="Заказов не найдено">
          Измените фильтры или дождитесь новых заявок с сайта.
        </EmptyState>
      )}

      {orders.data && orders.data.items.length > 0 && (
        <>
          {/* Телефоны и узкие планшеты: карточки */}
          <ul className="space-y-3 md:hidden">
            {orders.data.items.map((o) => (
              <li key={o.id}>
                <Link to={`/admin/orders/${o.id}`} className="panel block p-4 active:bg-paper">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="break-anywhere font-semibold text-cobalt">{o.name}</p>
                      <p className="break-anywhere text-[14px] text-muted">{o.email}</p>
                    </div>
                    <Badge tone={orderStatusTone[o.status]}>{orderStatusLabels[o.status]}</Badge>
                  </div>
                  <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-[14px]">
                    <div>
                      <dt className="text-muted">Бюджет</dt>
                      <dd className="font-semibold">{formatMoney(o.budget)}</dd>
                    </div>
                    <div>
                      <dt className="text-muted">Услуга</dt>
                      <dd>{o.service_type ? serviceLabels[o.service_type] : '—'}</dd>
                    </div>
                    <div>
                      <dt className="text-muted">Связь</dt>
                      <dd>{contactChannels[o.contact_channel].label}</dd>
                    </div>
                    <div>
                      <dt className="text-muted">Дата</dt>
                      <dd>{formatDateTime(o.created_at)}</dd>
                    </div>
                  </dl>
                </Link>
              </li>
            ))}
          </ul>

          {/* Планшеты и десктоп: таблица */}
          <div className="panel hidden overflow-x-auto md:block">
            <table className="w-full text-left text-[15px]">
              <thead className="border-b border-line text-[14px] text-muted">
                <tr>
                  <th className="px-4 py-3 font-semibold">
                    <button onClick={() => sortBy('created_at')}>Дата{sortMark('created_at')}</button>
                  </th>
                  <th className="px-4 py-3 font-semibold">Клиент</th>
                  <th className="px-4 py-3 font-semibold">
                    <button onClick={() => sortBy('budget')}>Бюджет{sortMark('budget')}</button>
                  </th>
                  <th className="px-4 py-3 font-semibold">Услуга</th>
                  <th className="px-4 py-3 font-semibold">Связь</th>
                  <th className="px-4 py-3 font-semibold">Источник</th>
                  <th className="px-4 py-3 font-semibold">Статус</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {orders.data.items.map((o) => (
                  <tr key={o.id} className="hover:bg-paper/70">
                    <td className="whitespace-nowrap px-4 py-3 text-muted">{formatDateTime(o.created_at)}</td>
                    <td className="px-4 py-3">
                      <Link to={`/admin/orders/${o.id}`} className="break-anywhere font-semibold text-cobalt hover:underline">
                        {o.name}
                      </Link>
                      <div className="break-anywhere text-[14px] text-muted">{o.email}</div>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">{formatMoney(o.budget)}</td>
                    <td className="px-4 py-3">{o.service_type ? serviceLabels[o.service_type] : '—'}</td>
                    <td className="px-4 py-3">{contactChannels[o.contact_channel].label}</td>
                    <td className="px-4 py-3">
                      {orderSourceLabels[o.source]}
                      {o.utm_source && <div className="text-[13px] text-muted">{o.utm_source}</div>}
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={orderStatusTone[o.status]}>{orderStatusLabels[o.status]}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            page={page}
            pageSize={orders.data.page_size}
            total={orders.data.total}
            onChange={(p) => update({ page: String(p) })}
          />
        </>
      )}
    </>
  )
}
