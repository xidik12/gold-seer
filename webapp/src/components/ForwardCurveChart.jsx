import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceDot,
} from 'recharts'
import { safeFixed } from '../utils/format'

export default function ForwardCurveChart() {
  const { t } = useTranslation('common')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const result = await api.getForwardCurve()
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
  }, [fetchData])

  if (loading) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
        <div className="h-4 w-32 bg-bg-hover rounded mb-3" />
        <div className="h-36 bg-bg-hover rounded" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-accent-red/20">
        <h4 className="text-text-primary text-xs font-semibold mb-1">{t('forwardCurve.title')}</h4>
        <p className="text-accent-red text-xs">{error}</p>
        <button onClick={fetchData} className="text-accent-gold text-xs mt-1 underline">
          {t('app.retry')}
        </button>
      </div>
    )
  }

  const spotPrice = data?.spot ?? data?.spot_price ?? null
  const contracts = data?.forwards || data?.contracts || data?.forward_prices || data?.curve || []
  const structure = data?.curve_shape || data?.structure || data?.curve_type || null

  // Build chart data: spot first, then forward contracts
  const chartData = []
  if (spotPrice != null) {
    chartData.push({ label: 'Spot', price: spotPrice, month: 0 })
  }
  contracts.forEach((c, i) => {
    chartData.push({
      label: c.label || c.contract || c.expiry || `M+${i + 1}`,
      price: c.price ?? c.value ?? c.settle ?? 0,
      month: i + 1,
    })
  })

  const hasData = chartData.length > 1

  // Determine contango/backwardation
  const isContango = structure === 'contango' ||
    (chartData.length > 1 && chartData[chartData.length - 1].price > chartData[0].price)
  const isBackwardation = structure === 'backwardation' ||
    (chartData.length > 1 && chartData[chartData.length - 1].price < chartData[0].price)

  const spreadPct = chartData.length > 1 && chartData[0].price > 0
    ? ((chartData[chartData.length - 1].price - chartData[0].price) / chartData[0].price) * 100
    : 0

  if (!hasData) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h4 className="text-text-primary text-xs font-semibold mb-2">{t('forwardCurve.title')}</h4>
        <p className="text-text-muted text-xs">{t('app.noData')}</p>
      </div>
    )
  }

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-text-primary text-xs font-semibold">{t('forwardCurve.title')}</h4>
        <div className="flex items-center gap-2">
          {/* Contango / Backwardation badge */}
          <span
            className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${
              isContango
                ? 'bg-accent-green/10 text-accent-green'
                : isBackwardation
                ? 'bg-accent-red/10 text-accent-red'
                : 'bg-bg-hover text-text-muted'
            }`}
          >
            {isContango
              ? t('forwardCurve.contango')
              : isBackwardation
              ? t('forwardCurve.backwardation')
              : '--'}
          </span>
          {/* Spread percentage */}
          <span className={`text-[10px] font-semibold tabular-nums ${spreadPct >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
            {t('forwardCurve.spread')}: {spreadPct >= 0 ? '+' : ''}{safeFixed(spreadPct, 2)}%
          </span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={150}>
        <LineChart data={chartData}>
          <XAxis
            dataKey="label"
            tick={{ fill: '#999', fontSize: 9 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={['auto', 'auto']}
            tick={{ fill: '#999', fontSize: 9 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => v != null && isFinite(v) ? `$${safeFixed(v, 0)}` : '--'}
          />
          <Tooltip
            contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
            formatter={(value) => [value != null && isFinite(value) ? `$${safeFixed(value, 2)}` : '--', 'Price']}
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke="#d4a017"
            strokeWidth={2}
            dot={{ r: 3, fill: '#d4a017' }}
            activeDot={{ r: 5, fill: '#f5c842' }}
          />
          {/* Highlight spot price */}
          {spotPrice != null && (
            <ReferenceDot
              x="Spot"
              y={spotPrice}
              r={5}
              fill="#f5c842"
              stroke="#d4a017"
              strokeWidth={2}
            />
          )}
        </LineChart>
      </ResponsiveContainer>

      {/* Spot label */}
      {spotPrice != null && (
        <p className="text-text-muted text-[9px] text-center mt-1">
          Spot: <span className="text-accent-goldBright font-semibold">${safeFixed(spotPrice, 2)}</span>
        </p>
      )}
    </div>
  )
}
