import type { ServiceType } from '@/api/types'

export interface Service {
  type: ServiceType
  title: string
  summary: string
  includes: string[]
  term: string
  priceFrom: number
}

export const services: Service[] = [
  {
    type: 'website',
    title: 'Сайты',
    summary: 'Лендинги, корпоративные сайты и интернет-магазины с админкой и оплатой.',
    includes: ['Дизайн под ваш бренд', 'Адаптация под телефоны', 'Оплата и интеграции', 'SEO-основа'],
    term: 'от 2 недель',
    priceFrom: 60000,
  },
  {
    type: 'bot',
    title: 'Боты',
    summary: 'Боты для Telegram, VK и WhatsApp: запись, заказы, поддержка, рассылки по подписке.',
    includes: ['Сценарии диалогов', 'Приём оплат', 'Связь с CRM', 'Панель статистики'],
    term: 'от 1 недели',
    priceFrom: 40000,
  },
  {
    type: 'crm',
    title: 'CRM-системы',
    summary: 'Учёт клиентов, сделок и задач под ваш процесс — без лишних модулей и подписок.',
    includes: ['Воронки и статусы', 'Роли и доступы', 'Отчёты', 'Импорт из таблиц'],
    term: 'от 4 недель',
    priceFrom: 180000,
  },
  {
    type: 'app',
    title: 'Приложения',
    summary: 'Веб- и мобильные приложения для iOS и Android: личные кабинеты, сервисы, маркетплейсы.',
    includes: ['Прототип и дизайн', 'iOS, Android, веб', 'Бэкенд и API', 'Публикация в сторах'],
    term: 'от 6 недель',
    priceFrom: 300000,
  },
]
