import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

const NAV = [
  { href: '/#services', label: 'Услуги' },
  { href: '/#process', label: 'Как работаем' },
  { href: '/#order', label: 'Заявка' },
]

export function Logo({ light = false }: { light?: boolean }) {
  return (
    <Link to="/" className="flex shrink-0 items-center gap-2.5" aria-label="На главную">
      <img src="/favicon.svg" alt="" width={32} height={32} className="h-8 w-8" />
      <span
        className={`font-display text-[16px] font-bold max-[359px]:sr-only sm:text-[17px] ${light ? 'text-white' : 'text-ink'}`}
      >
        Кодверк
      </span>
    </Link>
  )
}

export function SiteHeader({ onOrder }: { onOrder?: () => void }) {
  const [open, setOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const toggleRef = useRef<HTMLButtonElement>(null)

  // Закрываем меню по Escape и при переходе на десктопную ширину
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false)
        toggleRef.current?.focus()
      }
    }
    const mq = window.matchMedia('(min-width: 768px)')
    const onChange = () => mq.matches && setOpen(false)
    document.addEventListener('keydown', onKey)
    // Safari < 14 поддерживает только addListener
    if (mq.addEventListener) mq.addEventListener('change', onChange)
    else mq.addListener(onChange)
    return () => {
      document.removeEventListener('keydown', onKey)
      if (mq.removeEventListener) mq.removeEventListener('change', onChange)
      else mq.removeListener(onChange)
    }
  }, [open])

  return (
    <header
      className="sticky top-0 z-30 border-b border-line/70 bg-paper/95 supports-[backdrop-filter]:bg-paper/80 supports-[backdrop-filter]:backdrop-blur"
      style={{ paddingTop: 'env(safe-area-inset-top)' }}
    >
      <div className="page flex h-16 items-center justify-between gap-3">
        <Logo />
        <nav className="hidden items-center gap-7 text-[15px] font-medium md:flex" aria-label="Основное меню">
          {NAV.map((item) => (
            <a key={item.href} href={item.href} className="py-2 hover:text-cobalt">
              {item.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          {onOrder ? (
            <button className="btn-ink px-3 xs:px-4" onClick={onOrder}>
              Заказать
            </button>
          ) : (
            <a href="/#order" className="btn-ink px-3 xs:px-4">
              Заказать
            </a>
          )}
          <button
            ref={toggleRef}
            type="button"
            className="btn-ghost w-11 px-0 md:hidden"
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label={open ? 'Закрыть меню' : 'Открыть меню'}
            onClick={() => setOpen((v) => !v)}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
              {open ? (
                <path d="M4 4l12 12M16 4L4 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              ) : (
                <path d="M3 6h14M3 10h14M3 14h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              )}
            </svg>
          </button>
        </div>
      </div>
      <div
        id="mobile-menu"
        ref={menuRef}
        hidden={!open}
        className="border-t border-line bg-paper md:hidden"
      >
        <nav className="page py-2" aria-label="Мобильное меню">
          <ul>
            {NAV.map((item) => (
              <li key={item.href}>
                <a
                  href={item.href}
                  className="flex min-h-[48px] items-center border-b border-line/60 text-[17px] font-semibold last:border-b-0"
                  onClick={() => setOpen(false)}
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </header>
  )
}

export function SiteFooter() {
  return (
    <footer className="bg-ink pt-12 text-white" style={{ paddingBottom: 'max(3rem, env(safe-area-inset-bottom))' }}>
      <div className="page grid gap-8 sm:grid-cols-2 md:grid-cols-[1.4fr_1fr_1fr]">
        <div className="sm:col-span-2 md:col-span-1">
          <Logo light />
          <p className="mt-4 max-w-[38ch] text-[15px] text-white/70">
            Студия разработки: сайты, боты, CRM-системы и приложения для малого и среднего бизнеса.
          </p>
        </div>
        <div className="text-[15px]">
          <p className="font-semibold">Контакты</p>
          <ul className="mt-3 space-y-2 text-white/80">
            <li>
              <a href="mailto:hello@example.com" className="break-anywhere inline-block py-1 hover:text-marker">
                hello@example.com
              </a>
            </li>
            <li>
              <a href="tel:+70000000000" className="inline-block py-1 hover:text-marker">
                +7 (000) 000-00-00
              </a>
            </li>
          </ul>
        </div>
        <div className="text-[15px]">
          <p className="font-semibold">Мы в соцсетях</p>
          <ul className="mt-3 space-y-2 text-white/80">
            <li>
              <a href="https://t.me/" className="inline-block py-1 hover:text-marker" target="_blank" rel="noopener noreferrer">
                Telegram
              </a>
            </li>
            <li>
              <a href="https://vk.com/" className="inline-block py-1 hover:text-marker" target="_blank" rel="noopener noreferrer">
                ВКонтакте
              </a>
            </li>
          </ul>
        </div>
      </div>
      <div className="page mt-10 flex flex-col gap-3 border-t border-white/15 pt-6 text-[14px] text-white/60 sm:flex-row sm:justify-between">
        <span>© {new Date().getFullYear()} Кодверк</span>
        <Link to="/privacy" className="hover:text-white">
          Политика конфиденциальности
        </Link>
      </div>
    </footer>
  )
}
