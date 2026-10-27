import { useEffect, useState } from 'react'

import type { ServiceType } from '@/api/types'
import { OrderForm } from '@/components/OrderForm'
import { services } from '@/data/services'
import { captureAttribution } from '@/lib/attribution'
import { formatMoney } from '@/lib/labels'

import { SiteFooter, SiteHeader } from './SiteChrome'

const steps = [
  { title: 'Заявка', text: 'Вы описываете задачу в форме — без технических терминов.' },
  { title: 'Обсуждение', text: 'Созваниваемся, уточняем цели, сроки и бюджет.' },
  { title: 'Техзадание', text: 'Фиксируем функции, этапы и стоимость в договоре.' },
  { title: 'Разработка', text: 'Показываем результат каждые 1–2 недели, вы вносите правки.' },
  { title: 'Запуск', text: 'Публикуем, обучаем команду и сопровождаем после старта.' },
]

function prefersReducedMotion(): boolean {
  return typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function goToForm() {
  const target = document.getElementById('order')
  if (!target) return
  try {
    target.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'start' })
  } catch {
    // Очень старые браузеры не принимают объект настроек
    target.scrollIntoView(true)
  }
  window.setTimeout(() => {
    const field = document.getElementById('name')
    try {
      field?.focus({ preventScroll: true })
    } catch {
      field?.focus()
    }
  }, 500)
}

function Estimator({ onPick }: { onPick: (type: ServiceType) => void }) {
  const [active, setActive] = useState<ServiceType>('website')
  const service = services.find((s) => s.type === active) ?? services[0]

  return (
    <div className="min-w-0 rounded-xl bg-ink p-4 text-white shadow-[0_24px_60px_-30px_rgba(21,32,43,0.7)] xs:p-5 sm:p-7">
      <p id="estimator-label" className="text-[15px] text-white/70">
        Что вам нужно?
      </p>
      <div className="mt-3 grid grid-cols-2 gap-2" role="radiogroup" aria-labelledby="estimator-label">
        {services.map((s) => (
          <button
            key={s.type}
            type="button"
            role="radio"
            aria-checked={s.type === active}
            onClick={() => setActive(s.type)}
            className={`min-h-[44px] rounded-md border px-2.5 py-2 text-left text-[14px] font-semibold transition-colors xs:px-3 xs:text-[15px] ${
              s.type === active
                ? 'border-marker bg-marker text-ink'
                : 'border-white/20 text-white hover:border-white/50'
            }`}
          >
            {s.title}
          </button>
        ))}
      </div>

      <dl className="mt-6 grid grid-cols-1 gap-4 border-t border-white/15 pt-5 xs:grid-cols-2">
        <div className="min-w-0">
          <dt className="text-[14px] text-white/60">Срок</dt>
          <dd className="mt-1 font-display text-[clamp(1.125rem,5vw,1.375rem)] font-bold leading-tight">
            {service.term}
          </dd>
        </div>
        <div className="min-w-0">
          <dt className="text-[14px] text-white/60">Стоимость</dt>
          <dd className="mt-1 font-display text-[clamp(1.125rem,5vw,1.375rem)] font-bold leading-tight">
            от&nbsp;{formatMoney(service.priceFrom)}
          </dd>
        </div>
      </dl>
      <ul className="mt-5 space-y-1.5 text-[15px] text-white/85">
        {service.includes.map((item) => (
          <li key={item} className="flex">
            <span aria-hidden className="mr-2 text-marker">
              +
            </span>
            {item}
          </li>
        ))}
      </ul>
      <button
        type="button"
        className="btn mt-6 w-full bg-white py-3 text-ink hover:bg-marker"
        onClick={() => {
          onPick(active)
          goToForm()
        }}
      >
        Обсудить {service.title.toLowerCase()}
      </button>
    </div>
  )
}

