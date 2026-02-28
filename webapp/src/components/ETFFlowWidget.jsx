import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { safeFixed } from '../utils/format'
import { api } from '../utils/api'

const ETF_NAMES = ['GLD', 'IAU', 'SGOL', 'GLDM']

export default function ETFFlowWidget({ flows }) {
  const { t } = useTranslation()
  const [fetched, setFetched] = useState(null)
  const [loading, setLoading] = useState(!flows)

  // Self-fetch when used standalone (no flows prop)
  useEffect(() => {
    if (flows) return
    api.getGoldETFLatest()
      .then((data) => setFetched(data?.etfs || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [flows])

  if (loading) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
        <div className="h-4 w-28 bg-bg-hover rounded mb-3" />
        <div className="h-24 bg-bg-hover rounded" />
      </div>
    )
  }

  const etfData = flows || fetched || []

  const chartData = ETF_NAMES.map((name) => {
    const etf = etfData.find((f) => f.ticker === name || f.name === name)
    return {
      name,
      flow: etf?.daily_flow ?? etf?.net_flow ?? 0,
    }
  })

  const hasData = chartData.some((d) => d.flow !== 0)

  if (!hasData) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h4 className="text-text-primary text-xs font-semibold mb-2">
          {t('etfFlow.title', 'ETF Daily Flows')}
        </h4>
        <p className="text-text-muted text-xs">{t('common:app.noData', 'No data available')}</p>
      </div>
    )
  }

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <h4 className="text-text-primary text-xs font-semibold mb-3">
        {t('etfFlow.title', 'ETF Daily Flows')}
      </h4>
      <ResponsiveContainer width="100%" height={140}>
        <BarChart data={chartData} barSize={24}>
          <XAxis
            dataKey="name"
            tick={{ fill: '#999', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: '#999', fontSize: 9 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => v != null && isFinite(v) ? `${v > 0 ? '+' : ''}${safeFixed(v, 0)}` : '--'}
          />
          <Tooltip
            contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
            formatter={(value) => [value != null && isFinite(value) ? `${value > 0 ? '+' : ''}${safeFixed(value, 1)} tonnes` : '--', t('etfFlow.flow', 'Flow')]}
          />
          <Bar dataKey="flow" radius={[3, 3, 0, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.flow >= 0 ? '#22c55e' : '#ef4444'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
