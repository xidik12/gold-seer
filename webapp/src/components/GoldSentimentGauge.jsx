import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'

function getGaugeLabel(value, t) {
  if (value <= -60) return t('goldSentiment.extremeBearish', 'Extreme Bearish')
  if (value <= -20) return t('goldSentiment.bearish', 'Bearish')
  if (value <= 20) return t('goldSentiment.neutral', 'Neutral')
  if (value <= 60) return t('goldSentiment.bullish', 'Bullish')
  return t('goldSentiment.extremeBullish', 'Extreme Bullish')
}

function getGaugeColor(value) {
  if (value <= -60) return '#ef4444'
  if (value <= -20) return '#f97316'
  if (value <= 20) return '#D4AF37'
  if (value <= 60) return '#22c55e'
  return '#00d68f'
}

function SemiGauge({ value, size = 200 }) {
  // value from -100 to +100, mapped to 0..1
  const ratio = Math.max(0, Math.min(1, (value + 100) / 200))
  const strokeWidth = 14
  const radius = (size - strokeWidth) / 2
  const cx = size / 2
  const cy = size / 2

  const startAngle = Math.PI
  const bgStartX = cx + radius * Math.cos(startAngle)
  const bgStartY = cy - radius * Math.sin(startAngle)
  const bgEndX = cx + radius * Math.cos(0)
  const bgEndY = cy - radius * Math.sin(0)
  const bgPath = `M ${bgStartX} ${bgStartY} A ${radius} ${radius} 0 0 1 ${bgEndX} ${bgEndY}`

  const fillAngle = Math.PI - ratio * Math.PI
  const fillEndX = cx + radius * Math.cos(fillAngle)
  const fillEndY = cy - radius * Math.sin(fillAngle)
  const largeArc = ratio > 0.5 ? 1 : 0
  const fgPath = `M ${bgStartX} ${bgStartY} A ${radius} ${radius} 0 ${largeArc} 1 ${fillEndX} ${fillEndY}`

  const needleLength = radius - 10
  const needleX = cx + needleLength * Math.cos(fillAngle)
  const needleY = cy - needleLength * Math.sin(fillAngle)

  const color = getGaugeColor(value)

  return (
    <svg
      width={size}
      height={size / 2 + 24}
      viewBox={`0 0 ${size} ${size / 2 + 24}`}
      className="mx-auto"
    >
      <defs>
        <linearGradient id="gold-gauge-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#ef4444" />
          <stop offset="25%" stopColor="#f97316" />
          <stop offset="50%" stopColor="#D4AF37" />
          <stop offset="75%" stopColor="#22c55e" />
          <stop offset="100%" stopColor="#00d68f" />
        </linearGradient>
      </defs>

      {/* Background arc */}
      <path
        d={bgPath}
        fill="none"
        stroke="#1a1a24"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
      />

      {/* Faint gradient overlay */}
      <path
        d={bgPath}
        fill="none"
        stroke="url(#gold-gauge-gradient)"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        opacity={0.12}
      />

      {/* Filled arc */}
      {ratio > 0.005 && (
        <path
          d={fgPath}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          className="transition-all duration-700"
        />
      )}

      {/* Needle */}
      <line
        x1={cx}
        y1={cy}
        x2={needleX}
        y2={needleY}
        stroke="#ffffff"
        strokeWidth={2}
        strokeLinecap="round"
        className="transition-all duration-700"
      />

      {/* Center dot */}
      <circle cx={cx} cy={cy} r={4} fill="#ffffff" />

      {/* Min / Max labels */}
      <text x={strokeWidth / 2 + 2} y={cy + 18} fill="#5a5a70" fontSize="10" textAnchor="start">
        -100
      </text>
      <text x={size - strokeWidth / 2 - 2} y={cy + 18} fill="#5a5a70" fontSize="10" textAnchor="end">
        +100
      </text>
    </svg>
  )
}

export default function GoldSentimentGauge() {
  const { t } = useTranslation()
  const [score, setScore] = useState(null)
  const [loading, setLoading] = useState(true)
  const [breakdown, setBreakdown] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const macro = await api.getMacroData()

      // Extract raw numeric values — macro items are {price: X, change_1h, change_24h}
      const vixRaw = macro?.vix?.price ?? 20
      const realYield = macro?.real_yield_10y ?? 1.5
      const dxyRaw = macro?.dxy?.price ?? null
      const goldRaw = macro?.gold?.price ?? null

      // VIX: high = safe-haven demand = bullish for gold
      const vixScore = Math.round(Math.max(-100, Math.min(100, (vixRaw - 20) * 5)))

      // Real yield: negative = bullish for gold, positive = bearish
      const yieldScore = Math.round(Math.max(-100, Math.min(100, -realYield * 50)))

      // DXY: weak dollar = bullish gold. DXY ~100 neutral, <95 bullish, >105 bearish
      const dxyScore = dxyRaw != null
        ? Math.round(Math.max(-100, Math.min(100, (100 - dxyRaw) * 10)))
        : 0

      // Gold momentum: recent 24h change as signal
      const goldChange = macro?.gold?.change_24h ?? 0
      const momentumScore = Math.round(Math.max(-100, Math.min(100, goldChange * 20)))

      const composite = Math.round((vixScore + yieldScore + dxyScore + momentumScore) / 4)

      setScore(composite)
      setBreakdown({ vix: vixScore, yield: yieldScore, dxy: dxyScore, momentum: momentumScore })
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const iv = setInterval(fetchData, 120_000)
    return () => clearInterval(iv)
  }, [fetchData])

  if (loading) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
        <div className="h-5 w-40 bg-bg-hover rounded mb-4" />
        <div className="h-24 w-40 bg-bg-hover rounded mx-auto mb-3" />
        <div className="h-6 w-28 bg-bg-hover rounded mx-auto" />
      </div>
    )
  }

  const value = score ?? 0
  const label = getGaugeLabel(value, t)
  const color = getGaugeColor(value)

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <h3 className="text-text-primary text-sm font-semibold mb-2">
        {t('goldSentiment.title', 'Gold Sentiment')}
      </h3>

      <SemiGauge value={value} />

      <div className="text-center -mt-1">
        <p className="text-3xl font-bold tabular-nums" style={{ color }}>
          {value > 0 ? '+' : ''}{value}
        </p>
        <p className="text-sm font-medium mt-0.5" style={{ color }}>
          {label}
        </p>
      </div>

      {/* Breakdown */}
      {breakdown && (
        <div className="grid grid-cols-2 gap-2 mt-3">
          {[
            { key: 'vix', label: t('goldSentiment.vix', 'VIX'), val: breakdown.vix },
            { key: 'yield', label: t('goldSentiment.yield', 'Real Yield'), val: breakdown.yield },
            { key: 'dxy', label: t('goldSentiment.dxy', 'USD (DXY)'), val: breakdown.dxy },
            { key: 'momentum', label: t('goldSentiment.momentum', 'Momentum'), val: breakdown.momentum },
          ].map((item) => (
            <div key={item.key} className="flex items-center justify-between px-2 py-1 bg-bg-secondary/50 rounded-lg">
              <span className="text-text-muted text-[10px]">{item.label}</span>
              <span className={`text-[10px] font-bold tabular-nums ${
                item.val > 0 ? 'text-accent-green' : item.val < 0 ? 'text-accent-red' : 'text-text-muted'
              }`}>
                {item.val > 0 ? '+' : ''}{item.val}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
