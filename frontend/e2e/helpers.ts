import { expect, type Page } from '@playwright/test'

/** Страница не должна прокручиваться по горизонтали ни на одном экране. */
export async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() => {
    const doc = document.documentElement
    const offenders: string[] = []
    if (doc.scrollWidth > doc.clientWidth + 1) {
      for (const el of Array.from(document.querySelectorAll<HTMLElement>('body *'))) {
        const rect = el.getBoundingClientRect()
        if (rect.right > doc.clientWidth + 1 && rect.width > 0) {
          offenders.push(`${el.tagName.toLowerCase()}.${String(el.className).slice(0, 60)}`)
          if (offenders.length >= 5) break
        }
      }
    }
    return { scrollWidth: doc.scrollWidth, clientWidth: doc.clientWidth, offenders }
  })
  expect(overflow.offenders, `Элементы шире экрана (${overflow.scrollWidth} > ${overflow.clientWidth})`).toEqual([])
}

/** Все видимые кнопки и ссылки-кнопки не меньше 40px — удобно нажимать пальцем. */
export async function expectTouchTargets(page: Page) {
  const small = await page.evaluate(() =>
    Array.from(document.querySelectorAll<HTMLElement>('button, .btn, a.btn-primary, a.btn-ghost, a.btn-ink'))
      .filter((el) => {
        const r = el.getBoundingClientRect()
        const style = getComputedStyle(el)
        return r.width > 0 && r.height > 0 && style.visibility !== 'hidden' && r.height < 40
      })
      .map((el) => `${el.textContent?.trim().slice(0, 30)} (${Math.round(el.getBoundingClientRect().height)}px)`),
  )
  expect(small, 'Слишком маленькие кнопки').toEqual([])
}

export const adminUser = {
  id: 1,
  email: 'admin@example.com',
  name: 'Анна Смирнова',
  phone: null,
  avatar_url: null,
  role: 'admin',
  is_active: true,
  created_at: '2026-10-01T10:00:00Z',
}

export const sampleOrders = {
  items: Array.from({ length: 6 }, (_, i) => ({
    id: i + 1,
    name: i === 0 ? 'Константин Длиннофамильный-Двойной' : `Клиент ${i + 1}`,
    email: i === 0 ? 'very.long.email.address.for.testing@some-company-domain.example.com' : `client${i}@example.com`,
    budget: String(150000 + i * 25000),
    service_type: ['website', 'bot', 'crm', 'app'][i % 4],
    source: ['site', 'bot', 'utm'][i % 3],
    utm_source: i % 3 === 2 ? 'yandex' : null,
    status: ['new', 'in_progress', 'negotiation', 'done', 'rejected', 'new'][i],
    created_at: '2026-10-20T09:30:00Z',
  })),
  total: 6,
  page: 1,
  page_size: 20,
}

/** Подменяет API панели: пользователь уже вошёл, есть несколько заказов. */
export async function mockAdminApi(page: Page) {
  await page.route('**/api/auth/me', (r) => r.fulfill({ json: adminUser }))
  await page.route('**/api/admin/orders/new-count', (r) => r.fulfill({ json: { count: 2 } }))
  await page.route(/\/api\/admin\/orders(\?.*)?$/, (r) => r.fulfill({ json: sampleOrders }))
}
