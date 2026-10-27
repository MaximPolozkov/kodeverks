import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { api } from '@/api/client'
import { roleLabels } from '@/lib/labels'
import { Logo } from '@/pages/public/SiteChrome'

import { useLogout, useMe } from './auth'

export default function AdminLayout() {
  const { data: me } = useMe()
  const logout = useLogout()
  const navigate = useNavigate()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  // Меню на телефоне закрывается при переходе в другой раздел
  useEffect(() => setMenuOpen(false), [location.pathname])

  const newCount = useQuery({
    queryKey: ['orders', 'new-count'],
    queryFn: () => api<{ count: number }>('/api/admin/orders/new-count'),
    refetchInterval: 60_000,
  })

  const links = [
    { to: '/admin/orders', label: 'Заказы', badge: newCount.data?.count },
    { to: '/admin/profile', label: 'Профиль' },
    { to: '/admin/bot', label: 'Бот' },
    ...(me?.role === 'admin' ? [{ to: '/admin/users', label: 'Пользователи' }] : []),
  ]

  return (
    <div className="min-h-screen-safe lg:grid lg:grid-cols-[15rem_minmax(0,1fr)]">
      <aside
        className="sticky top-0 z-30 border-b border-line bg-white lg:h-screen-safe lg:border-b-0 lg:border-r"
        style={{ paddingTop: 'env(safe-area-inset-top)' }}
      >
        <div className="flex h-full flex-col">
          <div className="flex h-16 shrink-0 items-center justify-between gap-3 px-4 lg:px-5">
            <Logo />
            <button
              type="button"
              className="btn-ghost lg:hidden"
              aria-expanded={menuOpen}
              aria-controls="admin-nav"
              onClick={() => setMenuOpen((v) => !v)}
            >
              {menuOpen ? 'Закрыть' : 'Меню'}
              {!menuOpen && !!newCount.data?.count && (
                <span className="rounded bg-marker px-1.5 text-[13px] text-ink">{newCount.data.count}</span>
              )}
            </button>
          </div>
          <nav
            id="admin-nav"
            aria-label="Разделы панели"
            className={`${menuOpen ? 'flex' : 'hidden'} min-h-0 flex-1 flex-col overflow-y-auto px-3 pb-4 lg:flex`}
          >
            <ul className="space-y-1">
              {links.map((link) => (
                <li key={link.to}>
                  <NavLink
                    to={link.to}
                    className={({ isActive }) =>
                      `flex min-h-[44px] items-center justify-between rounded-md border-l-[3px] px-3 py-2 text-[15px] font-semibold ${
                        isActive
                          ? 'border-cobalt bg-cobalt-tint text-cobalt-dark'
                          : 'border-transparent text-ink hover:bg-paper'
                      }`
                    }
                  >
                    {link.label}
                    {!!link.badge && (
                      <span className="rounded bg-marker px-1.5 text-[13px] text-ink" aria-label={`новых: ${link.badge}`}>
                        {link.badge}
                      </span>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
            {me && (
              <div className="mt-6 border-t border-line px-3 pt-4 text-[14px] lg:mt-auto">
                <p className="break-anywhere font-semibold">{me.name}</p>
                <p className="text-muted">{roleLabels[me.role]}</p>
                <button
                  type="button"
                  className="mt-2 min-h-[44px] text-cobalt underline underline-offset-2"
                  onClick={async () => {
                    await logout()
                    navigate('/admin/login', { replace: true })
                  }}
                >
                  Выйти
                </button>
              </div>
            )}
          </nav>
        </div>
      </aside>
      <main
        className="min-w-0 py-5 sm:py-6 lg:py-8"
        style={{
          paddingLeft: 'max(1rem, env(safe-area-inset-left))',
          paddingRight: 'max(1rem, env(safe-area-inset-right))',
          paddingBottom: 'max(1.5rem, env(safe-area-inset-bottom))',
        }}
      >
        <div className="mx-auto max-w-[90rem] sm:px-2 lg:px-4">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
