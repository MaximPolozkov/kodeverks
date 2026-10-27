const KEY = 'order-attribution'
const FIELDS = [
  'ref',
  'lead_id',
  'utm_source',
  'utm_medium',
  'utm_campaign',
  'utm_content',
  'utm_term',
] as const

export type Attribution = Partial<Record<(typeof FIELDS)[number], string>>

/** Сохраняет UTM-метки и параметры бота из адресной строки на время визита. */
export function captureAttribution(search: string = window.location.search): void {
  const params = new URLSearchParams(search)
  const found: Attribution = {}
  for (const field of FIELDS) {
    const value = params.get(field)
    if (value) found[field] = value.slice(0, 100)
  }
  if (Object.keys(found).length === 0) return
  try {
    sessionStorage.setItem(KEY, JSON.stringify(found))
  } catch {
    /* хранилище недоступно — атрибуция просто не сохранится */
  }
}

export function readAttribution(): Attribution {
  try {
    const raw = sessionStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as Attribution) : {}
  } catch {
    return {}
  }
}
