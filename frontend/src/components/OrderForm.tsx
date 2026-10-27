import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router-dom'
import { z } from 'zod'

import { api, ApiError } from '@/api/client'
import type { ContactChannel, OrderCreatePayload, ServiceType } from '@/api/types'
import { Field } from '@/components/ui/Field'
import { readAttribution } from '@/lib/attribution'
import { contactChannels, serviceLabels } from '@/lib/labels'

const parseBudget = (value: string) => Number(value.replace(/[\s ₽]/g, '').replace(',', '.'))

const phoneDigits = (v: string) => v.replace(/\D/g, '')

export const orderSchema = z
  .object({
  name: z
    .string()
    .trim()
    .min(2, 'Укажите имя — минимум 2 символа')
    .max(100, 'Имя длиннее 100 символов'),
  email: z.string().trim().email('Укажите почту в формате name@example.com'),
  budget: z
    .string()
    .trim()
    .min(1, 'Укажите примерный бюджет')
    .refine((v) => Number.isFinite(parseBudget(v)) && parseBudget(v) > 0, 'Бюджет должен быть числом больше нуля')
    .refine((v) => parseBudget(v) < 10_000_000_000, 'Слишком большая сумма'),
  description: z
    .string()
    .trim()
    .min(20, 'Опишите задачу подробнее — минимум 20 символов')
    .max(5000, 'Описание длиннее 5000 символов'),
  service_type: z.enum(['', 'website', 'bot', 'crm', 'app']),
  contact_channel: z.enum(['email', 'telegram', 'vk', 'whatsapp', 'phone']),
  contact_value: z.string().trim().max(200, 'Слишком длинное значение'),
  consent: z.boolean().refine((v) => v, 'Без согласия мы не сможем обработать заявку'),
  website: z.string().optional(),
})
  .superRefine((v, ctx) => {
    const value = v.contact_value
    const fail = (message: string) => ctx.addIssue({ code: 'custom', path: ['contact_value'], message })
    switch (v.contact_channel) {
      case 'email':
        if (value && !z.string().email().safeParse(value).success) fail('Укажите почту в формате name@example.com')
        break
      case 'telegram':
        if (!value) fail('Укажите ник в Telegram или номер телефона')
        else if (!/^(https?:\/\/)?(t\.me\/)?@?[A-Za-z][A-Za-z0-9_]{4,31}\/?$/.test(value) && phoneDigits(value).length < 10)
          fail('Укажите ник в Telegram (например, @ivan_petrov) или номер телефона')
        break
      case 'vk':
        if (!value) fail('Укажите ссылку на страницу ВКонтакте')
        else if (!/^(https?:\/\/)?((m\.)?vk\.(com|ru)\/)?@?[A-Za-z0-9_.]{3,64}\/?$/.test(value))
          fail('Укажите ссылку на страницу ВКонтакте, например vk.com/ivan_petrov')
        break
      default:
        if (phoneDigits(value).length < 10 || phoneDigits(value).length > 15)
          fail('Укажите номер телефона, например +7 912 345-67-89')
    }
  })

export type OrderFormValues = z.infer<typeof orderSchema>

const emptyValues: OrderFormValues = {
  name: '',
  email: '',
  budget: '',
  description: '',
  service_type: '',
  contact_channel: 'email',
  contact_value: '',
  consent: false,
  website: '',
}

