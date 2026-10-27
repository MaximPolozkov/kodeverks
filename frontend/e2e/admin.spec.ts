import { expect, test } from '@playwright/test'

import { expectNoHorizontalOverflow, expectTouchTargets, mockAdminApi } from './helpers'

test.describe('Админ-панель', () => {
  test('/Admin без входа ведёт на страницу входа', async ({ page }) => {
    await page.route('**/api/auth/me', (r) => r.fulfill({ status: 401, json: { detail: 'Требуется вход' } }))
    await page.route('**/api/auth/refresh', (r) => r.fulfill({ status: 401, json: { detail: 'Сессия истекла' } }))

    await page.goto('/Admin')
    await expect(page).toHaveURL(/\/admin\/login$/)
    await expect(page.getByRole('heading', { name: 'Вход в панель' })).toBeVisible()
    await expectNoHorizontalOverflow(page)
    await expectTouchTargets(page)
  })

  test('список заказов: карточки на телефоне, таблица на широком экране', async ({ page }) => {
    await mockAdminApi(page)
    await page.goto('/admin/orders')
    await expect(page.getByRole('heading', { name: 'Заказы' })).toBeVisible()

    const width = page.viewportSize()!.width
    const table = page.locator('table')
    const firstName = 'Константин Длиннофамильный-Двойной'

    if (width < 768) {
      await expect(table).toBeHidden()
      await expect(page.getByRole('link', { name: new RegExp(firstName) })).toBeVisible()
    } else {
      await expect(table).toBeVisible()
      await expect(table.getByRole('link', { name: firstName })).toBeVisible()
    }
    // Длинное имя и email не растягивают страницу
    await expectNoHorizontalOverflow(page)
  })

  test('меню разделов на телефоне открывается и закрывается', async ({ page }) => {
    await mockAdminApi(page)
    await page.goto('/admin/orders')
    const width = page.viewportSize()!.width
    const nav = page.getByRole('navigation', { name: 'Разделы панели' })

    if (width < 1024) {
      await expect(nav).toBeHidden()
      await page.getByRole('button', { name: /Меню/ }).click()
      await expect(nav).toBeVisible()
      await page.route('**/api/admin/bot/**', (r) => r.fulfill({ status: 503, json: { detail: 'нет' } }))
      await nav.getByRole('link', { name: 'Бот' }).click()
      await expect(page).toHaveURL(/\/admin\/bot/)
      await expect(nav).toBeHidden()
    } else {
      await expect(nav).toBeVisible()
    }
  })
})
