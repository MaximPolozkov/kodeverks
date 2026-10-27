import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { OrderForm, orderSchema } from './OrderForm'

function renderForm() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <OrderForm />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  vi.restoreAllMocks()
  sessionStorage.clear()
})

describe('orderSchema', () => {
  const valid = {
    name: 'Иван',
    email: 'ivan@example.com',
    budget: '150 000',
    description: 'Нужен интернет-магазин с каталогом и онлайн-оплатой',
    service_type: '' as const,
    contact_channel: 'email' as const,
    contact_value: '',
    consent: true,
  }

  it('принимает корректные данные', () => {
    expect(orderSchema.safeParse(valid).success).toBe(true)
  })

  it('требует номер для WhatsApp', () => {
    const bad = orderSchema.safeParse({ ...valid, contact_channel: 'whatsapp', contact_value: 'abc' })
    expect(bad.success).toBe(false)
    const ok = orderSchema.safeParse({ ...valid, contact_channel: 'whatsapp', contact_value: '+7 912 345-67-89' })
    expect(ok.success).toBe(true)
  })

  it('отклоняет нулевой бюджет и короткое описание', () => {
    const result = orderSchema.safeParse({ ...valid, budget: '0', description: 'коротко' })
    expect(result.success).toBe(false)
    if (!result.success) {
      const fields = result.error.issues.map((i) => i.path[0])
      expect(fields).toContain('budget')
      expect(fields).toContain('description')
    }
  })
})

describe('OrderForm', () => {
  it('показывает ошибки при пустой отправке', async () => {
    renderForm()
    await userEvent.click(screen.getByRole('button', { name: 'Отправить заявку' }))
    expect(await screen.findByText('Укажите имя — минимум 2 символа')).toBeInTheDocument()
    expect(screen.getByText('Укажите примерный бюджет')).toBeInTheDocument()
    expect(screen.getByText('Без согласия мы не сможем обработать заявку')).toBeInTheDocument()
  })

  it('отправляет заявку с атрибуцией бота', async () => {
    sessionStorage.setItem('order-attribution', JSON.stringify({ ref: 'bot', lead_id: 'abc' }))
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true, detail: 'ok' }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    renderForm()
    const user = userEvent.setup()
    await user.type(screen.getByLabelText('Имя'), 'Иван')
    await user.type(screen.getByLabelText('Почта'), 'ivan@example.com')
    await user.type(screen.getByLabelText('Предполагаемый бюджет, ₽'), '150 000')
    await user.type(
      screen.getByLabelText('Подробное описание задачи'),
      'Нужен интернет-магазин с каталогом и онлайн-оплатой',
    )
    await user.click(screen.getByLabelText('Telegram'))
    await user.type(screen.getByLabelText('Ник или телефон в Telegram'), '@ivan_petrov')
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: 'Отправить заявку' }))

    expect(await screen.findByText('Заявка отправлена')).toBeInTheDocument()
    const body = JSON.parse(fetchMock.mock.calls[0][1]!.body as string)
    expect(body).toMatchObject({
      budget: 150000,
      ref: 'bot',
      lead_id: 'abc',
      consent: true,
      contact_channel: 'telegram',
      contact_value: '@ivan_petrov',
    })
  })
})