export default function HomePage() {
  const [selected, setSelected] = useState<ServiceType | null>(null)

  useEffect(() => {
    captureAttribution()
    if (window.location.hash === '#order') {
      window.setTimeout(() => document.getElementById('order')?.scrollIntoView(), 50)
    }
  }, [])

  return (
    <>
      <SiteHeader onOrder={goToForm} />
      <main>
        <section className="page grid items-center gap-8 pb-14 pt-8 sm:gap-10 sm:pt-10 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] lg:gap-14 lg:pb-24 lg:pt-16 xl:gap-16">
          <div className="min-w-0">
            <h1 className="max-w-[16ch] hyphens-auto text-[clamp(1.75rem,7vw,3.625rem)] font-bold leading-[1.1]">
              Делаем сайты, ботов, CRM и приложения под ваш процесс
            </h1>
            <p className="mt-5 max-w-[52ch] text-[17px] text-muted sm:mt-6 sm:text-[19px]">
              Не продаём шаблоны. Сначала разбираемся, как работает ваш бизнес, потом пишем код, который
              экономит время сотрудникам и приводит клиентов.
            </p>
            <div className="mt-7 flex flex-col gap-3 xs:flex-row xs:flex-wrap sm:mt-8">
              <button type="button" className="btn-primary px-6 py-3 text-[16px]" onClick={goToForm}>
                Заказать проект
              </button>
              <a href="#services" className="btn-ghost px-6 py-3 text-[16px]">
                Посмотреть услуги
              </a>
            </div>
          </div>
          <Estimator onPick={setSelected} />
        </section>

        <section id="services" className="scroll-mt-16 border-y border-line bg-white py-14 lg:py-20">
          <div className="page">
            <h2 className="text-[clamp(1.5rem,5vw,2.125rem)] font-bold">Услуги</h2>
            <p className="mt-3 max-w-[60ch] text-muted">
              Цены — нижняя граница для типового проекта. Точную стоимость считаем после обсуждения задачи.
            </p>

            <div className="mt-8 divide-y divide-line border-y border-line lg:mt-10">
              {services.map((s) => (
                <article
                  key={s.type}
                  className="grid gap-3 py-6 sm:gap-4 lg:grid-cols-[10rem_minmax(0,1fr)_auto] lg:items-center lg:gap-8 lg:py-7 xl:grid-cols-[12rem_minmax(0,1fr)_auto]"
                >
                  <h3 className="text-[20px] font-bold sm:text-[22px]">{s.title}</h3>
                  <div className="min-w-0">
                    <p>{s.summary}</p>
                    <p className="mt-1.5 text-[15px] text-muted">{s.includes.join(', ')}</p>
                  </div>
                  {/* Телефон: срок и цена в строку, кнопка на всю ширину. Десктоп: колонки таблицы */}
                  <div className="grid grid-cols-2 items-end gap-x-6 gap-y-3 sm:flex sm:flex-wrap sm:items-center lg:flex-nowrap lg:justify-end">
                    <p className="text-[15px] lg:w-32">
                      <span className="block text-[14px] text-muted">Срок</span>
                      {s.term}
                    </p>
                    <p className="font-semibold lg:w-36">
                      <span className="block text-[14px] font-normal text-muted">Стоимость</span>
                      от&nbsp;{formatMoney(s.priceFrom)}
                    </p>
                    <button
                      type="button"
                      className="btn-ghost col-span-2 w-full sm:col-span-1 sm:ml-auto sm:w-auto lg:ml-0"
                      onClick={() => {
                        setSelected(s.type)
                        goToForm()
                      }}
                    >
                      Выбрать
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="process" className="page scroll-mt-16 py-14 lg:py-20">
          <h2 className="text-[clamp(1.5rem,5vw,2.125rem)] font-bold">Как мы работаем</h2>
          <ol className="mt-8 grid gap-6 sm:grid-cols-2 sm:gap-8 lg:mt-10 lg:grid-cols-3 xl:grid-cols-5 xl:gap-6">
            {steps.map((step, i) => (
              <li key={step.title} className="border-t-2 border-ink pt-4">
                <span className="font-display text-[15px] font-bold text-cobalt">{i + 1}</span>
                <h3 className="mt-1 text-[18px] font-bold">{step.title}</h3>
                <p className="mt-2 text-[15px] text-muted">{step.text}</p>
              </li>
            ))}
          </ol>
        </section>

        <section id="order" className="scroll-mt-16 border-t border-line bg-cobalt-tint/60 py-14 lg:py-20">
          <div className="page grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)] lg:gap-16">
            <div className="min-w-0">
              <h2 className="text-[clamp(1.5rem,5vw,2.125rem)] font-bold">Расскажите о задаче</h2>
              <p className="mt-4 max-w-[46ch] text-muted">
                Чем подробнее описание, тем точнее будет первая оценка. После отправки менеджер ответит на
                почту в течение рабочего дня.
              </p>
              <ul className="mt-6 space-y-3 text-[16px] lg:mt-8 lg:space-y-4">
                <li className="border-l-2 border-marker pl-4">Оценка сроков и стоимости — бесплатно</li>
                <li className="border-l-2 border-marker pl-4">Договор и поэтапная оплата</li>
                <li className="border-l-2 border-marker pl-4">Код и доступы передаём вам</li>
              </ul>
            </div>
            <div className="min-w-0">
              <OrderForm selectedService={selected} />
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  )
}
