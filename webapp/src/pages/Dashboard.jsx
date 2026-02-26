import { Component } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useTelegram } from '../hooks/useTelegram'
import { useSubscription } from '../contexts/SubscriptionContext'
import PriceWidget from '../components/PriceWidget'
import PriceChart from '../components/PriceChart'
import PredictionCard from '../components/PredictionCard'
import QuantPredictionCard from '../components/QuantPredictionCard'
import SignalPanel from '../components/SignalPanel'
import NewsCarousel from '../components/NewsCarousel'
import MacroDashboard from '../components/MacroDashboard'
import TickerTape from '../components/TickerTape'
import DataSourceFooter from '../components/DataSourceFooter'
import DailyBriefingCard from '../components/DailyBriefingCard'
import SessionClock from '../components/SessionClock'
import GoldSentimentGauge from '../components/GoldSentimentGauge'
import RealYieldWidget from '../components/RealYieldWidget'
import ETFFlowWidget from '../components/ETFFlowWidget'
import COTChart from '../components/COTChart'
import CentralBankWidget from '../components/CentralBankWidget'
import CorrelationWidget from '../components/CorrelationWidget'
import SilverWidget from '../components/SilverWidget'
import SeasonalityWidget from '../components/SeasonalityWidget'

class SafeWrap extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }
  static getDerivedStateFromError() {
    return { hasError: true }
  }
  componentDidCatch(error, info) {
    console.error(`[${this.props.name}] crashed:`, error, info)
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="bg-bg-card rounded-2xl p-4 border border-accent-red/20">
          <p className="text-accent-red text-xs">{this.props.t('common:widget.failedToLoad', { name: this.props.name })}</p>
          <button
            onClick={() => this.setState({ hasError: false })}
            className="text-accent-gold text-[10px] mt-1 underline"
          >
            {this.props.t('common:app.retry')}
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

const quickIcons = {
  technical: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <path d="M7 16l4-6 4 4 5-8" />
    </svg>
  ),
  signals: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 20v-6" />
      <path d="M12 10V4" />
      <circle cx="12" cy="12" r="2" />
      <path d="M16.24 7.76a6 6 0 010 8.49" />
      <path d="M7.76 16.24a6 6 0 010-8.49" />
      <path d="M19.07 4.93a10 10 0 010 14.14" />
      <path d="M4.93 19.07a10 10 0 010-14.14" />
    </svg>
  ),
  elliott: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 17 7 10 10 14 14 6 17 11 21 4" />
      <path d="M21 4v4h-4" />
    </svg>
  ),
  events: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  ),
  advisor: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
    </svg>
  ),
  history: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <polyline points="12 7 12 12 15.5 14" />
    </svg>
  ),
  news: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 22h16a2 2 0 002-2V4a2 2 0 00-2-2H8a2 2 0 00-2 2v16a2 2 0 01-2 2zm0 0a2 2 0 01-2-2v-9c0-1.1.9-2 2-2h2" />
      <path d="M10 6h8M10 10h8M10 14h4" />
    </svg>
  ),
  settings: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
    </svg>
  ),
  about: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  ),
  premium: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
    </svg>
  ),
  tools: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z" />
    </svg>
  ),
  resources: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
      <path d="M8 7h8M8 11h6" />
    </svg>
  ),
  learn: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
      <path d="M6 12v5c0 1.66 2.69 3 6 3s6-1.34 6-3v-5" />
    </svg>
  ),
  alerts: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 01-3.46 0" />
    </svg>
  ),
  briefing: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  ),
  game: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M8 12h8" />
      <path d="M12 8v8" />
      <path d="M8.5 8.5l7 7" />
    </svg>
  ),
  market: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <path d="M7 16l4-4 4 4 5-5" />
    </svg>
  ),
  quant: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 20Q8 18 12 12t9-9" />
      <path d="M3 20h18" />
      <path d="M3 20V3" />
    </svg>
  ),
  cot: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M3 9h18" />
      <path d="M3 15h18" />
      <path d="M9 3v18" />
      <path d="M15 3v18" />
    </svg>
  ),
  sessions: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M2 12h20" />
      <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
    </svg>
  ),
  etf: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <rect x="7" y="10" width="3" height="8" rx="0.5" />
      <rect x="12" y="6" width="3" height="12" rx="0.5" />
      <rect x="17" y="8" width="3" height="10" rx="0.5" />
    </svg>
  ),
  calendar: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4M8 2v4M3 10h18" />
      <path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01" />
    </svg>
  ),
  journal: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.12 2.12 0 013 3L7 19l-4 1 1-4L16.5 3.5z" />
    </svg>
  ),
  tradingbot: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="10" rx="2" />
      <circle cx="9" cy="16" r="1" fill="currentColor" />
      <circle cx="15" cy="16" r="1" fill="currentColor" />
      <path d="M8 11V7a4 4 0 018 0v4" />
      <path d="M12 3v1" />
      <path d="M9 5l-1-2M15 5l1-2" />
    </svg>
  ),
}

