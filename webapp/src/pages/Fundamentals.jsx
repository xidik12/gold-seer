import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Legend, Cell,
} from 'recharts'
import { safeFixed } from '../utils/format'

const DEMAND_KEYS = ['jewellery', 'investment', 'central_banks', 'technology']
const DEMAND_COLORS = { jewellery: '#f59e0b', investment: '#3b82f6', central_banks: '#8b5cf6', technology: '#10b981' }
const SUPPLY_KEYS = ['mine_production', 'recycled']

function FundamentalsSkeleton({ t }) {
  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <div>
        <h1 className="text-lg font-bold text-shimmer-gold">{t('fundamentals.pageTitle')}</h1>
        <p className="text-text-muted text-xs mt-0.5">{t('fundamentals.subtitle')}</p>
      </div>
      <div className="bg-bg-card rounded-2xl p-5 border border-white/5 animate-pulse">
        <div className="h-4 w-40 bg-bg-hover rounded mb-3" />
        <div className="grid grid-cols-3 gap-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="bg-bg-secondary rounded-xl p-3">
              <div className="h-3 w-16 bg-bg-hover rounded mb-2" />
              <div className="h-6 w-20 bg-bg-hover rounded" />
            </div>
          ))}
        </div>
      </div>
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
        <div className="h-4 w-48 bg-bg-hover rounded mb-3" />
        <div className="h-48 bg-bg-hover rounded" />
      </div>
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
        <div className="h-4 w-48 bg-bg-hover rounded mb-3" />
        <div className="h-48 bg-bg-hover rounded" />
      </div>
    </div>
  )
}

