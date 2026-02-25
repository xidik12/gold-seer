import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatPricePrecise, formatPercent, formatDate, formatTime } from '../utils/format'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

const POLL_INTERVAL = 120_000

export default function TradeJournal() {
  const { t } = useTranslation()
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const result = await fetchJournalEntries()
      setEntries(result?.entries || result || [])
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

  // Compute stats
  const closed = entries.filter((e) => e.status === 'closed' || e.exit_price != null)
  const wins = closed.filter((e) => (e.pnl ?? e.profit ?? 0) > 0)
  const winRate = closed.length > 0 ? (wins.length / closed.length) * 100 : 0
  const totalPnl = closed.reduce((sum, e) => sum + (e.pnl ?? e.profit ?? 0), 0)
  const avgPnl = closed.length > 0 ? totalPnl / closed.length : 0

  // Equity curve data
  let runningEquity = 0
  const equityCurve = closed.map((e, i) => {
    runningEquity += (e.pnl ?? e.profit ?? 0)
    return {
      trade: i + 1,
      equity: runningEquity,
      date: e.close_date || e.exit_date || e.date || '',
    }
  })

  if (loading) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold text-shimmer-gold">{t('journal.pageTitle', 'Trade Journal')}</h1>
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
            <div className="h-5 w-32 bg-bg-hover rounded mb-3" />
            <div className="h-16 bg-bg-hover rounded" />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <h1 className="text-lg font-bold text-shimmer-gold">{t('journal.pageTitle', 'Trade Journal')}</h1>

      {error && (
        <div className="bg-bg-card rounded-2xl p-3 border border-accent-red/20">
          <p className="text-accent-red text-xs">{error}</p>
          <button onClick={fetchData} className="text-accent-gold text-xs mt-1 underline">
            {t('common:app.retry', 'Retry')}
          </button>
        </div>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-2">
        {[
          { label: t('journal.totalPnl', 'Total P&L'), value: formatPricePrecise(totalPnl), color: totalPnl >= 0 ? 'text-accent-green' : 'text-accent-red' },
          { label: t('journal.winRate', 'Win Rate'), value: `${winRate.toFixed(1)}%`, color: winRate >= 50 ? 'text-accent-green' : 'text-accent-red' },
          { label: t('journal.avgPnl', 'Avg P&L'), value: formatPricePrecise(avgPnl), color: avgPnl >= 0 ? 'text-accent-green' : 'text-accent-red' },
          { label: t('journal.trades', 'Trades'), value: String(closed.length), color: 'text-accent-goldBright' },
        ].map((stat) => (
          <div key={stat.label} className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
            <p className="text-text-muted text-[9px] mb-0.5">{stat.label}</p>
            <p className={`text-sm font-bold tabular-nums ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Equity Curve */}
      {equityCurve.length > 1 && (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
          <h4 className="text-text-primary text-sm font-semibold mb-3">
            {t('journal.equityCurve', 'Equity Curve')}
          </h4>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={equityCurve}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="trade"
                tick={{ fill: '#999', fontSize: 9 }}
                axisLine={false}
                tickLine={false}
                label={{ value: t('journal.tradeNum', 'Trade #'), position: 'insideBottom', offset: -5, fill: '#666', fontSize: 9 }}
              />
              <YAxis
                tick={{ fill: '#999', fontSize: 9 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `$${v.toFixed(0)}`}
              />
              <Tooltip
                contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
                formatter={(value) => [`$${value.toFixed(2)}`, t('journal.equity', 'Equity')]}
              />
              <Line
                type="monotone"
                dataKey="equity"
                stroke="#D4AF37"
                strokeWidth={2}
                dot={false}
                name={t('journal.equity', 'Equity')}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Trade list */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h4 className="text-text-primary text-sm font-semibold mb-3">
          {t('journal.recentTrades', 'Recent Trades')}
        </h4>
        {entries.length === 0 ? (
          <p className="text-text-muted text-xs">{t('journal.noTrades', 'No journal entries yet')}</p>
        ) : (
          <div className="space-y-2">
            {entries.slice(0, 50).map((entry, idx) => {
              const pnl = entry.pnl ?? entry.profit ?? 0
              const isWin = pnl > 0
              const direction = entry.direction || entry.type || 'buy'

              return (
                <div
                  key={entry.id ?? idx}
                  className="bg-bg-secondary/50 rounded-lg px-3 py-2.5 border-l-2"
                  style={{ borderLeftColor: isWin ? '#22c55e' : pnl < 0 ? '#ef4444' : '#D4AF37' }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        direction === 'buy' || direction === 'long'
                          ? 'bg-accent-green/10 text-accent-green'
                          : 'bg-accent-red/10 text-accent-red'
                      }`}>
                        {direction.toUpperCase()}
                      </span>
                      <span className="text-text-primary text-xs font-medium">{entry.symbol || 'XAUUSD'}</span>
                    </div>
                    <span className={`text-sm font-bold tabular-nums ${
                      pnl > 0 ? 'text-accent-green' : pnl < 0 ? 'text-accent-red' : 'text-text-muted'
                    }`}>
                      {pnl > 0 ? '+' : ''}{formatPricePrecise(pnl)}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 mt-1 text-text-muted text-[10px]">
                    {entry.open_price && <span>Entry: {formatPricePrecise(entry.open_price)}</span>}
                    {entry.exit_price && <span>Exit: {formatPricePrecise(entry.exit_price)}</span>}
                    {entry.lot_size && <span>{entry.lot_size} lot</span>}
                    {(entry.close_date || entry.date) && <span>{formatDate(entry.close_date || entry.date)}</span>}
                  </div>

                  {entry.notes && (
                    <p className="text-text-muted text-[10px] mt-1 italic border-t border-white/5 pt-1">
                      {entry.notes}
                    </p>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

async function fetchJournalEntries() {
  const res = await fetch(`${import.meta.env.VITE_API_URL || '/api'}/trade-journal/entries`)
  if (!res.ok) throw new Error(`Journal API error: ${res.status}`)
  return res.json()
}