const CATEGORIES = [
  {
    titleKey: 'category.trading',
    links: [
      { path: '/signals', labelKey: 'link.signals', icon: 'signals' },
      { path: '/advisor', labelKey: 'link.advisor', icon: 'advisor' },
      { path: '/trading-bot', labelKey: 'link.tradingBot', icon: 'tradingbot' },
      { path: '/mock-trading', labelKey: 'link.paperTrade', icon: 'advisor' },
      { path: '/alerts', labelKey: 'link.alerts', icon: 'alerts' },
    ],
  },
  {
    titleKey: 'category.analysis',
    links: [
      { path: '/technical', labelKey: 'link.technical', icon: 'technical' },
      { path: '/technical', labelKey: 'link.quantAnalysis', icon: 'quant' },
      { path: '/elliott-wave', labelKey: 'link.elliottWave', icon: 'elliott' },
      { path: '/cot', labelKey: 'link.cotData', icon: 'cot' },
      { path: '/sessions', labelKey: 'link.sessions', icon: 'sessions' },
    ],
  },
  {
    titleKey: 'category.market',
    links: [
      { path: '/markets', labelKey: 'link.markets', icon: 'market' },
      { path: '/gold-etf', labelKey: 'link.goldETF', icon: 'etf' },
      { path: '/calendar', labelKey: 'link.calendar', icon: 'calendar' },
      { path: '/news', labelKey: 'link.news', icon: 'news' },
      { path: '/events', labelKey: 'link.events', icon: 'events' },
      { path: '/history', labelKey: 'link.history', icon: 'history' },
    ],
  },
  {
    titleKey: 'category.more',
    links: [
      { path: '/game', labelKey: 'link.game', icon: 'game' },
      { path: '/briefing', labelKey: 'link.briefing', icon: 'briefing' },
      { path: '/trade-journal', labelKey: 'link.journal', icon: 'journal' },
      { path: '/learn', labelKey: 'link.learn', icon: 'learn' },
      { path: '/resources', labelKey: 'link.resources', icon: 'resources' },
      { path: '/tools', labelKey: 'link.tools', icon: 'tools' },
      { path: '/subscription', labelKey: 'link.premium', icon: 'premium', highlight: true },
      { path: '/settings', labelKey: 'link.settings', icon: 'settings' },
      { path: '/about', labelKey: 'link.about', icon: 'about' },
    ],
  },
]

