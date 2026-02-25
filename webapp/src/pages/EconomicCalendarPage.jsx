import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'

const POLL_INTERVAL = 300_000

const IMPORTANCE_STYLES = {
  high: { bg: 'bg-accent-red/10', text: 'text-accent-red', dot: 'bg-accent-red', label: 'High' },
  medium: { bg: 'bg-accent-goldBright/10', text: 'text-accent-goldBright', dot: 'bg-accent-goldBright', label: 'Medium' },
  low: { bg: 'bg-bg-secondary', text: 'text-text-muted', dot: 'bg-gray-500', label: 'Low' },
}

function formatEventDate(dateStr) {
  const d = new Date(dateStr)
  const now = new Date()
  const tomorrow = new Date(now)
  tomorrow.setDate(tomorrow.getDate() + 1)

  const locale = navigator.language || 'en-US'
  const dateOnly = d.toLocaleDateString(locale, { weekday: 'short', month: 'short', day: 'numeric' })
  const time = d.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit', hour12: false })

  if (d.toDateString() === now.toDateString()) return `Today ${time}`
  if (d.toDateString() === tomorrow.toDateString()) return `Tomorrow ${time}`
  return `${dateOnly} ${time}`
}

function getCountdownString(dateStr) {
  const diff = new Date(dateStr) - new Date()
  if (diff <= 0) return null
  const hours = Math.floor(diff / 3600000)
  const minutes = Math.floor((diff % 3600000) / 60000)
  if (hours > 24) return `${Math.floor(hours / 24)}d ${hours % 24}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

export default function EconomicCalendarPage() {
  const { t } = useTranslation()
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all') // all, high, medium, low
  const [, setTick] = useState(0)

  const fetchData = useCallback(async () => {
    try {
      const result = await api.getEconomicCalendar(30)
      setEvents(result?.events || [])
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const iv = setInterval(fetchData, POLL_INTERVAL)
    return () => clearInterval(iv)
  }, [fetchData])

  // Update countdown every minute
  useEffect(() => {
    const iv = setInterval(() => setTick((n) => n + 1), 60_000)
    return () => clearInterval(iv)
  }, [])

  const filteredEvents = filter === 'all' ? events : events.filter((e) => e.importance === filter)

  // Find next upcoming event
  const now = new Date()
  const nextEvent = events.find((e) => new Date(e.event_date) > now)
  const nextCountdown = nextEvent ? getCountdownString(nextEvent.event_date) : null

  if (loading) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold text-shimmer-gold">{t('calendar.pageTitle', 'Economic Calendar')}</h1>
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="bg-bg-card rounded-xl p-3 border border-white/5 animate-pulse">
            <div className="h-4 w-48 bg-bg-hover rounded mb-2" />
            <div className="h-3 w-32 bg-bg-hover rounded" />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <h1 className="text-lg font-bold text-shimmer-gold">{t('calendar.pageTitle', 'Economic Calendar')}</h1>

      {/* Next event countdown */}
      {nextEvent && nextCountdown && (
        <div className="bg-bg-card rounded-2xl p-3 border border-accent-gold/10 flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <p className="text-text-muted text-[10px]">{t('calendar.nextEvent', 'Next Event')}</p>
            <p className="text-text-primary text-xs font-semibold truncate">{nextEvent.event_name}</p>
          </div>
          <div className="text-right shrink-0 ml-3">
            <p className="text-accent-goldBright text-sm font-bold tabular-nums">{nextCountdown}</p>
          </div>
        </div>
      )}

      {/* Filter bar */}
      <div className="flex gap-2">
        {['all', 'high', 'medium', 'low'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-[10px] font-medium transition-all ${
              filter === f
                ? 'bg-accent-gold/20 text-accent-goldBright border border-accent-gold/30'
                : 'bg-bg-secondary text-text-muted border border-white/5 hover:text-text-primary'
            }`}
          >
            {f === 'all'
              ? t('calendar.all', 'All')
              : t(`calendar.${f}`, IMPORTANCE_STYLES[f]?.label || f)
            } ({f === 'all' ? events.length : events.filter((e) => e.importance === f).length})
          </button>
        ))}
      </div>

      {error && (
        <div className="bg-bg-card rounded-2xl p-3 border border-accent-red/20">
          <p className="text-accent-red text-xs">{error}</p>
          <button onClick={fetchData} className="text-accent-gold text-xs mt-1 underline">
            {t('common:app.retry', 'Retry')}
          </button>
        </div>
      )}

      {/* Event list */}
      {filteredEvents.length === 0 ? (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5 text-center">
          <p className="text-text-muted text-xs">{t('calendar.noEvents', 'No events found')}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filteredEvents.map((event, i) => {
            const imp = IMPORTANCE_STYLES[event.importance] || IMPORTANCE_STYLES.low
            const isPast = new Date(event.event_date) < now
            const countdown = !isPast ? getCountdownString(event.event_date) : null
            const goldImpact = event.gold_impact ?? event.gold_impact_score ?? null

            return (
              <div
                key={`${event.event_name}-${event.event_date}-${i}`}
                className={`bg-bg-card rounded-xl p-3 border border-white/5 ${isPast ? 'opacity-50' : 'slide-up'}`}
              >
                <div className="flex items-start gap-3">
                  {/* Importance indicator */}
                  <div className="flex flex-col items-center gap-0.5 pt-0.5 shrink-0">
                    {[1, 2, 3].map((dot) => (
                      <div
                        key={dot}
                        className={`w-1.5 h-1.5 rounded-full ${
                          (event.importance === 'high' && dot <= 3) ||
                          (event.importance === 'medium' && dot <= 2) ||
                          (event.importance === 'low' && dot <= 1)
                            ? imp.dot
                            : 'bg-bg-secondary'
                        }`}
                      />
                    ))}
                  </div>

                  {/* Event details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-text-primary text-xs font-semibold truncate">{event.event_name}</p>
                      <span className="text-[9px] font-mono bg-bg-secondary rounded px-1.5 py-0.5 text-text-muted shrink-0">
                        {event.country || 'US'}
                      </span>
                    </div>
                    <p className="text-text-muted text-[10px] mt-0.5">{formatEventDate(event.event_date)}</p>

                    {/* Values row */}
                    <div className="flex items-center gap-3 mt-1.5">
                      {event.actual != null && (
                        <span className="text-accent-green text-[10px] font-semibold">
                          A: {event.actual}
                        </span>
                      )}
                      {event.forecast != null && (
                        <span className="text-text-secondary text-[10px]">
                          F: {event.forecast}
                        </span>
                      )}
                      {event.previous != null && (
                        <span className="text-text-muted text-[10px]">
                          P: {event.previous}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Right side: countdown + gold impact */}
                  <div className="text-right shrink-0">
                    {countdown && (
                      <p className="text-accent-goldBright text-[10px] font-bold tabular-nums">{countdown}</p>
                    )}
                    {isPast && (
                      <p className="text-text-muted text-[10px]">{t('calendar.past', 'Past')}</p>
                    )}
                    {goldImpact != null && (
                      <div className={`mt-1 px-1.5 py-0.5 rounded text-[9px] font-medium ${
                        goldImpact >= 7 ? 'bg-accent-red/10 text-accent-red'
                          : goldImpact >= 4 ? 'bg-accent-goldBright/10 text-accent-goldBright'
                          : 'bg-bg-secondary text-text-muted'
                      }`}>
                        {t('calendar.goldImpact', 'Gold')}: {goldImpact}/10
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      <p className="text-text-muted text-[10px] text-center">
        {t('calendar.disclaimer', 'Times shown in your local timezone. Data may be delayed.')}
      </p>
    </div>
  )
}
