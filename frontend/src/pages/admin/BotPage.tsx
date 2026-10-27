import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { api, buildQuery } from '@/api/client'
import type { BotRun, BotSettings, BotSettingsData, BotStatus, FunnelStats, Lead, LeadSource, LeadStatus, Page } from '@/api/types'
import { Badge, EmptyState, ErrorNote, PageHeader, Pagination, Spinner } from '@/components/ui/misc'
import { formatDateTime, leadSourceLabels, leadStatusLabels, leadStatusTone, serviceLabels } from '@/lib/labels'

const TABS = [
  { id: 'overview', label: 'Обзор' },
  { id: 'leads', label: 'Лиды' },
  { id: 'settings', label: 'Настройки' },
  { id: 'log', label: 'Журнал' },
] as const
type TabId = (typeof TABS)[number]['id']

export default function BotPage() {
  const [params, setParams] = useSearchParams()
  const tab = (params.get('tab') as TabId) || 'overview'

  return (
    <>
      <PageHeader title="Бот для поиска клиентов" />
      <div role="tablist" aria-label="Разделы бота" className="scroll-x -mx-4 mb-5 flex gap-1 border-b border-line px-4 sm:mx-0 sm:mb-6 sm:px-0">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setParams({ tab: t.id }, { replace: true })}
            className={`-mb-px whitespace-nowrap border-b-[3px] px-4 py-2.5 text-[15px] font-semibold ${
              tab === t.id ? 'border-cobalt text-cobalt-dark' : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div role="tabpanel">
        {tab === 'overview' && <Overview />}
        {tab === 'leads' && <Leads />}
        {tab === 'settings' && <SettingsTab />}
        {tab === 'log' && <RunLog />}
      </div>
    </>
  )
}

/* ---------- Обзор ---------- */

function Overview() {
  const client = useQueryClient()
  const status = useQuery({
    queryKey: ['bot', 'status'],
    queryFn: () => api<BotStatus>('/api/admin/bot/status'),
    refetchInterval: 10_000,
  })
  const stats = useQuery({ queryKey: ['bot', 'stats'], queryFn: () => api<FunnelStats>('/api/admin/bot/stats') })

  const action = useMutation({
    mutationFn: (path: 'start' | 'stop' | 'run-now') => api<BotStatus>(`/api/admin/bot/${path}`, { method: 'POST' }),
    onSuccess: (data) => {
      client.setQueryData(['bot', 'status'], data)
      client.invalidateQueries({ queryKey: ['bot', 'runs'] })
    },
  })

  if (status.isLoading) return <Spinner />
  if (status.isError) return <ErrorNote error={status.error} />
  const s = status.data!

  const funnel = stats.data
    ? [
        ['Найдено', stats.data.found],
        ['Написали', stats.data.contacted],
        ['Ответили', stats.data.replied],
        ['Перешли к заявке', stats.data.link_sent],
        ['Оформили заказ', stats.data.converted],
      ]
    : []
  const max = Math.max(1, ...funnel.map(([, v]) => Number(v)))

  return (
    <div className="grid gap-5 sm:gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
      <section className="panel p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[14px] text-muted">Состояние</p>
            <p className="text-[20px] font-bold">
              {s.running ? 'Идёт поиск' : s.enabled ? 'Включён, ждёт расписания' : 'Выключен'}
            </p>
          </div>
          <div className="flex w-full flex-wrap gap-2 xs:w-auto">
            {s.enabled ? (
              <button className="btn-danger" onClick={() => action.mutate('stop')} disabled={action.isPending}>
                Остановить
              </button>
            ) : (
              <button className="btn-primary" onClick={() => action.mutate('start')} disabled={action.isPending}>
                Запустить
              </button>
            )}
            <button className="btn-ghost" onClick={() => action.mutate('run-now')} disabled={action.isPending || s.running}>
              Искать сейчас
            </button>
          </div>
        </div>
        {action.isError && <p className="mt-3 text-danger">{action.error.message}</p>}

        {!s.worker_available && (
          <p className="mt-4 rounded-md border border-marker bg-marker-tint px-4 py-3 text-[15px]">
            Фоновый воркер недоступен. Запустите сервисы <code>redis</code> и <code>worker</code>, иначе поиск по
            расписанию не будет работать.
          </p>
        )}

        <h3 className="mt-6 font-sans text-[16px] font-semibold">Подключения</h3>
        <ul className="mt-2 divide-y divide-line text-[15px]">
          {(Object.keys(leadSourceLabels) as LeadSource[]).map((src) => (
            <li key={src} className="flex flex-wrap justify-between gap-x-4 py-2">
              <span>{leadSourceLabels[src]}</span>
              <span className={s.sources_configured[src] ? 'text-ok' : 'text-muted'}>
                {s.sources_configured[src] ? 'Ключи заданы' : 'Не настроено'}
              </span>
            </li>
          ))}
          <li className="flex flex-wrap justify-between gap-x-4 py-2">
            <span>Языковая модель для ответов</span>
            <span className={s.llm_configured ? 'text-ok' : 'text-muted'}>
              {s.llm_configured ? 'Подключена' : 'Сценарий без ИИ'}
            </span>
          </li>
        </ul>

        {s.last_run && (
          <p className="mt-4 text-[14px] text-muted">
            Последний запуск: {formatDateTime(s.last_run.started_at)} — найдено {s.last_run.found_count}, написали{' '}
            {s.last_run.contacted_count}, ошибок {s.last_run.errors}
          </p>
        )}
      </section>

      <section className="panel p-4 sm:p-5">
        <h3 className="font-sans text-[18px] font-semibold">Воронка</h3>
        {stats.isLoading && <Spinner />}
        {stats.data && (
          <>
            <ol className="mt-4 space-y-3">
              {funnel.map(([label, value]) => (
                <li key={label as string}>
                  <div className="flex justify-between text-[15px]">
                    <span>{label}</span>
                    <span className="font-semibold tabular-nums">{value}</span>
                  </div>
                  <div className="mt-1 h-2.5 rounded bg-paper">
                    <div
                      className="h-2.5 rounded bg-cobalt"
                      style={{ width: `${(Number(value) / max) * 100}%` }}
                    />
                  </div>
                </li>
              ))}
            </ol>
            <p className="mt-4 text-[14px] text-muted">
              Отказались от общения: {stats.data.opted_out}.{' '}
              {Object.entries(stats.data.by_source)
                .map(([src, n]) => `${leadSourceLabels[src as LeadSource] ?? src}: ${n}`)
                .join(', ')}
            </p>
          </>
        )}
      </section>
    </div>
  )
}

/* ---------- Лиды ---------- */

function Leads() {
  const [status, setStatus] = useState('')
  const [source, setSource] = useState('')
  const [minScore, setMinScore] = useState(0)
  const [page, setPage] = useState(1)
  const query = { status, source, min_score: minScore, page, page_size: 20, sort: 'created_at' }

  const leads = useQuery({
    queryKey: ['bot', 'leads', query],
    queryFn: () => api<Page<Lead>>(`/api/admin/bot/leads${buildQuery(query)}`),
    placeholderData: keepPreviousData,
  })

  return (
    <>
      <div className="panel mb-5 grid gap-3 p-3 xs:p-4 sm:grid-cols-2 lg:grid-cols-3">
        <select className="input" aria-label="Статус лида" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
          <option value="">Все статусы</option>
          {(Object.keys(leadStatusLabels) as LeadStatus[]).map((s) => (
            <option key={s} value={s}>
              {leadStatusLabels[s]}
            </option>
          ))}
        </select>
        <select className="input" aria-label="Источник" value={source} onChange={(e) => { setSource(e.target.value); setPage(1) }}>
          <option value="">Все источники</option>
          {(Object.keys(leadSourceLabels) as LeadSource[]).map((s) => (
            <option key={s} value={s}>
              {leadSourceLabels[s]}
            </option>
          ))}
        </select>
        <label className="flex min-h-[44px] items-center gap-3 text-[15px] sm:col-span-2 lg:col-span-1">
          <span className="whitespace-nowrap">Релевантность от {minScore}</span>
          <input
            type="range"
            min={0}
            max={100}
            step={10}
            value={minScore}
            onChange={(e) => { setMinScore(Number(e.target.value)); setPage(1) }}
            className="w-full accent-cobalt"
          />
        </label>
      </div>

      {leads.isLoading && <Spinner />}
      {leads.isError && <ErrorNote error={leads.error} />}
      {leads.data && leads.data.items.length === 0 && (
        <EmptyState title="Лидов пока нет">
          Запустите бота на вкладке «Обзор» или добавьте ключевые слова в настройках.
        </EmptyState>
      )}
      {leads.data && leads.data.items.length > 0 && (
        <>
          <ul className="space-y-3">
            {leads.data.items.map((lead) => (
              <li key={lead.id} className="panel p-3 xs:p-4">
                <div className="flex flex-wrap items-center gap-2 text-[14px] text-muted">
                  <span>{leadSourceLabels[lead.source]}</span>
                  <span aria-hidden>/</span>
                  <span>{formatDateTime(lead.created_at)}</span>
                  <span aria-hidden>/</span>
                  <span>релевантность {lead.relevance_score}</span>
                  {lead.service_guess && (
                    <>
                      <span aria-hidden>/</span>
                      <span>{serviceLabels[lead.service_guess]}</span>
                    </>
                  )}
                  <span className="ml-auto pl-2">
                    <Badge tone={leadStatusTone[lead.status]}>{leadStatusLabels[lead.status]}</Badge>
                  </span>
                </div>
                <p className="break-anywhere mt-2 line-clamp-3 max-w-prose">{lead.request_text || 'Без текста'}</p>
                <div className="mt-3 flex flex-wrap gap-4 text-[15px]">
                  <Link to={`/admin/bot/leads/${lead.id}`} className="font-semibold text-cobalt hover:underline">
                    Открыть переписку
                  </Link>
                  {lead.post_url && (
                    <a href={lead.post_url} target="_blank" rel="noreferrer" className="text-cobalt hover:underline">
                      Исходный пост
                    </a>
                  )}
                  {lead.author_name && <span className="text-muted">{lead.author_name}</span>}
                </div>
              </li>
            ))}
          </ul>
          <Pagination page={page} pageSize={leads.data.page_size} total={leads.data.total} onChange={setPage} />
        </>
      )}
    </>
  )
}

/* ---------- Настройки ---------- */

const listToText = (list: string[]) => list.join('\n')
const textToList = (text: string) =>
  text
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)

function SettingsTab() {
  const client = useQueryClient()
  const settings = useQuery({ queryKey: ['bot', 'settings'], queryFn: () => api<BotSettings>('/api/admin/bot/settings') })
  const [draft, setDraft] = useState<BotSettingsData | null>(null)
  const [lists, setLists] = useState({ keywords: '', stop_words: '', web_sites: '' })
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (settings.data && !draft) {
      setDraft(settings.data.data)
      setLists({
        keywords: listToText(settings.data.data.keywords),
        stop_words: listToText(settings.data.data.stop_words),
        web_sites: listToText(settings.data.data.web_sites),
      })
    }
  }, [settings.data, draft])

  const save = useMutation({
    mutationFn: (data: BotSettingsData) => api<BotSettings>('/api/admin/bot/settings', { method: 'PUT', json: data }),
    onSuccess: (data) => {
      client.setQueryData(['bot', 'settings'], data)
      setDraft(data.data)
      setSaved(true)
    },
  })

  if (settings.isLoading || !draft) return settings.isError ? <ErrorNote error={settings.error} /> : <Spinner />

  const set = <K extends keyof BotSettingsData>(key: K, value: BotSettingsData[K]) => {
    setSaved(false)
    setDraft({ ...draft, [key]: value })
  }
  const setLimit = (src: LeadSource, patch: Partial<BotSettingsData['sources'][LeadSource]>) =>
    set('sources', { ...draft.sources, [src]: { ...draft.sources[src], ...patch } })

  const submit = () =>
    save.mutate({
      ...draft,
      keywords: textToList(lists.keywords),
      stop_words: textToList(lists.stop_words),
      web_sites: textToList(lists.web_sites),
    })

  return (
    <form
      className="grid max-w-5xl gap-6"
      onSubmit={(e) => {
        e.preventDefault()
        submit()
      }}
    >
      <section className="panel grid gap-5 p-4 sm:p-5 md:grid-cols-2">
        <div>
          <label htmlFor="keywords" className="label">
            Ключевые фразы
          </label>
          <textarea
            id="keywords"
            rows={8}
            className="input"
            value={lists.keywords}
            onChange={(e) => {
              setSaved(false)
              setLists({ ...lists, keywords: e.target.value })
            }}
          />
          <p className="mt-1.5 text-[14px] text-muted">По одной на строку, например «нужен сайт».</p>
        </div>
        <div>
          <label htmlFor="stop_words" className="label">
            Стоп-слова
          </label>
          <textarea
            id="stop_words"
            rows={8}
            className="input"
            value={lists.stop_words}
            onChange={(e) => {
              setSaved(false)
              setLists({ ...lists, stop_words: e.target.value })
            }}
          />
          <p className="mt-1.5 text-[14px] text-muted">Посты с этими словами пропускаются (вакансии, резюме).</p>
        </div>
      </section>

      <section className="panel p-4 sm:p-5">
        <h3 className="font-sans text-[18px] font-semibold">Источники и лимиты сообщений</h3>
        <p className="mt-1 max-w-prose text-[15px] text-muted">
          Лимиты считают только автоматические сообщения бота. Писать первым бот может лишь там, где это разрешено
          правилами площадки: во ВКонтакте — пользователям, которые разрешили сообщения от сообщества.
        </p>
        <div className="mt-4 divide-y divide-line">
          {(Object.keys(leadSourceLabels) as LeadSource[]).map((src) => (
            <div key={src} className="grid grid-cols-2 items-end gap-3 py-3 sm:grid-cols-[minmax(0,1fr)_9rem_9rem] sm:items-center">
              <label className="col-span-2 flex min-h-[44px] items-center gap-3 font-semibold sm:col-span-1">
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-cobalt"
                  checked={draft.sources[src]?.enabled ?? false}
                  onChange={(e) => setLimit(src, { enabled: e.target.checked })}
                />
                {leadSourceLabels[src]}
              </label>
              <label className="text-[14px] text-muted">
                В час
                <input
                  type="number"
                  min={0}
                  max={100}
                  className="input mt-1"
                  value={draft.sources[src]?.per_hour ?? 0}
                  onChange={(e) => setLimit(src, { per_hour: Number(e.target.value) })}
                />
              </label>
              <label className="text-[14px] text-muted">
                В сутки
                <input
                  type="number"
                  min={0}
                  max={1000}
                  className="input mt-1"
                  value={draft.sources[src]?.per_day ?? 0}
                  onChange={(e) => setLimit(src, { per_day: Number(e.target.value) })}
                />
              </label>
            </div>
          ))}
        </div>
        <div className="mt-4">
          <label htmlFor="web_sites" className="label">
            Сайты для поиска (биржи, форумы)
          </label>
          <textarea
            id="web_sites"
            rows={3}
            className="input"
            placeholder="freelance.ru"
            value={lists.web_sites}
            onChange={(e) => {
              setSaved(false)
              setLists({ ...lists, web_sites: e.target.value })
            }}
          />
        </div>
      </section>

      <section className="panel grid gap-5 p-4 sm:p-5 sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-[15px] font-semibold">
          Минимальная релевантность
          <input
            type="number"
            min={0}
            max={100}
            className="input mt-1.5"
            value={draft.min_score}
            onChange={(e) => set('min_score', Number(e.target.value))}
          />
        </label>
        <label className="text-[15px] font-semibold">
          Запуск каждые, мин
          <input
            type="number"
            min={15}
            max={1440}
            className="input mt-1.5"
            value={draft.schedule_minutes}
            onChange={(e) => set('schedule_minutes', Number(e.target.value))}
          />
        </label>
        <label className="text-[15px] font-semibold">
          Постов за запуск
          <input
            type="number"
            min={1}
            max={200}
            className="input mt-1.5"
            value={draft.search_limit}
            onChange={(e) => set('search_limit', Number(e.target.value))}
          />
        </label>
        <label className="text-[15px] font-semibold">
          Хранить лиды, дней
          <input
            type="number"
            min={7}
            max={3650}
            className="input mt-1.5"
            value={draft.retention_days}
            onChange={(e) => set('retention_days', Number(e.target.value))}
          />
        </label>
        <label className="flex items-start gap-3 text-[15px] sm:col-span-2 lg:col-span-4">
          <input
            type="checkbox"
            className="mt-1 h-4 w-4 accent-cobalt"
            checked={draft.auto_contact}
            onChange={(e) => set('auto_contact', e.target.checked)}
          />
          <span>
            <span className="font-semibold">Писать найденным лидам первым</span>
            <span className="block text-muted">
              Если выключено, бот только собирает лиды и отвечает тем, кто написал сам.
            </span>
          </span>
        </label>
      </section>

      <section className="panel grid gap-5 p-4 sm:p-5">
        <div>
          <label htmlFor="first_message" className="label">
            Шаблон первого сообщения
          </label>
          <textarea
            id="first_message"
            rows={4}
            className="input"
            value={draft.first_message_template}
            onChange={(e) => set('first_message_template', e.target.value)}
          />
          <p className="mt-1.5 text-[14px] text-muted">
            {'{snippet}'} — фрагмент запроса клиента, {'{service}'} — подходящая услуга. Если в тексте нет
            упоминания, что пишет бот, и слова «стоп», они добавятся автоматически.
          </p>
        </div>
        <div>
          <label htmlFor="system_prompt" className="label">
            Инструкция для языковой модели
          </label>
          <textarea
            id="system_prompt"
            rows={8}
            className="input"
            value={draft.system_prompt}
            onChange={(e) => set('system_prompt', e.target.value)}
          />
          <p className="mt-1.5 text-[14px] text-muted">
            Маркер [READY] в ответе модели отправляет клиенту ссылку на форму заказа, [STOP] — заносит в стоп-лист.
          </p>
        </div>
      </section>

      <div className="flex flex-wrap items-center gap-3 sm:gap-4">
        <button className="btn-primary w-full xs:w-auto" disabled={save.isPending}>
          Сохранить настройки
        </button>
        {saved && (
          <span role="status" className="text-ok">
            Настройки сохранены
          </span>
        )}
        {save.isError && <span className="text-danger">{save.error.message}</span>}
      </div>
    </form>
  )
}

/* ---------- Журнал ---------- */

function RunLog() {
  const runs = useQuery({
    queryKey: ['bot', 'runs'],
    queryFn: () => api<BotRun[]>('/api/admin/bot/runs?limit=20'),
    refetchInterval: 15_000,
  })
  if (runs.isLoading) return <Spinner />
  if (runs.isError) return <ErrorNote error={runs.error} />
  if (!runs.data?.length) return <EmptyState title="Запусков ещё не было">Нажмите «Искать сейчас» на вкладке «Обзор».</EmptyState>

  return (
    <ul className="space-y-4">
      {runs.data.map((run) => (
        <li key={run.id} className="panel p-3 xs:p-4">
          <details>
            <summary className="flex cursor-pointer flex-wrap items-center gap-x-4 gap-y-1 text-[15px]">
              <span className="font-semibold">{formatDateTime(run.started_at)}</span>
              <span>найдено {run.found_count}</span>
              <span>написали {run.contacted_count}</span>
              <span className={run.errors ? 'text-danger' : 'text-muted'}>ошибок {run.errors}</span>
              <span className="text-muted">{run.finished_at ? 'завершён' : 'выполняется'}</span>
            </summary>
            <ol className="mt-3 space-y-1 border-t border-line pt-3 text-[14px]">
              {run.log.map((line, i) => (
                <li key={i} className={line.level === 'error' ? 'text-danger' : 'text-ink'}>
                  <span className="mr-2 text-muted">{new Date(line.at).toLocaleTimeString('ru-RU')}</span>
                  {line.text}
                </li>
              ))}
            </ol>
          </details>
        </li>
      ))}
    </ul>
  )
}
