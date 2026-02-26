import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatPricePrecise, formatPercent, safeFixed } from '../utils/format'
import SessionClock from '../components/SessionClock'
import IntradayHeatmap from '../components/IntradayHeatmap'

const POLL_INTERVAL = 60_000

const SESSION_META = {
  asian: { label: 'Asian', emoji: '\uD83C\uDDEF\uD83C\uDDF5', hours: '00:00 - 09:00 UTC' },
  london: { label: 'London', emoji: '\uD83C\uDDEC\uD83C\uDDE7', hours: '08:00 - 17:00 UTC' },
  new_york: { label: 'New York', emoji: '\uD83C\uDDFA\uD83C\uDDF8', hours: '13:00 - 22:00 UTC' },
}

function SessionCard({ session, data = {} }) {
  const { t } = useTranslation()
  const meta = SESSION_META[session] || { label: session, emoji: '', hours: '' }
  const isActive = data.status === 'active'
  const change = data.close && data.open ? ((data.close - data.open) / data.open) * 100 : data.change_pct ?? null
  const range = data.high && data.low ? data.high - data.low : null

  return (
    <div className={`bg-bg-card rounded-2xl p-4 border ${isActive ? 'border-accent-gold/30' : 'border-white/5'} slide-up`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">{meta.emoji}</span>
          <div>
            <h4 className="text-text-primary text-sm font-semibold">{meta.label}</h4>
            <p className="text-text-muted text-[10px]">{meta.hours}</p>
          </div>
        </div>
        <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium ${
          isActive ? 'bg-accent-green/10 text-accent-green' : 'bg-bg-secondary text-text-muted'
        }`}>
          <div className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
          {isActive ? t('sessions.active', 'Active') : t('sessions.closed', 'Closed')}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="bg-bg-secondary/50 rounded-lg px-2.5 py-1.5">
          <p className="text-text-muted text-[9px]">{t('sessions.open', 'Open')}</p>
          <p className="text-text-primary text-xs font-semibold tabular-nums">{data.open ? formatPricePrecise(data.open) : '--'}</p>
        </div>
        <div className="bg-bg-secondary/50 rounded-lg px-2.5 py-1.5">
          <p className="text-text-muted text-[9px]">{t('sessions.close', 'Close')}</p>
          <p className="text-text-primary text-xs font-semibold tabular-nums">{data.close ? formatPricePrecise(data.close) : '--'}</p>
        </div>
        <div className="bg-bg-secondary/50 rounded-lg px-2.5 py-1.5">
          <p className="text-text-muted text-[9px]">{t('sessions.high', 'High')}</p>
          <p className="text-text-primary text-xs font-semibold tabular-nums">{data.high ? formatPricePrecise(data.high) : '--'}</p>
        </div>
        <div className="bg-bg-secondary/50 rounded-lg px-2.5 py-1.5">
          <p className="text-text-muted text-[9px]">{t('sessions.low', 'Low')}</p>
          <p className="text-text-primary text-xs font-semibold tabular-nums">{data.low ? formatPricePrecise(data.low) : '--'}</p>
        </div>
      </div>

      <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/5">
        {change != null && (
          <span className={`text-xs font-bold tabular-nums ${change >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
            {formatPercent(change)}
          </span>
        )}
        {range != null && (
          <span className="text-text-muted text-[10px] tabular-nums">
            {t('sessions.range', 'Range')}: ${safeFixed(range, 2)}
          </span>
        )}
        {data.volume != null && (
          <span className="text-text-muted text-[10px] tabular-nums">
            {t('sessions.vol', 'Vol')}: {safeFixed(data.volume / 1000, 1)}K
          </span>
        )}
      </div>
    </div>
  )
}

