import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatDate, formatNumber } from '../utils/format'
import COTChart from '../components/COTChart'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Area, ComposedChart, Bar,
} from 'recharts'

const POLL_INTERVAL = 300_000

function NetPercentileGauge({ percentile = 50 }) {
  const { t } = useTranslation()
  const pct = Math.max(0, Math.min(100, percentile))
  const color = pct >= 70 ? '#22c55e' : pct <= 30 ? '#ef4444' : '#D4AF37'

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h4 className="text-text-primary text-xs font-semibold mb-3">
        {t('cot.netPercentile', 'Net Long Percentile')}
      </h4>
      <div className="relative h-3 bg-bg-secondary rounded-full overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <div className="flex justify-between mt-1.5">
        <span className="text-text-muted text-[9px]">{t('cot.mostShort', 'Most Short')}</span>
        <span className="text-sm font-bold tabular-nums" style={{ color }}>{pct}%</span>
        <span className="text-text-muted text-[9px]">{t('cot.mostLong', 'Most Long')}</span>
      </div>
    </div>
  )
}

export default function COTAnalysis() {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const result = await api.getCOTLatest ? await api.getCOTLatest() : await fetchCOT()
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

  if (loading) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold text-shimmer-gold">{t('cot.pageTitle', 'COT Analysis')}</h1>
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
            <div className="h-5 w-36 bg-bg-hover rounded mb-3" />
            <div className="h-40 bg-bg-hover rounded" />
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="px-4 pt-4">
        <h1 className="text-lg font-bold text-shimmer-gold mb-4">{t('cot.pageTitle', 'COT Analysis')}</h1>
        <div className="bg-bg-card rounded-2xl p-4 border border-accent-red/20">
          <p className="text-accent-red text-sm">{error}</p>
          <button onClick={fetchData} className="text-accent-gold text-xs mt-2 underline">
            {t('common:app.retry', 'Retry')}
          </button>
        </div>
      </div>
    )
  }

  const latest = data?.latest || data || {}
  const history = data?.history || []
  const percentile = latest.net_percentile ?? latest.mm_net_percentile ?? 50

  // Open interest trend data
  const oiData = history.map((h) => ({
    date: h.report_date ? new Date(h.report_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '--',
    oi: h.open_interest ?? 0,
    price: h.price ?? h.gold_price ?? 0,
  }))

  // Positioning vs price data
  const posVsPrice = history.map((h) => ({
    date: h.report_date ? new Date(h.report_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '--',
    net_long: (h.mm_long ?? 0) - (h.mm_short ?? 0),
    price: h.price ?? h.gold_price ?? 0,
  }))

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <h1 className="text-lg font-bold text-shimmer-gold">{t('cot.pageTitle', 'COT Analysis')}</h1>
      <p className="text-text-muted text-xs -mt-2">
        {t('cot.subtitle', 'Commitments of Traders — Gold Futures (COMEX)')}
      </p>

      {/* Managed Money Positioning */}
      <COTChart data={history.length ? history : [latest]} />

      {/* Net Percentile Gauge */}
      <NetPercentileGauge percentile={percentile} />

      {/* Open Interest Trend */}
      {oiData.length > 1 && (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
          <h4 className="text-text-primary text-sm font-semibold mb-3">
            {t('cot.openInterest', 'Open Interest Trend')}
          </h4>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={oiData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="date" tick={{ fill: '#999', fontSize: 9 }} axisLine={false} tickLine={false} />
              <YAxis
                tick={{ fill: '#999', fontSize: 9 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => formatNumber(v)}
              />
              <Tooltip
                contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
              />
              <Line type="monotone" dataKey="oi" stroke="#D4AF37" strokeWidth={2} dot={false} name={t('cot.openInterest', 'Open Interest')} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Positioning vs Price */}
      {posVsPrice.length > 1 && (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
          <h4 className="text-text-primary text-sm font-semibold mb-3">
            {t('cot.positioningVsPrice', 'Positioning vs Gold Price')}
          </h4>
          <ResponsiveContainer width="100%" height={220}>
            <ComposedChart data={posVsPrice}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="date" tick={{ fill: '#999', fontSize: 9 }} axisLine={false} tickLine={false} />
              <YAxis
                yAxisId="left"
                tick={{ fill: '#999', fontSize: 9 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => formatNumber(v)}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fill: '#999', fontSize: 9 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `$${formatNumber(v)}`}
              />
              <Tooltip
                contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
              />
              <Bar yAxisId="left" dataKey="net_long" fill="#D4AF37" opacity={0.4} radius={[2, 2, 0, 0]} name={t('cot.netLong', 'Net Long')} />
              <Line yAxisId="right" type="monotone" dataKey="price" stroke="#FFD700" strokeWidth={2} dot={false} name={t('cot.goldPrice', 'Gold Price')} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Latest report info */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h4 className="text-text-primary text-xs font-semibold mb-2">{t('cot.latestReport', 'Latest Report')}</h4>
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: t('cot.mmLong', 'MM Long'), value: formatNumber(latest.mm_long ?? 0) },
            { label: t('cot.mmShort', 'MM Short'), value: formatNumber(latest.mm_short ?? 0) },
            { label: t('cot.netLong', 'Net Long'), value: formatNumber((latest.mm_long ?? 0) - (latest.mm_short ?? 0)) },
            { label: t('cot.oi', 'Open Interest'), value: formatNumber(latest.open_interest ?? 0) },
          ].map((item) => (
            <div key={item.label} className="bg-bg-secondary/50 rounded-lg px-3 py-2">
              <p className="text-text-muted text-[10px]">{item.label}</p>
              <p className="text-text-primary text-sm font-semibold tabular-nums">{item.value}</p>
            </div>
          ))}
        </div>
        {latest.report_date && (
          <p className="text-text-muted text-[10px] mt-2 text-right">
            {t('cot.reportDate', 'Report')}: {formatDate(latest.report_date)}
          </p>
        )}
      </div>
    </div>
  )
}

// Fallback fetch if api.getCOTLatest isn't available
async function fetchCOT() {
  const res = await fetch(`${import.meta.env.VITE_API_URL || '/api'}/cot/latest`)
  if (!res.ok) throw new Error(`COT API error: ${res.status}`)
  return res.json()
}
