import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api } from '@/api/client'
import type { BotMessage, Lead, LeadStatus } from '@/api/types'
import { Badge, ErrorNote, Spinner } from '@/components/ui/misc'
import { formatDateTime, leadSourceLabels, leadStatusLabels, leadStatusTone, serviceLabels } from '@/lib/labels'

export default function LeadPage() {
  const { id } = useParams()
  const client = useQueryClient()
  const [text, setText] = useState('')

  const lead = useQuery({ queryKey: ['lead', id], queryFn: () => api<Lead>(`/api/admin/bot/leads/${id}`) })
  const messages = useQuery({
    queryKey: ['lead', id, 'messages'],
    queryFn: () => api<BotMessage[]>(`/api/admin/bot/leads/${id}/messages`),
    refetchInterval: 15_000,
  })

  const patch = useMutation({
    mutationFn: (body: { status?: LeadStatus; manual_mode?: boolean }) =>
      api<Lead>(`/api/admin/bot/leads/${id}`, { method: 'PATCH', json: body }),
    onSuccess: (data) => {
      client.setQueryData(['lead', id], data)
      client.invalidateQueries({ queryKey: ['bot', 'leads'] })
    },
  })

  const send = useMutation({
    mutationFn: (message: string) =>
      api<BotMessage[]>(`/api/admin/bot/leads/${id}/messages`, { method: 'POST', json: { text: message } }),
    onSuccess: (data) => {
      client.setQueryData(['lead', id, 'messages'], data)
      client.invalidateQueries({ queryKey: ['lead', id], exact: true })
      setText('')
    },
  })

  if (lead.isLoading) return <Spinner />
  if (lead.isError) return <ErrorNote error={lead.error} />
  const l = lead.data!
  const blocked = l.status === 'opted_out'
  const canWrite = !blocked && (l.can_contact || (messages.data?.some((m) => m.direction === 'in') ?? false))

  return (
    <>
      <Link to="/admin/bot?tab=leads" className="text-[15px] text-cobalt hover:underline">
        ← Все лиды
      </Link>
      <div className="mb-6 mt-3 flex flex-wrap items-center gap-3">
        <h1 className="break-anywhere min-w-0 text-[clamp(1.375rem,5vw,1.625rem)] font-bold">{l.author_name || `Лид №${l.id}`}</h1>
        <Badge tone={leadStatusTone[l.status]}>{leadStatusLabels[l.status]}</Badge>
      </div>

      <div className="grid gap-5 sm:gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <section className="panel flex min-h-[24rem] min-w-0 flex-col sm:min-h-[28rem]">
          <div className="border-b border-line p-4">
            <p className="text-[14px] text-muted">Исходный запрос</p>
            <p className="break-anywhere mt-1 whitespace-pre-wrap">{l.request_text || 'Клиент написал сам'}</p>
          </div>
          <ol className="max-h-[60vh] flex-1 space-y-3 overflow-y-auto p-3 xs:p-4 xl:max-h-[70vh]" aria-label="Переписка">
            {messages.isLoading && <Spinner />}
            {messages.data?.length === 0 && <p className="text-muted">Сообщений пока нет.</p>}
            {messages.data?.map((m) => (
              <li key={m.id} className={`flex ${m.direction === 'out' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[88%] rounded-lg px-3.5 py-2.5 sm:max-w-[80%] ${
                    m.direction === 'out' ? 'bg-cobalt text-white' : 'border border-line bg-paper'
                  }`}
                >
                  <p className="break-anywhere whitespace-pre-wrap text-[15px]">{m.text}</p>
                  <p className={`mt-1 text-[12px] ${m.direction === 'out' ? 'text-white/70' : 'text-muted'}`}>
                    {m.direction === 'out' ? (m.is_manual ? 'Менеджер' : 'Бот') : 'Клиент'},{' '}
                    {formatDateTime(m.created_at)}
                  </p>
                </div>
              </li>
            ))}
          </ol>
          <form
            className="border-t border-line p-3 xs:p-4"
            onSubmit={(e) => {
              e.preventDefault()
              if (text.trim()) send.mutate(text.trim())
            }}
          >
            {canWrite ? (
              <>
                <label htmlFor="reply" className="label">
                  Ответить от имени менеджера
                </label>
                <textarea id="reply" rows={3} className="input" value={text} onChange={(e) => setText(e.target.value)} />
                {send.isError && <p className="mt-2 text-danger">{send.error.message}</p>}
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <button className="btn-primary w-full xs:w-auto" disabled={!text.trim() || send.isPending}>
                    Отправить
                  </button>
                  <span className="text-[14px] text-muted">После ответа менеджера бот перестаёт отвечать сам.</span>
                </div>
              </>
            ) : (
              <p className="text-[15px] text-muted">
                {blocked
                  ? 'Клиент отказался от общения — писать ему нельзя.'
                  : 'Площадка не разрешает писать этому автору первым. Откликнитесь вручную по ссылке на пост.'}
              </p>
            )}
          </form>
        </section>

        <aside className="min-w-0 space-y-5 sm:space-y-6">
          <section className="panel p-4 sm:p-5">
            <dl className="space-y-3 text-[15px]">
              <div>
                <dt className="text-muted">Источник</dt>
                <dd>{leadSourceLabels[l.source]}</dd>
              </div>
              <div>
                <dt className="text-muted">Найден</dt>
                <dd>{formatDateTime(l.created_at)}</dd>
              </div>
              <div>
                <dt className="text-muted">Релевантность</dt>
                <dd>{l.relevance_score} из 100</dd>
              </div>
              {l.service_guess && (
                <div>
                  <dt className="text-muted">Похоже на запрос</dt>
                  <dd>{serviceLabels[l.service_guess]}</dd>
                </div>
              )}
              {l.link_sent_at && (
                <div>
                  <dt className="text-muted">Ссылка на заявку отправлена</dt>
                  <dd>{formatDateTime(l.link_sent_at)}</dd>
                </div>
              )}
            </dl>
            <div className="mt-4 flex flex-col gap-2 text-[15px]">
              {l.post_url && (
                <a href={l.post_url} target="_blank" rel="noreferrer" className="text-cobalt hover:underline">
                  Открыть исходный пост
                </a>
              )}
              {l.profile_url && (
                <a href={l.profile_url} target="_blank" rel="noreferrer" className="text-cobalt hover:underline">
                  Профиль автора
                </a>
              )}
            </div>
          </section>

          <section className="panel space-y-4 p-4 sm:p-5">
            <label className="flex items-start gap-3 text-[15px]">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 accent-cobalt"
                checked={l.manual_mode}
                disabled={blocked || patch.isPending}
                onChange={(e) => patch.mutate({ manual_mode: e.target.checked })}
              />
              <span>
                <span className="font-semibold">Диалог ведёт менеджер</span>
                <span className="block text-muted">Бот сохраняет сообщения клиента, но не отвечает.</span>
              </span>
            </label>
            <label className="block text-[15px] font-semibold">
              Статус лида
              <select
                className="input mt-1.5"
                value={l.status}
                disabled={patch.isPending}
                onChange={(e) => patch.mutate({ status: e.target.value as LeadStatus })}
              >
                {(Object.keys(leadStatusLabels) as LeadStatus[]).map((s) => (
                  <option key={s} value={s}>
                    {leadStatusLabels[s]}
                  </option>
                ))}
              </select>
            </label>
            {!blocked && (
              <button className="btn-danger w-full" onClick={() => patch.mutate({ status: 'opted_out' })}>
                Добавить в стоп-лист
              </button>
            )}
            {patch.isError && <p className="text-danger">{patch.error.message}</p>}
          </section>
        </aside>
      </div>
    </>
  )
}