function CountdownToNext({ sessions }) {
  const { t } = useTranslation()
  const [, setTick] = useState(0)

  useEffect(() => {
    const iv = setInterval(() => setTick((n) => n + 1), 1000)
    return () => clearInterval(iv)
  }, [])

  // Find next session open
  const now = new Date()
  const utcH = now.getUTCHours()
  const utcM = now.getUTCMinutes()
  const utcS = now.getUTCSeconds()
  const currentSec = utcH * 3600 + utcM * 60 + utcS

  const sessionTimes = [
    { name: 'Asian', openSec: 0 },
    { name: 'London', openSec: 8 * 3600 },
    { name: 'New York', openSec: 13 * 3600 },
  ]

  let nextName = ''
  let nextDiff = Infinity
  for (const s of sessionTimes) {
    let diff = s.openSec - currentSec
    if (diff <= 0) diff += 86400
    if (diff < nextDiff) {
      nextDiff = diff
      nextName = s.name
    }
  }

  const h = Math.floor(nextDiff / 3600)
  const m = Math.floor((nextDiff % 3600) / 60)
  const s = nextDiff % 60

  return (
    <div className="bg-bg-card rounded-2xl p-3 border border-accent-gold/10 text-center">
      <p className="text-text-muted text-[10px] mb-1">{t('sessions.nextSession', 'Next Session')} ({nextName})</p>
      <p className="text-accent-goldBright text-lg font-bold tabular-nums">
        {String(h).padStart(2, '0')}:{String(m).padStart(2, '0')}:{String(s).padStart(2, '0')}
      </p>
    </div>
  )
}

export default function SessionMap() {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const result = await fetchSessions()
      setData(result)
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

  // Find session with biggest move
  const sessions = data?.sessions || {}
  const allSessions = Object.entries(sessions)
  let biggestMove = null
  let biggestValue = 0
  for (const [key, s] of allSessions) {
    const move = Math.abs((s.change_pct ?? 0) || (s.close && s.open ? ((s.close - s.open) / s.open) * 100 : 0))
    if (move > biggestValue) {
      biggestValue = move
      biggestMove = key
    }
  }

  if (loading) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold text-shimmer-gold">{t('sessions.pageTitle', 'Trading Sessions')}</h1>
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
            <div className="h-5 w-28 bg-bg-hover rounded mb-3" />
            <div className="h-20 bg-bg-hover rounded" />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <h1 className="text-lg font-bold text-shimmer-gold">{t('sessions.pageTitle', 'Trading Sessions')}</h1>
      <p className="text-text-muted text-xs -mt-2">
        {t('sessions.subtitle', 'Gold XAUUSD session breakdown')}
      </p>

      <SessionClock />
      <CountdownToNext sessions={sessions} />

      <IntradayHeatmap />

      {error && (
        <div className="bg-bg-card rounded-2xl p-4 border border-accent-red/20">
          <p className="text-accent-red text-sm">{error}</p>
          <button onClick={fetchData} className="text-accent-gold text-xs mt-2 underline">
            {t('common:app.retry', 'Retry')}
          </button>
        </div>
      )}

      {/* Session cards */}
      {['asian', 'london', 'new_york'].map((key) => (
        <div key={key} className="relative">
          {biggestMove === key && (
            <span className="absolute -top-1 right-3 bg-accent-gold text-bg-primary text-[9px] font-bold px-2 py-0.5 rounded-full z-10">
              {t('sessions.biggestMove', 'Biggest Move')}
            </span>
          )}
          <SessionCard session={key} data={sessions[key] || {}} />
        </div>
      ))}

      {/* Performance stats */}
      {data?.stats && (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
          <h4 className="text-text-primary text-xs font-semibold mb-2">{t('sessions.todayStats', 'Today\'s Stats')}</h4>
          <div className="grid grid-cols-3 gap-2">
            {[
              { label: t('sessions.totalRange', 'Total Range'), value: data.stats.total_range != null && isFinite(data.stats.total_range) ? `$${safeFixed(data.stats.total_range, 2)}` : '--' },
              { label: t('sessions.totalVol', 'Total Volume'), value: data.stats.total_volume != null && isFinite(data.stats.total_volume) ? `${safeFixed(data.stats.total_volume / 1000, 1)}K` : '--' },
              { label: t('sessions.dayChange', 'Day Change'), value: data.stats.day_change != null ? formatPercent(data.stats.day_change) : '--' },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <p className="text-text-muted text-[9px]">{s.label}</p>
                <p className="text-text-primary text-xs font-semibold tabular-nums">{s.value}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

async function fetchSessions() {
  const res = await fetch(`${import.meta.env.VITE_API_URL || '/api'}/sessions/current`)
  if (!res.ok) throw new Error(`Sessions API error: ${res.status}`)
  return res.json()
}
