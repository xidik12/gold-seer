import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatNumber, formatPricePrecise, formatDate, safeFixed } from '../utils/format'
import ETFFlowWidget from '../components/ETFFlowWidget'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell, ComposedChart,
} from 'recharts'

const POLL_INTERVAL = 300_000

const ETF_INFO = {
  GLD: { name: 'SPDR Gold Shares', color: '#FFD700' },
  IAU: { name: 'iShares Gold Trust', color: '#D4AF37' },
  SGOL: { name: 'Aberdeen Standard Physical Gold', color: '#B8860B' },
  GLDM: { name: 'SPDR Gold MiniShares', color: '#f59e0b' },
}

export default function GoldETF() {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const result = await fetchETFData()
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
        <h1 className="text-lg font-bold text-shimmer-gold">{t('goldEtf.pageTitle', 'Gold ETF Analysis')}</h1>
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
            <div className="h-5 w-36 bg-bg-hover rounded mb-3" />
            <div className="h-32 bg-bg-hover rounded" />
          </div>
        ))}
      </div>
    )
  }

  const etfs = data?.etfs || []
  const dailyFlows = data?.daily_flows || []
  const holdingsTrend = data?.holdings_trend || []
  const flowVsPrice = data?.flow_vs_price || []

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <h1 className="text-lg font-bold text-shimmer-gold">{t('goldEtf.pageTitle', 'Gold ETF Analysis')}</h1>
      <p className="text-text-muted text-xs -mt-2">
        {t('goldEtf.subtitle', 'Track institutional gold demand through ETF flows')}
      </p>

      {error && (
        <div className="bg-bg-card rounded-2xl p-3 border border-accent-red/20">
          <p className="text-accent-red text-xs">{error}</p>
          <button onClick={fetchData} className="text-accent-gold text-xs mt-1 underline">
            {t('common:app.retry', 'Retry')}
          </button>
        </div>
      )}

      {/* Compact daily flows bar chart */}
      <ETFFlowWidget flows={etfs} />

      {/* Daily flow history */}
      {dailyFlows.length > 1 && (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
          <h4 className="text-text-primary text-sm font-semibold mb-3">
            {t('goldEtf.dailyFlows', 'Daily Net Flows (tonnes)')}
          </h4>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={dailyFlows.slice(-30)}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="date"
                tick={{ fill: '#999', fontSize: 9 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(d) => {
                  try { return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) } catch { return d }
                }}
              />
              <YAxis tick={{ fill: '#999', fontSize: 9 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
                formatter={(v) => [v != null && isFinite(v) ? `${v > 0 ? '+' : ''}${safeFixed(v, 2)}t` : '--', t('goldEtf.flow', 'Flow')]}
              />
              <Bar dataKey="flow" radius={[2, 2, 0, 0]}>
                {dailyFlows.slice(-30).map((entry, i) => (
                  <Cell key={i} fill={(entry.flow ?? 0) >= 0 ? '#22c55e' : '#ef4444'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Total holdings trend */}
      {holdingsTrend.length > 1 && (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
          <h4 className="text-text-primary text-sm font-semibold mb-3">
            {t('goldEtf.totalHoldings', 'Total Holdings Trend')}
          </h4>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={holdingsTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="date"
                tick={{ fill: '#999', fontSize: 9 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(d) => {
                  try { return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) } catch { return d }
                }}
              />
              <YAxis tick={{ fill: '#999', fontSize: 9 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
                formatter={(v) => [v != null && isFinite(v) ? `${safeFixed(v, 1)} tonnes` : '--', t('goldEtf.holdings', 'Holdings')]}
              />
              <Line type="monotone" dataKey="holdings" stroke="#D4AF37" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Price correlation */}
      {flowVsPrice.length > 1 && (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
          <h4 className="text-text-primary text-sm font-semibold mb-3">
            {t('goldEtf.priceCorrelation', 'ETF Flows vs Gold Price')}
          </h4>
          <ResponsiveContainer width="100%" height={200}>
            <ComposedChart data={flowVsPrice.slice(-30)}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="date" tick={{ fill: '#999', fontSize: 9 }} axisLine={false} tickLine={false}
                tickFormatter={(d) => {
                  try { return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) } catch { return d }
                }}
              />
              <YAxis yAxisId="left" tick={{ fill: '#999', fontSize: 9 }} axisLine={false} tickLine={false} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: '#999', fontSize: 9 }} axisLine={false} tickLine={false}
                tickFormatter={(v) => `$${formatNumber(v)}`}
              />
              <Tooltip
                contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
              />
              <Bar yAxisId="left" dataKey="flow" opacity={0.5} radius={[2, 2, 0, 0]}>
                {flowVsPrice.slice(-30).map((entry, i) => (
                  <Cell key={i} fill={(entry.flow ?? 0) >= 0 ? '#22c55e' : '#ef4444'} />
                ))}
              </Bar>
              <Line yAxisId="right" type="monotone" dataKey="price" stroke="#FFD700" strokeWidth={2} dot={false} name={t('goldEtf.goldPrice', 'Gold Price')} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Per-ETF cards */}
      <h3 className="text-text-primary text-sm font-semibold">{t('goldEtf.perEtf', 'Per-ETF Breakdown')}</h3>
      <div className="grid grid-cols-2 gap-3">
        {Object.entries(ETF_INFO).map(([ticker, info]) => {
          const etf = etfs.find((e) => e.ticker === ticker || e.name === ticker) || {}
          return (
            <div key={ticker} className="bg-bg-card rounded-xl p-3 border border-white/5 slide-up">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: info.color }} />
                <span className="text-text-primary text-xs font-bold">{ticker}</span>
              </div>
              <p className="text-text-muted text-[9px] mb-2">{info.name}</p>
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-text-muted text-[10px]">{t('goldEtf.holdings', 'Holdings')}</span>
                  <span className="text-text-primary text-[10px] font-semibold tabular-nums">
                    {etf.holdings != null ? `${safeFixed(etf.holdings, 1)}t` : '--'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted text-[10px]">{t('goldEtf.dayFlow', 'Day Flow')}</span>
                  <span className={`text-[10px] font-semibold tabular-nums ${
                    (etf.daily_flow ?? etf.net_flow ?? 0) >= 0 ? 'text-accent-green' : 'text-accent-red'
                  }`}>
                    {etf.daily_flow != null || etf.net_flow != null
                      ? `${(etf.daily_flow ?? etf.net_flow) > 0 ? '+' : ''}${safeFixed(etf.daily_flow ?? etf.net_flow, 2)}t`
                      : '--'
                    }
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted text-[10px]">{t('goldEtf.aum', 'AUM')}</span>
                  <span className="text-text-primary text-[10px] font-semibold tabular-nums">
                    {etf.aum != null ? `$${formatNumber(etf.aum)}` : '--'}
                  </span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

async function fetchETFData() {
  const res = await fetch(`${import.meta.env.VITE_API_URL || '/api'}/gold-etf/latest`)
  if (!res.ok) throw new Error(`ETF API error: ${res.status}`)
  return res.json()
}
