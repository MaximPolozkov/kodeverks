import type { ContactChannel, LeadSource, LeadStatus, OrderSource, OrderStatus, ServiceType, UserRole } from '@/api/types'

export const serviceLabels: Record<ServiceType, string> = {
  website: 'Сайт',
  bot: 'Бот',
  crm: 'CRM-система',
  app: 'Приложение',
}

export const orderStatusLabels: Record<OrderStatus, string> = {
  new: 'Новый',
  in_progress: 'В работе',
  negotiation: 'Переговоры',
  done: 'Выполнен',
  rejected: 'Отклонён',
}

export const orderStatusTone: Record<OrderStatus, string> = {
  new: 'bg-marker-tint text-ink border-marker',
  in_progress: 'bg-cobalt-tint text-cobalt-dark border-cobalt/30',
  negotiation: 'bg-white text-ink border-ink/30',
  done: 'bg-ok/10 text-ok border-ok/30',
  rejected: 'bg-paper text-muted border-line',
}

export const contactChannels: Record<
  ContactChannel,
  { label: string; field: string; placeholder: string; inputMode: 'email' | 'tel' | 'text'; hint: string }
> = {
  email: { label: 'E-mail', field: 'Другая почта (необязательно)', placeholder: 'Оставьте пустым, если та же', inputMode: 'email', hint: 'Ответим на почту, указанную выше' },
  telegram: { label: 'Telegram', field: 'Ник или телефон в Telegram', placeholder: '@ivan_petrov', inputMode: 'text', hint: 'Напишем вам в Telegram' },
  vk: { label: 'ВКонтакте', field: 'Ссылка на страницу ВКонтакте', placeholder: 'vk.com/ivan_petrov', inputMode: 'text', hint: 'Напишем вам в личные сообщения VK' },
  whatsapp: { label: 'WhatsApp', field: 'Номер WhatsApp', placeholder: '+7 912 345-67-89', inputMode: 'tel', hint: 'Напишем вам в WhatsApp' },
  phone: { label: 'Звонок', field: 'Номер телефона', placeholder: '+7 912 345-67-89', inputMode: 'tel', hint: 'Перезвоним в рабочее время' },
}

export const orderSourceLabels: Record<OrderSource, string> = {
  site: 'Сайт',
  bot: 'Бот',
  utm: 'Реклама (UTM)',
}

export const leadSourceLabels: Record<LeadSource, string> = {
  vk: 'ВКонтакте',
  telegram: 'Telegram',
  web: 'Поиск по сайтам',
  freelance: 'Биржи фриланса',
}

export const leadStatusLabels: Record<LeadStatus, string> = {
  found: 'Найден',
  contacted: 'Написали',
  replied: 'Ответил',
  qualified: 'Получил ссылку',
  converted: 'Оформил заказ',
  lost: 'Потерян',
  opted_out: 'Отказался',
}

export const leadStatusTone: Record<LeadStatus, string> = {
  found: 'bg-white text-ink border-line',
  contacted: 'bg-cobalt-tint text-cobalt-dark border-cobalt/30',
  replied: 'bg-marker-tint text-ink border-marker',
  qualified: 'bg-marker-tint text-ink border-marker',
  converted: 'bg-ok/10 text-ok border-ok/30',
  lost: 'bg-paper text-muted border-line',
  opted_out: 'bg-danger/5 text-danger border-danger/30',
}

export const roleLabels: Record<UserRole, string> = {
  admin: 'Администратор',
  manager: 'Менеджер',
}

const money = new Intl.NumberFormat('ru-RU', {
  style: 'currency',
  currency: 'RUB',
  maximumFractionDigits: 0,
})
export const formatMoney = (value: string | number) => money.format(Number(value))

const dateTime = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})
export const formatDateTime = (value: string) => dateTime.format(new Date(value))