export default function Fundamentals() {
  const { t } = useTranslation('common')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const result = await api.getSupplyDemand()
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

  if (loading) return <FundamentalsSkeleton t={t} />

  const quarters = data?.quarters || data?.data || []
  const latest = quarters.length > 0 ? quarters[quarters.length - 1] : null

  const totalDemand = latest
    ? (latest.jewellery || 0) + (latest.investment || 0) + (latest.central_banks || 0) + (latest.technology || 0)
    : 0
  const totalSupply = latest
    ? (latest.mine_production || 0) + (latest.recycled || 0)
    : 0
  const balance = totalSupply - totalDemand

  // Demand breakdown stacked bar chart data
  const demandChartData = quarters.map((q) => ({
    quarter: q.quarter || q.period || q.label,
    [t('fundamentals.jewellery')]: q.jewellery || 0,
    [t('fundamentals.investment')]: q.investment || 0,
    [t('fundamentals.centralBanks')]: q.central_banks || 0,
    [t('fundamentals.technology')]: q.technology || 0,
  }))

  // Supply vs Demand balance chart
  const balanceChartData = quarters.map((q) => {
    const qDemand = (q.jewellery || 0) + (q.investment || 0) + (q.central_banks || 0) + (q.technology || 0)
    const qSupply = (q.mine_production || 0) + (q.recycled || 0)
    return {
      quarter: q.quarter || q.period || q.label,
      [t('fundamentals.supply')]: qSupply,
      [t('fundamentals.demand')]: qDemand,
      balance: qSupply - qDemand,
    }
  })

  const demandKeyLabels = {
    jewellery: t('fundamentals.jewellery'),
    investment: t('fundamentals.investment'),
    central_banks: t('fundamentals.centralBanks'),
    technology: t('fundamentals.technology'),
  }

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <div>
        <h1 className="text-lg font-bold text-shimmer-gold">{t('fundamentals.pageTitle')}</h1>
        <p className="text-text-muted text-xs mt-0.5">{t('fundamentals.subtitle')}</p>
      </div>

      {error && (
        <div className="bg-bg-card rounded-2xl p-3 border border-accent-red/20">
          <p className="text-accent-red text-xs">{error}</p>
          <button onClick={fetchData} className="text-accent-gold text-xs mt-1 underline">
            {t('app.retry')}
          </button>
        </div>
      )}

      {/* Latest Quarter Summary */}
      {latest && (
        <div className="bg-bg-card rounded-2xl p-5 border border-accent-gold/15 slide-up">
          <p className="text-text-muted text-[10px] uppercase tracking-wider font-medium mb-3">
            {latest.quarter || latest.period || 'Latest Quarter'}
          </p>
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-bg-secondary rounded-xl p-3 text-center">
              <p className="text-text-muted text-[10px] mb-1">{t('fundamentals.demand')}</p>
              <p className="text-lg font-bold text-accent-goldBright tabular-nums">{safeFixed(totalDemand, 0)}</p>
              <p className="text-text-muted text-[8px]">tonnes</p>
            </div>
            <div className="bg-bg-secondary rounded-xl p-3 text-center">
              <p className="text-text-muted text-[10px] mb-1">{t('fundamentals.supply')}</p>
              <p className="text-lg font-bold text-accent-goldBright tabular-nums">{safeFixed(totalSupply, 0)}</p>
              <p className="text-text-muted text-[8px]">tonnes</p>
            </div>
            <div className="bg-bg-secondary rounded-xl p-3 text-center">
              <p className="text-text-muted text-[10px] mb-1">
                {balance >= 0 ? t('fundamentals.surplus') : t('fundamentals.deficit')}
              </p>
              <p className={`text-lg font-bold tabular-nums ${balance >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                {balance >= 0 ? '+' : ''}{safeFixed(balance, 0)}
              </p>
              <p className="text-text-muted text-[8px]">tonnes</p>
            </div>
          </div>
        </div>
      )}

      {/* Demand Breakdown Stacked Bar Chart */}
      {demandChartData.length > 0 && (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up" style={{ animationDelay: '50ms' }}>
          <h4 className="text-text-primary text-xs font-semibold mb-3">
            {t('fundamentals.demand')} — {t('fundamentals.pageTitle')}
          </h4>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={demandChartData} barSize={20}>
              <XAxis
                dataKey="quarter"
                tick={{ fill: '#999', fontSize: 9 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: '#999', fontSize: 9 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => v != null && isFinite(v) ? safeFixed(v, 0) : '--'}
              />
              <Tooltip
                contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
                formatter={(value, name) => [value != null && isFinite(value) ? `${safeFixed(value, 1)} t` : '--', name]}
              />
              <Legend wrapperStyle={{ fontSize: 10 }} />
              <Bar dataKey={t('fundamentals.jewellery')} stackId="demand" fill="#f59e0b" radius={[0, 0, 0, 0]} />
              <Bar dataKey={t('fundamentals.investment')} stackId="demand" fill="#3b82f6" radius={[0, 0, 0, 0]} />
              <Bar dataKey={t('fundamentals.centralBanks')} stackId="demand" fill="#8b5cf6" radius={[0, 0, 0, 0]} />
              <Bar dataKey={t('fundamentals.technology')} stackId="demand" fill="#10b981" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Supply vs Demand Balance Chart */}
      {balanceChartData.length > 0 && (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up" style={{ animationDelay: '100ms' }}>
          <h4 className="text-text-primary text-xs font-semibold mb-3">
            {t('fundamentals.supply')} vs {t('fundamentals.demand')}
          </h4>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={balanceChartData} barSize={14}>
              <XAxis
                dataKey="quarter"
                tick={{ fill: '#999', fontSize: 9 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: '#999', fontSize: 9 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => v != null && isFinite(v) ? safeFixed(v, 0) : '--'}
              />
              <Tooltip
                contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
                formatter={(value, name) => [value != null && isFinite(value) ? `${safeFixed(value, 1)} t` : '--', name]}
              />
              <Legend wrapperStyle={{ fontSize: 10 }} />
              <Bar dataKey={t('fundamentals.supply')} fill="#22c55e" radius={[3, 3, 0, 0]} />
              <Bar dataKey={t('fundamentals.demand')} fill="#ef4444" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>

          {/* Balance row */}
          <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
            {balanceChartData.map((q, i) => (
              <div key={i} className="bg-bg-secondary rounded-lg px-2.5 py-1.5 shrink-0 text-center min-w-[70px]">
                <p className="text-text-muted text-[8px]">{q.quarter}</p>
                <p className={`text-xs font-bold tabular-nums ${q.balance >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                  {q.balance >= 0 ? '+' : ''}{safeFixed(q.balance, 0)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {!latest && !error && (
        <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
          <p className="text-text-muted text-xs">{t('app.noData')}</p>
        </div>
      )}
    </div>
  )
}
