import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'

/**
 * SilverWidget — Shows current silver (XAG/USD) price, 24h change,
 * gold/silver ratio gauge with historical context, and signal interpretation.
 * Silver is gold's most important correlated asset; gold traders always watch this ratio.
 */

function RatioGauge({ ratio }) {
  // Historical range: ~15 (all-time low) to ~130 (2020 peak)
  // Practical display range: 40-100
  const MIN = 40
  const MAX = 100
  const AVG = 65
  const clamped = Math.max(MIN, Math.min(MAX, ratio))
  const pct = ((clamped - MIN) / (MAX - MIN)) * 100
  const avgPct = ((AVG - MIN) / (MAX - MIN)) * 100

  // Color gradient: green (low/silver overvalued) -> yellow (neutral) -> red (high/silver undervalued)
  let markerColor = 'bg-accent-gold'
  if (ratio > 80) markerColor = 'bg-accent-red'
  else if (ratio > 70) markerColor = 'bg-yellow-400'
  else if (ratio < 50) markerColor = 'bg-accent-green'

  return (
    <div className="mt-2">
      {/* Gauge bar */}
      <div className="relative h-2.5 bg-white/5 rounded-full overflow-hidden">
        {/* Gradient background */}
        <div
          className="absolute inset-y-0 rounded-full"
          style={{
            left: '0%',
            right: '0%',
            background: 'linear-gradient(to right, #22c55e, #eab308, #ef4444)',
            opacity: 0.2,
          }}
        />
        {/* Average marker */}
        <div
          className="absolute top-0 bottom-0 w-px bg-text-muted/40"
          style={{ left: `${avgPct}%` }}
        />
        {/* Current value marker */}
        <div
          className={`absolute top-0 bottom-0 w-2 rounded-full ${markerColor} transition-all duration-700 shadow-sm`}
          style={{ left: `calc(${pct}% - 4px)` }}
        />
      </div>

      {/* Labels */}
      <div className="flex justify-between mt-1">
        <span className="text-accent-green text-[8px] font-medium">40</span>
        <span className="text-text-muted text-[8px]">Avg ~65</span>
        <span className="text-accent-red text-[8px] font-medium">100</span>
      </div>
    </div>
  )
}

function SignalBadge({ signal }) {
  const config = {
    silver_very_undervalued: { label: 'Silver Very Undervalued', color: 'text-accent-green', bg: 'bg-accent-green/10' },
    silver_undervalued: { label: 'Silver Undervalued', color: 'text-accent-green', bg: 'bg-accent-green/10' },
    slightly_high: { label: 'Slightly High', color: 'text-yellow-400', bg: 'bg-yellow-400/10' },
    neutral: { label: 'Neutral', color: 'text-text-secondary', bg: 'bg-white/5' },
    slightly_low: { label: 'Slightly Low', color: 'text-yellow-400', bg: 'bg-yellow-400/10' },
    silver_overvalued: { label: 'Silver Overvalued', color: 'text-accent-red', bg: 'bg-accent-red/10' },
  }

  const c = config[signal] || config.neutral

  return (
    <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded ${c.color} ${c.bg}`}>
      {c.label}
    </span>
  )
}

export default function SilverWidget() {
  const { t } = useTranslation('common')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getSilverData()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
        <div className="h-4 w-36 bg-bg-hover rounded mb-3" />
        <div className="flex gap-4">
          <div className="h-8 w-24 bg-bg-hover rounded" />
          <div className="h-8 w-24 bg-bg-hover rounded" />
        </div>
        <div className="h-3 w-full bg-bg-hover rounded mt-3" />
      </div>
    )
  }

  if (!data || data.silver_price == null) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-1">SILVER (XAG/USD)</h3>
        <p className="text-text-muted text-[10px]">Silver data unavailable</p>
      </div>
    )
  }

  const { silver_price, change_24h, change_24h_pct, gold_silver_ratio, ratio_change_24h, ratio_signal, ratio_interpretation } = data
  const isUp = change_24h != null && change_24h >= 0
  const ratioUp = ratio_change_24h != null && ratio_change_24h >= 0

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm">🥈</span>
          <h3 className="text-text-secondary text-xs font-semibold">SILVER & GOLD/SILVER RATIO</h3>
        </div>
        <SignalBadge signal={ratio_signal} />
      </div>

      {/* Two-column: Silver Price | G/S Ratio */}
      <div className="grid grid-cols-2 gap-3 mb-2">
        {/* Silver Price */}
        <div>
          <p className="text-text-muted text-[9px] mb-0.5">XAG/USD</p>
          <div className="flex items-baseline gap-1.5">
            <span className="text-lg font-bold text-text-primary tabular-nums">
              ${silver_price.toFixed(2)}
            </span>
          </div>
          {change_24h_pct != null && (
            <p className={`text-[10px] font-medium tabular-nums ${isUp ? 'text-accent-green' : 'text-accent-red'}`}>
              {isUp ? '+' : ''}{change_24h?.toFixed(2)} ({isUp ? '+' : ''}{change_24h_pct}%)
            </p>
          )}
        </div>

        {/* Gold/Silver Ratio */}
        <div>
          <p className="text-text-muted text-[9px] mb-0.5">Gold/Silver Ratio</p>
          <div className="flex items-baseline gap-1.5">
            <span className="text-lg font-bold text-accent-goldBright tabular-nums">
              {gold_silver_ratio?.toFixed(1) ?? '--'}
            </span>
          </div>
          {ratio_change_24h != null && (
            <p className={`text-[10px] font-medium tabular-nums ${ratioUp ? 'text-accent-red' : 'text-accent-green'}`}>
              {ratioUp ? '+' : ''}{ratio_change_24h.toFixed(1)} 24h
            </p>
          )}
        </div>
      </div>

      {/* Ratio Gauge */}
      {gold_silver_ratio != null && <RatioGauge ratio={gold_silver_ratio} />}

      {/* Interpretation */}
      {ratio_interpretation && (
        <p className="text-text-muted text-[9px] mt-2 leading-relaxed">
          {ratio_interpretation}
        </p>
      )}
    </div>
  )
}
