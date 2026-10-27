import { expect, test } from '@playwright/test'

import { expectNoHorizontalOverflow, expectTouchTargets } from './helpers'

test.describe('Главная страница', () => {
  test('без горизонтальной прокрутки и с крупными кнопками', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await expectNoHorizontalOverflow(page)
    await expectTouchTargets(page)

    // Проверяем и нижние блоки страницы
    await page.locator('#order').scrollIntoViewIfNeeded()
    await expectNoHorizontalOverflow(page)
  })

  test('все четыре услуги и форма заказа на месте', async ({ page }) => {
    await page.goto('/')
    for (const title of ['Сайты', 'Боты', 'CRM-системы', 'Приложения']) {
      await expect(page.locator('#services').getByRole('heading', { name: title })).toBeVisible()
    }
    for (const label of ['Имя', 'Почта', 'Предполагаемый бюджет, ₽', 'Подробное описание задачи']) {
      await expect(page.getByLabel(label)).toBeAttached()
    }
  })

  test('меню: на телефоне — кнопка, на десктопе — ссылки', async ({ page }) => {
    await page.goto('/')
    const width = page.viewportSize()!.width
    const toggle = page.getByRole('button', { name: 'Открыть меню' })

    if (width < 768) {
      await expect(toggle).toBeVisible()
      await toggle.click()
      const menu = page.getByRole('navigation', { name: 'Мобильное меню' })
      await expect(menu).toBeVisible()
      await menu.getByRole('link', { name: 'Услуги' }).click()
      await expect(menu).toBeHidden()
      await expect(page.locator('#services')).toBeInViewport()
    } else {
      await expect(toggle).toBeHidden()
      await expect(page.getByRole('navigation', { name: 'Основное меню' })).toBeVisible()
    }
  })

  test('выбор услуги подставляет её в форму', async ({ page }) => {
    await page.goto('/')
    await page.locator('#services article').filter({ hasText: 'CRM-системы' }).getByRole('button', { name: 'Выбрать' }).click()
    await expect(page.getByLabel('Что нужно сделать')).toHaveValue('crm')
    await expect(page.locator('#order')).toBeInViewport()
  })

  test('форма показывает ошибки и отправляет заявку', async ({ page }) => {
    let payload: Record<string, unknown> | null = null
    await page.route('**/api/orders', async (route) => {
      payload = route.request().postDataJSON()
      await route.fulfill({ status: 201, json: { ok: true, detail: 'ok' } })
    })

    await page.goto('/?utm_source=yandex&utm_campaign=autumn')
    const form = page.locator('#order form')
    await form.getByRole('button', { name: 'Отправить заявку' }).click()
    await expect(form.getByText('Укажите имя — минимум 2 символа')).toBeVisible()

    await form.getByLabel('Имя').fill('Иван')
    await form.getByLabel('Почта').fill('ivan@example.com')
    await form.getByLabel('Предполагаемый бюджет, ₽').fill('150 000')
    await form.getByLabel('Подробное описание задачи').fill('Нужен интернет-магазин с каталогом и онлайн-оплатой')
    await form.getByRole('checkbox').check()
    await form.getByRole('button', { name: 'Отправить заявку' }).click()

    await expect(page.getByText('Заявка отправлена')).toBeVisible()
    expect(payload).toMatchObject({ budget: 150000, utm_source: 'yandex', utm_campaign: 'autumn', consent: true })
    await expectNoHorizontalOverflow(page)
  })

  test('поле ввода не мельче 16px — iOS не увеличивает страницу при фокусе', async ({ page }) => {
    await page.goto('/')
    const sizes = await page.locator('#order input, #order select, #order textarea').evaluateAll((els) =>
      els
        .filter((el) => (el as HTMLElement).offsetParent !== null && (el as HTMLInputElement).type !== 'checkbox')
        .map((el) => parseFloat(getComputedStyle(el).fontSize)),
    )
    expect(sizes.length).toBeGreaterThan(0)
    for (const size of sizes) expect(size).toBeGreaterThanOrEqual(16)
  })
})
