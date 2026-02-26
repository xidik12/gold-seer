import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'

const PAIRS = [
  { key: 'dxy', label: 'Gold vs DXY', expected: 'inverse', emoji: '\u{1F4B5}' },
  { key: 'treasury_10y', label: 'Gold vs Real Yield', expected: 'inverse', emoji: '\u{1F4CA}' },
  { key: 'vix', label: 'Gold vs VIX', expected: 'positive', emoji: '\u{1F4C8}' },
  { key: 'silver', label: 'Gold vs Silver', expected: 'positive', emoji: '\u{1F948}' },
  { key: 'sp500', label: 'Gold vs S&P 500', expected: 'weak', emoji: '\u{1F4C9}' },
]

function CorrelationBar({ corr }) {
  if (corr == null) return <span className="text-text-muted text-[10px]">N/A</span>
  const pct = Math.abs(corr) * 100
  const isPositive = corr > 0
  const barColor = isPositive ? 'bg-accent-green' : 'bg-accent-red'
  return (
    <div className="flex items-center gap-2 flex-1">
      <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-xs font-bold tabular-nums w-12 text-right ${isPositive ? 'text-accent-green' : 'text-accent-red'}`}>
        {corr > 0 ? '+' : ''}{corr.toFixed(2)}
      </span>
    </div>
  )
}

export default function CorrelationWidget() {
  const { t } = useTranslation('common')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getCorrelations()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
        <div className="h-5 w-40 bg-bg-hover rounded mb-3" />
        <div className="space-y-3">
          {[1,2,3,4,5].map(i => <div key={i} className="h-4 bg-bg-hover rounded" />)}
        </div>
      </div>
    )
  }

  const correlations = data?.correlations || {}

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-1">GOLD CORRELATIONS</h3>
      <p className="text-text-muted text-[9px] mb-3">30-day rolling correlations with key macro indicators</p>
      <div className="space-y-2.5">
        {PAIRS.map(({ key, label, emoji }) => {
          const c = correlations[key]
          return (
            <div key={key} className="flex items-center gap-2">
              <span className="text-xs w-4">{emoji}</span>
              <span className="text-text-secondary text-[11px] w-28 shrink-0">{label}</span>
              <CorrelationBar corr={c?.correlation} />
            </div>
          )
        })}
      </div>
      {data?.timestamp && (
        <p className="text-text-muted text-[9px] mt-2 text-right">
          {data.total_data_points} data points
        </p>
      )}
    </div>
  )
}
