import { Component, lazy, Suspense, useEffect } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import { useTelegram } from './hooks/useTelegram'
import { useLanguageInit } from './i18n/useLanguage'
import { SubscriptionProvider, useSubscription } from './contexts/SubscriptionContext'
import NavBar from './components/NavBar'
import PaywallOverlay from './components/PaywallOverlay'

// Lazy-load all pages for code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Technical = lazy(() => import('./pages/Technical'))
const Signals = lazy(() => import('./pages/Signals'))
const News = lazy(() => import('./pages/News'))
const History = lazy(() => import('./pages/History'))
const About = lazy(() => import('./pages/About'))
const EventMemory = lazy(() => import('./pages/EventMemory'))
const ElliottWave = lazy(() => import('./pages/ElliottWave'))
const Advisor = lazy(() => import('./pages/Advisor'))
const MockTrading = lazy(() => import('./pages/MockTrading'))
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'))
const More = lazy(() => import('./pages/More'))
const Settings = lazy(() => import('./pages/Settings'))
const Subscription = lazy(() => import('./pages/Subscription'))
const Tools = lazy(() => import('./pages/Tools'))
const Resources = lazy(() => import('./pages/Resources'))
const Learn = lazy(() => import('./pages/Learn'))
const PartnerDashboard = lazy(() => import('./pages/PartnerDashboard'))
const PriceAlerts = lazy(() => import('./pages/PriceAlerts'))
const Briefing = lazy(() => import('./pages/Briefing'))
const PredictionGame = lazy(() => import('./pages/PredictionGame'))
const MarketOverview = lazy(() => import('./pages/MarketOverview'))

// Gold-specific pages
const COTAnalysis = lazy(() => import('./pages/COTAnalysis'))
const SessionMap = lazy(() => import('./pages/SessionMap'))
const TradingBot = lazy(() => import('./pages/TradingBot'))
const TradeJournal = lazy(() => import('./pages/TradeJournal'))
const GoldETF = lazy(() => import('./pages/GoldETF'))
const EconomicCalendarPage = lazy(() => import('./pages/EconomicCalendarPage'))

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo })
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 24, color: 'white', fontFamily: 'monospace' }}>
          <h2 style={{ color: '#ff4d6a' }}>Something went wrong</h2>
          <pre style={{ fontSize: 12, color: '#aaa', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
            {this.state.error?.message}
            {'\n\n'}
            {this.state.error?.stack}
            {'\n\n'}
            {this.state.errorInfo?.componentStack}
          </pre>
          <button
            onClick={() => window.location.reload()}
            style={{ marginTop: 16, padding: '8px 16px', background: '#4a9eff', border: 'none', borderRadius: 6, color: 'white', cursor: 'pointer' }}
          >
            Reload
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="w-6 h-6 border-2 border-accent-gold border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  return null
}

function PremiumRoute({ children }) {
  const { isPremium, loading } = useSubscription()
  if (loading) return <PageLoader />
  if (!isPremium) return <PaywallOverlay />
  return children
}

export default function App() {
  const location = useLocation()
  useLanguageInit()

  return (
    <ErrorBoundary>
      <SubscriptionProvider>
        <ScrollToTop />
        <div className="min-h-screen bg-bg-primary text-text-primary pb-20">
          <div key={location.pathname} className="page-enter">
          <Suspense fallback={<PageLoader />}>
          <Routes>
            {/* Free routes */}
            <Route path="/" element={<Dashboard />} />
            <Route path="/more" element={<More />} />
            <Route path="/subscription" element={<Subscription />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/about" element={<About />} />
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/partner/:code" element={<PartnerDashboard />} />

            {/* Premium routes — gated */}
            <Route path="/technical" element={<PremiumRoute><Technical /></PremiumRoute>} />
            <Route path="/signals" element={<PremiumRoute><Signals /></PremiumRoute>} />
            <Route path="/events" element={<PremiumRoute><EventMemory /></PremiumRoute>} />
            <Route path="/elliott-wave" element={<PremiumRoute><ElliottWave /></PremiumRoute>} />
            <Route path="/tools" element={<PremiumRoute><Tools /></PremiumRoute>} />
            <Route path="/resources" element={<PremiumRoute><Resources /></PremiumRoute>} />
            <Route path="/learn" element={<PremiumRoute><Learn /></PremiumRoute>} />
            <Route path="/history" element={<PremiumRoute><History /></PremiumRoute>} />
            <Route path="/news" element={<PremiumRoute><News /></PremiumRoute>} />
            <Route path="/advisor" element={<PremiumRoute><Advisor /></PremiumRoute>} />
            <Route path="/mock-trading" element={<PremiumRoute><MockTrading /></PremiumRoute>} />
            <Route path="/alerts" element={<PremiumRoute><PriceAlerts /></PremiumRoute>} />
            <Route path="/briefing" element={<PremiumRoute><Briefing /></PremiumRoute>} />
            <Route path="/game" element={<PremiumRoute><PredictionGame /></PremiumRoute>} />
            <Route path="/markets" element={<PremiumRoute><MarketOverview /></PremiumRoute>} />

            {/* Gold-specific premium routes */}
            <Route path="/cot" element={<PremiumRoute><COTAnalysis /></PremiumRoute>} />
            <Route path="/sessions" element={<PremiumRoute><SessionMap /></PremiumRoute>} />
            <Route path="/trading-bot" element={<PremiumRoute><TradingBot /></PremiumRoute>} />
            <Route path="/trade-journal" element={<PremiumRoute><TradeJournal /></PremiumRoute>} />
            <Route path="/gold-etf" element={<PremiumRoute><GoldETF /></PremiumRoute>} />
            <Route path="/calendar-full" element={<PremiumRoute><EconomicCalendarPage /></PremiumRoute>} />
          </Routes>
          </Suspense>
          </div>
          <NavBar />
        </div>
      </SubscriptionProvider>
    </ErrorBoundary>
  )
}
