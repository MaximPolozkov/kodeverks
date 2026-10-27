export interface FieldError {
  field: string
  message: string
}

export class ApiError extends Error {
  status: number
  errors: FieldError[]

  constructor(status: number, message: string, errors: FieldError[] = []) {
    super(message)
    this.status = status
    this.errors = errors
  }
}

type Query = Record<string, string | number | boolean | null | undefined>

export function buildQuery(params: Query = {}): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  }
  const str = search.toString()
  return str ? `?${str}` : ''
}

let refreshing: Promise<boolean> | null = null

async function refreshSession(): Promise<boolean> {
  refreshing ??= fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' })
    .then((r) => r.ok)
    .catch(() => false)
    .finally(() => {
      setTimeout(() => (refreshing = null), 0)
    })
  return refreshing
}

async function parseError(resp: Response): Promise<ApiError> {
  let message = 'Не удалось выполнить запрос'
  let errors: FieldError[] = []
  try {
    const body = await resp.json()
    if (typeof body.detail === 'string') message = body.detail
    if (Array.isArray(body.errors)) errors = body.errors
  } catch {
    if (resp.status >= 500) message = 'Сервер временно недоступен. Попробуйте позже.'
  }
  return new ApiError(resp.status, message, errors)
}

export async function api<T>(
  path: string,
  init: RequestInit & { json?: unknown; retry?: boolean } = {},
): Promise<T> {
  const { json, retry = true, headers, ...rest } = init
  const resp = await fetch(path, {
    credentials: 'include',
    ...rest,
    headers: {
      ...(json !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...headers,
    },
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  }).catch(() => {
    throw new ApiError(0, 'Нет соединения с сервером. Проверьте интернет и повторите.')
  })

  const isAuthCall = path.startsWith('/api/auth/')
  if (resp.status === 401 && retry && !isAuthCall && path.startsWith('/api/admin')) {
    if (await refreshSession()) return api<T>(path, { ...init, retry: false })
  }
  if (!resp.ok) throw await parseError(resp)
  if (resp.status === 204) return undefined as T
  const type = resp.headers.get('content-type') ?? ''
  return (type.includes('application/json') ? resp.json() : resp.text()) as Promise<T>
}

export async function downloadFile(path: string, filename: string): Promise<void> {
  const resp = await fetch(path, { credentials: 'include' })
  if (!resp.ok) throw await parseError(resp)
  const blob = await resp.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.rel = 'noopener'
  // Firefox и старый Edge требуют, чтобы ссылка была в документе
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  // Safari начинает загрузку асинхронно — освобождаем URL с задержкой
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