function QuickAccessGrid() {
  const navigate = useNavigate()
  const { t } = useTranslation('common')
  const { isAdmin } = useSubscription()

  return (
    <div className="space-y-3">
      {CATEGORIES.map((cat) => {
        const links = cat.titleKey === 'category.more' && isAdmin
          ? [...cat.links, { path: '/admin', labelKey: 'link.admin', icon: 'settings' }]
          : cat.links
        return (
          <div key={cat.titleKey}>
            <h3 className="text-accent-goldBright text-[10px] font-semibold uppercase tracking-wider mb-1.5 px-1">{t(cat.titleKey)}</h3>
            <div className="grid grid-cols-4 gap-2">
              {links.map((link) => (
                <button
                  key={link.path}
                  onClick={() => navigate(link.path)}
                  className="bg-bg-card rounded-xl border border-accent-goldBright/10 p-3 flex flex-col items-center gap-1.5 hover:border-accent-goldBright/25 active:scale-95 transition-all"
                >
                  <span className="w-5 h-5 text-accent-goldBright">{quickIcons[link.icon]}</span>
                  <span className="text-[10px] text-accent-goldBright/80 font-medium leading-tight text-center">{t(link.labelKey)}</span>
                </button>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function CouncilCTA() {
  const { t } = useTranslation('common')
  const tg = window.Telegram?.WebApp
  const openCommunity = () => {
    if (tg?.openTelegramLink) {
      tg.openTelegramLink('https://t.me/+-72wnR04tPUyZmIy')
    } else {
      window.open('https://t.me/+-72wnR04tPUyZmIy', '_blank')
    }
  }

  return (
    <button
      onClick={openCommunity}
      className="w-full flex items-center gap-3 bg-bg-card rounded-xl border border-accent-gold/15 p-4 hover:border-accent-gold/30 transition-colors text-left"
    >
      <div className="w-9 h-9 rounded-full bg-accent-gold/10 flex items-center justify-center shrink-0">
        <svg className="w-5 h-5 text-accent-gold" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M22 2L11 13" />
          <path d="M22 2L15 22L11 13L2 9L22 2Z" />
        </svg>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-text-primary text-sm font-medium">{t('paywall.joinCouncil')}</p>
        <p className="text-text-muted text-[10px]">{t('paywall.councilDesc')}</p>
      </div>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4 text-text-muted shrink-0">
        <polyline points="9 18 15 12 9 6" />
      </svg>
    </button>
  )
}

function DashboardPaywallCTA() {
  const navigate = useNavigate()
  const { t } = useTranslation('common')
  const { tier } = useSubscription()
  const hadTrial = tier === 'expired' || tier === 'trial_expired'

  const tg = window.Telegram?.WebApp
  const openCommunity = () => {
    if (tg?.openTelegramLink) {
      tg.openTelegramLink('https://t.me/+-72wnR04tPUyZmIy')
    } else {
      window.open('https://t.me/+-72wnR04tPUyZmIy', '_blank')
    }
  }

  return (
    <div className="space-y-4">
      {hadTrial && (
        <div className="bg-accent-red/10 border border-accent-red/20 rounded-xl px-4 py-2">
          <p className="text-accent-red text-xs font-medium">{t('paywall.trialExpired')}</p>
        </div>
      )}
      <div className="bg-bg-card rounded-2xl border border-accent-gold/20 p-5 text-center">
        <div className="w-12 h-12 rounded-full bg-accent-goldBright/10 flex items-center justify-center mx-auto mb-3">
          <svg className="w-6 h-6 text-accent-goldBright" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0110 0v4" />
          </svg>
        </div>
        <h3 className="text-text-primary text-sm font-bold mb-1">{t('paywall.unlockPrompt')}</h3>
        <ul className="text-text-muted text-xs space-y-1 mb-4 text-left max-w-xs mx-auto">
          {['paywall.features.predictions', 'paywall.features.signals', 'paywall.features.advisor', 'paywall.features.alerts'].map((key) => (
            <li key={key} className="flex items-center gap-2">
              <svg className="w-3 h-3 text-accent-green shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              {t(key)}
            </li>
          ))}
        </ul>
        <button
          onClick={() => navigate('/settings')}
          className="w-full py-2.5 rounded-xl text-sm font-bold text-white bg-accent-gold active:scale-95 transition-all mb-2"
        >
          {hadTrial ? t('paywall.subscribe') : t('paywall.startTrial')}
        </button>
        <button
          onClick={() => navigate('/subscription')}
          className="text-accent-gold text-xs font-medium"
        >
          {t('paywall.viewPlans')}
        </button>
      </div>

      {/* Community CTA */}
      <button
        onClick={openCommunity}
        className="w-full flex items-center gap-3 bg-bg-card rounded-xl border border-accent-gold/15 p-4 hover:border-accent-gold/30 transition-colors text-left"
      >
        <div className="w-9 h-9 rounded-full bg-accent-gold/10 flex items-center justify-center shrink-0">
          <svg className="w-5 h-5 text-accent-gold" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 2L11 13" />
            <path d="M22 2L15 22L11 13L2 9L22 2Z" />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-text-primary text-sm font-medium">{t('paywall.joinCouncil')}</p>
          <p className="text-text-muted text-[10px]">{t('paywall.councilDesc')}</p>
        </div>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4 text-text-muted shrink-0">
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>
    </div>
  )
}

export default function Dashboard() {
  const { t } = useTranslation(['common', 'dashboard'])
  const { isPremium, loading } = useSubscription()

  return (
    <div className="px-4 pt-4 space-y-4 dashboard-stagger">
      <header className="flex items-center justify-between mb-2">
        <h1 className="text-lg font-bold flex items-center gap-2">
          <svg className="w-6 h-6 text-accent-goldBright" viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="7" width="20" height="10" rx="1.5" fill="currentColor" opacity="0.25" stroke="currentColor" strokeWidth="1.2" />
            <rect x="4" y="9" width="16" height="6" rx="0.75" fill="currentColor" opacity="0.5" stroke="currentColor" strokeWidth="0.8" />
            <rect x="6" y="10.5" width="12" height="3" rx="0.5" fill="currentColor" opacity="0.85" />
          </svg>
          <span className="text-shimmer-gold">{t('common:app.title')}</span>
        </h1>
        <span className="text-text-muted text-xs pulse-glow">{t('common:app.live')}</span>
      </header>

      {(loading || isPremium) && <TickerTape />}

      <QuickAccessGrid />

      <SafeWrap name="PriceWidget" t={t}>
        <PriceWidget />
      </SafeWrap>

      <SafeWrap name="PriceChart" t={t}>
        <PriceChart />
      </SafeWrap>

      {/* Paywall CTA for free users — shown below price */}
      {!loading && !isPremium && <DashboardPaywallCTA />}

      {/* Premium content — only shown for premium users */}
      {(loading || isPremium) && (
        <>
          <SafeWrap name="SessionClock" t={t}>
            <SessionClock />
          </SafeWrap>

          {/* Dual Predictions */}
          <div className="space-y-3">
            <SafeWrap name="AI Prediction" t={t}>
              <PredictionCard />
            </SafeWrap>
            <SafeWrap name="Quant Prediction" t={t}>
              <QuantPredictionCard />
            </SafeWrap>
          </div>

          <SafeWrap name="DailyBriefing" t={t}>
            <DailyBriefingCard />
          </SafeWrap>

          <SafeWrap name="SignalPanel" t={t}>
            <SignalPanel />
          </SafeWrap>

          <SafeWrap name="GoldSentimentGauge" t={t}>
            <GoldSentimentGauge />
          </SafeWrap>

          <SafeWrap name="MacroDashboard" t={t}>
            <MacroDashboard />
          </SafeWrap>

          <SafeWrap name="CorrelationWidget" t={t}>
            <CorrelationWidget />
          </SafeWrap>

          <SafeWrap name="SilverWidget" t={t}>
            <SilverWidget />
          </SafeWrap>

          <SafeWrap name="RealYieldWidget" t={t}>
            <RealYieldWidget />
          </SafeWrap>

          <SafeWrap name="ETFFlowWidget" t={t}>
            <ETFFlowWidget />
          </SafeWrap>

          <SafeWrap name="CentralBankWidget" t={t}>
            <CentralBankWidget />
          </SafeWrap>

          <SafeWrap name="SeasonalityWidget" t={t}>
            <SeasonalityWidget />
          </SafeWrap>

          <SafeWrap name="NewsCarousel" t={t}>
            <NewsCarousel />
          </SafeWrap>

          <DataSourceFooter sources={['goldapi', 'yahoo', 'fred', 'cftc', 'alphavantage', 'rss', 'reddit', 'kitco', 'ai']} />

          {/* Community CTA for premium users */}
          <CouncilCTA />
        </>
      )}

      <p className="text-text-muted text-[10px] text-center pb-4 leading-relaxed">
        {t('common:app.disclaimer')}
      </p>
    </div>
  )
}
