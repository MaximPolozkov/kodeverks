export type UserRole = 'admin' | 'manager'
export type ServiceType = 'website' | 'bot' | 'crm' | 'app'
export type OrderStatus = 'new' | 'in_progress' | 'negotiation' | 'done' | 'rejected'
export type OrderSource = 'site' | 'bot' | 'utm'
export type LeadSource = 'vk' | 'telegram' | 'web'
export type ContactChannel = 'email' | 'telegram' | 'vk' | 'whatsapp' | 'phone'
export type LeadStatus =
  | 'found'
  | 'contacted'
  | 'replied'
  | 'qualified'
  | 'converted'
  | 'lost'
  | 'opted_out'

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface User {
  id: number
  email: string
  name: string
  phone: string | null
  avatar_url: string | null
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface OrderListItem {
  id: number
  name: string
  email: string
  budget: string
  service_type: ServiceType | null
  source: OrderSource
  utm_source: string | null
  contact_channel: ContactChannel
  contact_value: string | null
  status: OrderStatus
  created_at: string
}

export interface OrderComment {
  id: number
  text: string
  author_id: number | null
  author_name: string | null
  created_at: string
}

export interface OrderHistory {
  id: number
  old_status: OrderStatus | null
  new_status: OrderStatus
  changed_by: number | null
  author_name: string | null
  changed_at: string
}

export interface OrderDetail extends OrderListItem {
  description: string
  utm_medium: string | null
  utm_campaign: string | null
  utm_content: string | null
  utm_term: string | null
  lead_id: number | null
  vk_notified_at: string | null
  contact_link: string | null
  updated_at: string
  comments: OrderComment[]
  history: OrderHistory[]
}

export interface OrderCreatePayload {
  name: string
  email: string
  budget: number
  description: string
  service_type?: ServiceType | null
  contact_channel: ContactChannel
  contact_value?: string
  consent: true
  website?: string
  ref?: string
  lead_id?: string
  utm_source?: string
  utm_medium?: string
  utm_campaign?: string
  utm_content?: string
  utm_term?: string
}

export interface SourceLimits {
  enabled: boolean
  per_hour: number
  per_day: number
}

export interface BotSettingsData {
  keywords: string[]
  stop_words: string[]
  sources: Record<LeadSource, SourceLimits>
  web_sites: string[]
  min_score: number
  auto_contact: boolean
  schedule_minutes: number
  search_limit: number
  first_message_template: string
  system_prompt: string
  retention_days: number
}

export interface BotSettings {
  enabled: boolean
  data: BotSettingsData
  updated_at: string | null
}

export interface BotRun {
  id: number
  started_at: string
  finished_at: string | null
  found_count: number
  contacted_count: number
  errors: number
  log: { at: string; level: 'info' | 'error'; text: string }[]
}

export interface BotStatus {
  enabled: boolean
  running: boolean
  worker_available: boolean
  last_run: BotRun | null
  sources_configured: Record<LeadSource, boolean>
  llm_configured: boolean
}

export interface Lead {
  id: number
  source: LeadSource
  external_id: string
  author_name: string | null
  profile_url: string | null
  post_url: string | null
  request_text: string
  relevance_score: number
  service_guess: ServiceType | null
  status: LeadStatus
  can_contact: boolean
  manual_mode: boolean
  link_sent_at: string | null
  created_at: string
}

export interface BotMessage {
  id: number
  direction: 'in' | 'out'
  text: string
  is_manual: boolean
  created_at: string
}

export interface FunnelStats {
  found: number
  contacted: number
  replied: number
  link_sent: number
  converted: number
  opted_out: number
  by_source: Record<string, number>
}