export function OrderForm({ selectedService }: { selectedService?: ServiceType | null }) {
  const [sent, setSent] = useState(false)
  const {
    register,
    handleSubmit,
    setValue,
    setError,
    reset,
    watch,
    formState: { errors },
  } = useForm<OrderFormValues>({ resolver: zodResolver(orderSchema), defaultValues: emptyValues })

  useEffect(() => {
    if (selectedService) setValue('service_type', selectedService)
  }, [selectedService, setValue])

  const mutation = useMutation({
    mutationFn: (payload: OrderCreatePayload) =>
      api<{ ok: boolean; detail: string }>('/api/orders', { method: 'POST', json: payload }),
    onSuccess: () => {
      setSent(true)
      reset(emptyValues)
    },
    onError: (error) => {
      if (error instanceof ApiError) {
        for (const e of error.errors) {
          if (e.field in emptyValues) {
            setError(e.field as keyof OrderFormValues, { message: e.message })
          }
        }
      }
    },
  })

  const onSubmit = (values: OrderFormValues) => {
    mutation.mutate({
      ...readAttribution(),
      name: values.name,
      email: values.email,
      budget: parseBudget(values.budget),
      description: values.description,
      service_type: values.service_type || null,
      contact_channel: values.contact_channel,
      contact_value: values.contact_value || undefined,
      consent: true,
      website: values.website,
    })
  }

  if (sent) {
    return (
      <div className="panel p-5 sm:p-8" role="status">
        <h3 className="text-[22px] font-bold">Заявка отправлена</h3>
        <p className="mt-3 max-w-prose text-muted">
          Менеджер прочитает описание и ответит на почту в течение рабочего дня. Если понадобится,
          уточним детали и предложим созвон.
        </p>
        <button className="btn-ghost mt-6" onClick={() => setSent(false)}>
          Отправить ещё одну заявку
        </button>
      </div>
    )
  }

  const descriptionLength = watch('description')?.length ?? 0
  const channel = (watch('contact_channel') ?? 'email') as ContactChannel
  const channelInfo = contactChannels[channel]
  const invalid = (name: keyof OrderFormValues) => (errors[name] ? 'input input-error' : 'input')
  const describedBy = (name: keyof OrderFormValues) => (errors[name] ? `${name}-error` : undefined)

  return (
    <form className="panel relative space-y-5 p-4 xs:p-5 sm:p-8" onSubmit={handleSubmit(onSubmit)} noValidate>
      <div className="grid gap-5 sm:grid-cols-2">
        <Field id="name" label="Имя" error={errors.name?.message}>
          <input
            id="name"
            className={invalid('name')}
            autoComplete="name"
            aria-invalid={!!errors.name}
            aria-describedby={describedBy('name')}
            {...register('name')}
          />
        </Field>
        <Field id="email" label="Почта" error={errors.email?.message}>
          <input
            id="email"
            type="email"
            inputMode="email"
            className={invalid('email')}
            autoComplete="email"
            aria-invalid={!!errors.email}
            aria-describedby={describedBy('email')}
            {...register('email')}
          />
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field
          id="budget"
          label="Предполагаемый бюджет, ₽"
          error={errors.budget?.message}
          hint="Можно примерно — уточним при обсуждении"
        >
          <input
            id="budget"
            inputMode="decimal"
            placeholder="150 000"
            className={invalid('budget')}
            aria-invalid={!!errors.budget}
            aria-describedby={errors.budget ? 'budget-error' : 'budget-hint'}
            {...register('budget')}
          />
        </Field>
        <Field id="service_type" label="Что нужно сделать">
          <select id="service_type" className="input" {...register('service_type')}>
            <option value="">Пока не знаю</option>
            {(Object.keys(serviceLabels) as ServiceType[]).map((key) => (
              <option key={key} value={key}>
                {serviceLabels[key]}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <fieldset className="min-w-0">
        <legend className="label">Где вам удобно получить ответ</legend>
        <div className="grid grid-cols-2 gap-2 xs:grid-cols-3 sm:grid-cols-5">
          {(Object.keys(contactChannels) as ContactChannel[]).map((key) => (
            <label
              key={key}
              className={`flex min-h-[44px] cursor-pointer items-center justify-center rounded-md border px-2 text-center text-[15px] font-semibold transition-colors focus-within:ring-2 focus-within:ring-marker ${
                channel === key ? 'border-cobalt bg-cobalt-tint text-cobalt-dark' : 'border-line bg-white hover:border-ink/40'
              }`}
            >
              <input
                type="radio"
                value={key}
                className="sr-only"
                {...register('contact_channel', { onChange: () => setValue('contact_value', '') })}
              />
              {contactChannels[key].label}
            </label>
          ))}
        </div>
      </fieldset>

      <Field
        id="contact_value"
        label={channelInfo.field}
        error={errors.contact_value?.message}
        hint={channelInfo.hint}
      >
        <input
          id="contact_value"
          inputMode={channelInfo.inputMode}
          autoComplete={channel === 'phone' || channel === 'whatsapp' ? 'tel' : 'off'}
          placeholder={channelInfo.placeholder}
          className={invalid('contact_value')}
          aria-invalid={!!errors.contact_value}
          aria-describedby={errors.contact_value ? 'contact_value-error' : 'contact_value-hint'}
          {...register('contact_value')}
        />
      </Field>

      <Field
        id="description"
        label="Подробное описание задачи"
        error={errors.description?.message}
        hint={`Что должно получиться, для кого, какие есть примеры и сроки. ${descriptionLength}/5000`}
      >
        <textarea
          id="description"
          rows={6}
          className={invalid('description')}
          aria-invalid={!!errors.description}
          aria-describedby={errors.description ? 'description-error' : 'description-hint'}
          {...register('description')}
        />
      </Field>

      {/* Honeypot: скрыто от людей и скринридеров */}
      <div aria-hidden="true" className="absolute left-[-10000px] h-px w-px overflow-hidden">
        <label htmlFor="website">Сайт</label>
        <input id="website" tabIndex={-1} autoComplete="off" {...register('website')} />
      </div>

      <div>
        <label className="flex items-start gap-3 text-[15px]">
          <input
            type="checkbox"
            className="mt-1 h-5 w-5 shrink-0 accent-cobalt"
            aria-invalid={!!errors.consent}
            aria-describedby={describedBy('consent')}
            {...register('consent')}
          />
          <span>
            Согласен на обработку персональных данных в соответствии с{' '}
            <Link to="/privacy" className="text-cobalt underline underline-offset-2">
              политикой конфиденциальности
            </Link>
          </span>
        </label>
        {errors.consent && (
          <p id="consent-error" role="alert" className="mt-1.5 text-[14px] text-danger">
            {errors.consent.message}
          </p>
        )}
      </div>

      {mutation.isError && !(mutation.error instanceof ApiError && mutation.error.errors.length) && (
        <p role="alert" className="rounded-md bg-danger/5 px-4 py-3 text-danger">
          {mutation.error.message}
        </p>
      )}

      <button type="submit" className="btn-primary w-full py-3 text-[16px] sm:w-auto" disabled={mutation.isPending}>
        {mutation.isPending ? 'Отправляем…' : 'Отправить заявку'}
      </button>
    </form>
  )
}
