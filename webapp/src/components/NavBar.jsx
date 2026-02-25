import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useTelegram } from '../hooks/useTelegram'

const tabs = [
  {
    path: '/',
    labelKey: 'nav.home',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z" />
        <path d="M9 21V12h6v9" />
      </svg>
    ),
  },
  {
    path: '/technical',
    labelKey: 'nav.analysis',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 3v18h18" />
        <path d="M7 16l4-6 4 4 5-8" />
      </svg>
    ),
  },
  {
    path: '/signals',
    labelKey: 'nav.trade',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
      </svg>
    ),
  },
  {
    path: '/calendar-full',
    labelKey: 'nav.calendar',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
        <line x1="16" y1="2" x2="16" y2="6" />
        <line x1="8" y1="2" x2="8" y2="6" />
        <line x1="3" y1="10" x2="21" y2="10" />
      </svg>
    ),
  },
  {
    path: '/more',
    labelKey: 'nav.more',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <line x1="3" y1="6" x2="21" y2="6" />
        <line x1="3" y1="12" x2="21" y2="12" />
        <line x1="3" y1="18" x2="21" y2="18" />
      </svg>
    ),
  },
]

export default function NavBar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { hapticFeedback } = useTelegram()
  const { t } = useTranslation()

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-bg-secondary/95 backdrop-blur-md border-t border-white/5 flex justify-around items-center h-14 z-50" style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}>
      {tabs.map((tab) => {
        const isActive = tab.path === '/'
          ? location.pathname === '/'
          : location.pathname.startsWith(tab.path)

        return (
          <button
            key={tab.path}
            onClick={() => { hapticFeedback?.selectionChanged(); navigate(tab.path) }}
            className={`flex flex-col items-center gap-0.5 px-4 py-2 transition-all duration-200 ${
              isActive
                ? 'text-accent-goldBright'
                : 'text-accent-goldBright/50 hover:text-accent-goldBright/80 active:scale-90'
            }`}
          >
            <span className={`w-5 h-5 transition-transform duration-200 ${isActive ? 'scale-110' : ''}`}>
              {tab.icon}
            </span>
            <span className="text-[9px] font-medium">{t(tab.labelKey)}</span>
          </button>
        )
      })}
    </nav>
  )
}
