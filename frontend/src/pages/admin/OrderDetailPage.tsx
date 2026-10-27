import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api } from '@/api/client'
import type { OrderDetail, OrderStatus } from '@/api/types'
import { Badge, ErrorNote, Spinner } from '@/components/ui/misc'
import {
  contactChannels,
  formatDateTime,
  formatMoney,
  orderSourceLabels,
  orderStatusLabels,
  orderStatusTone,
  serviceLabels,
} from '@/lib/labels'

export default function OrderDetailPage() {
  const { id } = useParams()
  const client = useQueryClient()
  const [comment, setComment] = useState('')
  const key = ['order', id]

  const order = useQuery({
    queryKey: key,
    queryFn: () => api<OrderDetail>(`/api/admin/orders/${id}`),
  })

  const onSaved = (data: OrderDetail) => {
    client.setQueryData(key, data)
    client.invalidateQueries({ queryKey: ['orders'] })
  }

  const setStatus = useMutation({
    mutationFn: (status: OrderStatus) =>
      api<OrderDetail>(`/api/admin/orders/${id}`, { method: 'PATCH', json: { status } }),
    onSuccess: onSaved,
  })

  const addComment = useMutation({
    mutationFn: (text: string) =>
      api<OrderDetail>(`/api/admin/orders/${id}/comments`, { method: 'POST', json: { text } }),
    onSuccess: (data) => {
      onSaved(data)
      setComment('')
    },
  })

  if (order.isLoading) return <Spinner />
  if (order.isError) return <ErrorNote error={order.error} />
  const o = order.data!

  const utm = [
    ['source', o.utm_source],
    ['medium', o.utm_medium],
    ['campaign', o.utm_campaign],
    ['content', o.utm_content],
    ['term', o.utm_term],
  ].filter(([, v]) => v)

  return (
    <>
      <Link to="/admin/orders" className="text-[15px] text-cobalt hover:underline">
        ← Все заказы
      </Link>
      <div className="mb-6 mt-3 flex flex-wrap items-center gap-3">
        <h1 className="text-[clamp(1.375rem,5vw,1.625rem)] font-bold">Заказ №{o.id}</h1>
        <Badge tone={orderStatusTone[o.status]}>{orderStatusLabels[o.status]}</Badge>
      </div>

      <div className="grid gap-5 sm:gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <div className="min-w-0 space-y-5 sm:space-y-6">
          <section className="panel p-4 sm:p-5">
            <dl className="grid gap-4 sm:grid-cols-2">
              <div>
                <dt className="text-[14px] text-muted">Клиент</dt>
                <dd className="break-anywhere font-semibold">{o.name}</dd>
              </div>
              <div>
                <dt className="text-[14px] text-muted">Почта</dt>
                <dd>
                  <a className="break-anywhere text-cobalt hover:underline" href={`mailto:${o.email}`}>
                    {o.email}
                  </a>
                </dd>
              </div>
              <div>
                <dt className="text-[14px] text-muted">Удобная связь</dt>
                <dd>
                  {contactChannels[o.contact_channel].label}
                  {o.contact_link && (
                    <a
                      className="break-anywhere ml-2 font-semibold text-cobalt hover:underline"
                      href={o.contact_link}
                      target={o.contact_link.startsWith('https://') ? '_blank' : undefined}
                      rel="noopener noreferrer"
                    >
                      {o.contact_value ?? o.email}
                    </a>
                  )}
                </dd>
              </div>
              <div>
                <dt className="text-[14px] text-muted">Уведомление во ВКонтакте</dt>
                <dd>{o.vk_notified_at ? `Отправлено ${formatDateTime(o.vk_notified_at)}` : 'Не отправлялось'}</dd>
              </div>
              <div>
                <dt className="text-[14px] text-muted">Бюджет</dt>
                <dd className="font-semibold">{formatMoney(o.budget)}</dd>
              </div>
              <div>
                <dt className="text-[14px] text-muted">Услуга</dt>
                <dd>{o.service_type ? serviceLabels[o.service_type] : 'Не выбрана'}</dd>
              </div>
              <div>
                <dt className="text-[14px] text-muted">Источник</dt>
                <dd>
                  {orderSourceLabels[o.source]}
                  {o.lead_id && (
                    <Link to={`/admin/bot/leads/${o.lead_id}`} className="ml-2 text-cobalt hover:underline">
                      лид №{o.lead_id}
                    </Link>
                  )}
                </dd>
              </div>
              <div>
                <dt className="text-[14px] text-muted">Создан</dt>
                <dd>{formatDateTime(o.created_at)}</dd>
              </div>
              {utm.length > 0 && (
                <div className="sm:col-span-2">
                  <dt className="text-[14px] text-muted">UTM-метки</dt>
                  <dd className="break-anywhere text-[15px]">{utm.map(([k, v]) => `${k}: ${v}`).join(', ')}</dd>
                </div>
              )}
            </dl>
            <h2 className="mt-6 font-sans text-[16px] font-semibold">Описание задачи</h2>
            <p className="break-anywhere mt-2 max-w-prose whitespace-pre-wrap">{o.description}</p>
          </section>

          <section className="panel p-4 sm:p-5">
            <h2 className="font-sans text-[18px] font-semibold">Комментарии менеджеров</h2>
            {o.comments.length === 0 && <p className="mt-3 text-muted">Пока нет комментариев.</p>}
            <ul className="mt-4 space-y-4">
              {o.comments.map((c) => (
                <li key={c.id} className="border-l-2 border-line pl-4">
                  <p className="text-[14px] text-muted">
                    {c.author_name ?? 'Удалённый пользователь'}, {formatDateTime(c.created_at)}
                  </p>
                  <p className="break-anywhere mt-1 whitespace-pre-wrap">{c.text}</p>
                </li>
              ))}
            </ul>
            <form
              className="mt-5"
              onSubmit={(e) => {
                e.preventDefault()
                if (comment.trim()) addComment.mutate(comment.trim())
              }}
            >
              <label htmlFor="comment" className="label">
                Новый комментарий
              </label>
              <textarea
                id="comment"
                rows={3}
                className="input"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
              />
              {addComment.isError && <p className="mt-2 text-danger">{addComment.error.message}</p>}
              <button className="btn-primary mt-3 w-full sm:w-auto" disabled={!comment.trim() || addComment.isPending}>
                Добавить комментарий
              </button>
            </form>
          </section>
        </div>

        <aside className="min-w-0 space-y-5 sm:space-y-6">
          <section className="panel p-4 sm:p-5">
            <h2 className="font-sans text-[18px] font-semibold">Статус</h2>
            <div className="mt-3 grid grid-cols-1 gap-2 xs:grid-cols-2 xl:grid-cols-1">
              {(Object.keys(orderStatusLabels) as OrderStatus[]).map((s) => (
                <button
                  key={s}
                  className={`btn justify-start border ${
                    s === o.status ? 'border-cobalt bg-cobalt-tint text-cobalt-dark' : 'border-line bg-white'
                  }`}
                  aria-pressed={s === o.status}
                  disabled={setStatus.isPending}
                  onClick={() => s !== o.status && setStatus.mutate(s)}
                >
                  {orderStatusLabels[s]}
                </button>
              ))}
            </div>
            {setStatus.isError && <p className="mt-2 text-danger">{setStatus.error.message}</p>}
          </section>

          <section className="panel p-4 sm:p-5">
            <h2 className="font-sans text-[18px] font-semibold">История изменений</h2>
            <ol className="mt-3 space-y-3 text-[15px]">
              {o.history.map((h) => (
                <li key={h.id}>
                  <span className="font-semibold">
                    {h.old_status ? `${orderStatusLabels[h.old_status]} → ` : 'Создан: '}
                    {orderStatusLabels[h.new_status]}
                  </span>
                  <div className="text-[14px] text-muted">
                    {formatDateTime(h.changed_at)}
                    {h.author_name ? `, ${h.author_name}` : ''}
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </aside>
      </div>
    </>
  )
}
