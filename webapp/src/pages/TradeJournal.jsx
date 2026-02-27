import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatPricePrecise, formatPercent, formatDate, formatTime } from '../utils/format'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

const POLL_INTERVAL = 120_000

const EMOTIONS = ['confident', 'fearful', 'greedy', 'neutral', 'anxious']
const RATINGS = [1, 2, 3, 4, 5]

const defaultForm = {
  direction: 'buy',
  symbol: 'XAUUSD',
  open_price: '',
  exit_price: '',
  lot_size: '',
  pnl: '',
  notes: '',
  emotion: 'neutral',
  self_rating: 3,
  status: 'open',
}

export default function TradeJournal() {
  const { t } = useTranslation()
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ ...defaultForm })
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const result = await api.getJournalEntries()
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

  const handleFormChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const body = {
        ...form,
        open_price: form.open_price ? parseFloat(form.open_price) : null,
        exit_price: form.exit_price ? parseFloat(form.exit_price) : null,
        lot_size: form.lot_size ? parseFloat(form.lot_size) : null,
        pnl: form.pnl ? parseFloat(form.pnl) : null,
        self_rating: parseInt(form.self_rating, 10),
      }
      await api.createJournalEntry(body)
      setForm({ ...defaultForm })
      setShowForm(false)
      await fetchData()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm(t('journal.deleteConfirm', 'Delete this trade?'))) return
    setDeleting(id)
    try {
      await api.deleteJournalEntry(id)
      await fetchData()
    } catch (err) {
      setError(err.message)
    } finally {
      setDeleting(null)
    }
  }

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
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-shimmer-gold">{t('journal.pageTitle', 'Trade Journal')}</h1>
        <button
          onClick={() => setShowForm((prev) => !prev)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-accent-gold/10 text-accent-gold border border-accent-gold/20 hover:bg-accent-gold/20 transition-colors"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
            {showForm ? <path d="M18 6L6 18M6 6l12 12" /> : <><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></>}
          </svg>
          {t('journal.newTrade', 'New Trade')}
        </button>
      </div>

      {error && (
        <div className="bg-bg-card rounded-2xl p-3 border border-accent-red/20">
          <p className="text-accent-red text-xs">{error}</p>
          <button onClick={fetchData} className="text-accent-gold text-xs mt-1 underline">
            {t('common:app.retry', 'Retry')}
          </button>
        </div>
      )}

      {/* New Trade Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-bg-card rounded-2xl p-4 border border-accent-gold/20 space-y-3 slide-up">
          <h4 className="text-text-primary text-sm font-semibold">{t('journal.newTrade', 'New Trade')}</h4>

          {/* Direction + Symbol row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-text-muted text-[10px] block mb-1">{t('journal.direction', 'Direction')}</label>
              <div className="flex gap-1">
                {['buy', 'sell'].map((dir) => (
                  <button
                    key={dir}
                    type="button"
                    onClick={() => handleFormChange('direction', dir)}
                    className={`flex-1 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                      form.direction === dir
                        ? dir === 'buy'
                          ? 'bg-accent-green/20 text-accent-green border border-accent-green/30'
                          : 'bg-accent-red/20 text-accent-red border border-accent-red/30'
                        : 'bg-bg-hover text-text-muted border border-white/5'
                    }`}
                  >
                    {dir.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-text-muted text-[10px] block mb-1">{t('journal.symbol', 'Symbol')}</label>
              <input
                type="text"
                value={form.symbol}
                onChange={(e) => handleFormChange('symbol', e.target.value)}
                className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-1.5 text-text-primary text-xs outline-none focus:border-accent-gold/30"
              />
            </div>
          </div>

          {/* Price row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-text-muted text-[10px] block mb-1">{t('journal.openPrice', 'Open Price')}</label>
              <input
                type="number"
                step="0.01"
                value={form.open_price}
                onChange={(e) => handleFormChange('open_price', e.target.value)}
                placeholder="0.00"
                className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-1.5 text-text-primary text-xs outline-none focus:border-accent-gold/30 tabular-nums"
              />
            </div>
            <div>
              <label className="text-text-muted text-[10px] block mb-1">{t('journal.exitPrice', 'Exit Price')}</label>
              <input
                type="number"
                step="0.01"
                value={form.exit_price}
                onChange={(e) => handleFormChange('exit_price', e.target.value)}
                placeholder="0.00"
                className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-1.5 text-text-primary text-xs outline-none focus:border-accent-gold/30 tabular-nums"
              />
            </div>
          </div>

          {/* Lot size + PnL */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-text-muted text-[10px] block mb-1">{t('journal.lotSize', 'Lot Size')}</label>
              <input
                type="number"
                step="0.01"
                value={form.lot_size}
                onChange={(e) => handleFormChange('lot_size', e.target.value)}
                placeholder="0.01"
                className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-1.5 text-text-primary text-xs outline-none focus:border-accent-gold/30 tabular-nums"
              />
            </div>
            <div>
              <label className="text-text-muted text-[10px] block mb-1">{t('journal.pnl', 'P&L')}</label>
              <input
                type="number"
                step="0.01"
                value={form.pnl}
                onChange={(e) => handleFormChange('pnl', e.target.value)}
                placeholder="0.00"
                className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-1.5 text-text-primary text-xs outline-none focus:border-accent-gold/30 tabular-nums"
              />
            </div>
          </div>

          {/* Emotion + Rating + Status */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-text-muted text-[10px] block mb-1">{t('journal.emotion', 'Emotion')}</label>
              <select
                value={form.emotion}
                onChange={(e) => handleFormChange('emotion', e.target.value)}
                className="w-full bg-bg-hover border border-white/10 rounded-lg px-2 py-1.5 text-text-primary text-xs outline-none focus:border-accent-gold/30"
              >
                {EMOTIONS.map((em) => (
                  <option key={em} value={em}>{em.charAt(0).toUpperCase() + em.slice(1)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-text-muted text-[10px] block mb-1">{t('journal.rating', 'Self Rating')}</label>
              <select
                value={form.self_rating}
                onChange={(e) => handleFormChange('self_rating', e.target.value)}
                className="w-full bg-bg-hover border border-white/10 rounded-lg px-2 py-1.5 text-text-primary text-xs outline-none focus:border-accent-gold/30"
              >
                {RATINGS.map((r) => (
                  <option key={r} value={r}>{r}/5</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-text-muted text-[10px] block mb-1">{t('journal.status', 'Status')}</label>
              <select
                value={form.status}
                onChange={(e) => handleFormChange('status', e.target.value)}
                className="w-full bg-bg-hover border border-white/10 rounded-lg px-2 py-1.5 text-text-primary text-xs outline-none focus:border-accent-gold/30"
              >
                <option value="open">Open</option>
                <option value="closed">Closed</option>
              </select>
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="text-text-muted text-[10px] block mb-1">{t('journal.notes', 'Notes')}</label>
            <textarea
              value={form.notes}
              onChange={(e) => handleFormChange('notes', e.target.value)}
              rows={2}
              placeholder={t('journal.notes', 'Notes')}
              className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-1.5 text-text-primary text-xs outline-none focus:border-accent-gold/30 resize-none"
            />
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={saving}
            className="w-full py-2 rounded-xl text-sm font-bold text-white bg-accent-gold disabled:opacity-50 active:scale-95 transition-all"
          >
            {saving ? t('journal.saving', 'Saving...') : t('journal.save', 'Save Trade')}
          </button>
        </form>
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
              const entryId = entry.id ?? idx

              return (
                <div
                  key={entryId}
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
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-bold tabular-nums ${
                        pnl > 0 ? 'text-accent-green' : pnl < 0 ? 'text-accent-red' : 'text-text-muted'
                      }`}>
                        {pnl > 0 ? '+' : ''}{formatPricePrecise(pnl)}
                      </span>
                      {entry.id != null && (
                        <button
                          onClick={() => handleDelete(entry.id)}
                          disabled={deleting === entry.id}
                          className="p-1 rounded hover:bg-accent-red/10 transition-colors disabled:opacity-50"
                          title={t('journal.deleteConfirm', 'Delete this trade?')}
                        >
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5 text-accent-red/60 hover:text-accent-red">
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-3 mt-1 text-text-muted text-[10px]">
                    {entry.open_price && <span>Entry: {formatPricePrecise(entry.open_price)}</span>}
                    {entry.exit_price && <span>Exit: {formatPricePrecise(entry.exit_price)}</span>}
                    {entry.lot_size && <span>{entry.lot_size} lot</span>}
                    {(entry.close_date || entry.date) && <span>{formatDate(entry.close_date || entry.date)}</span>}
                  </div>

                  {(entry.emotion || entry.self_rating) && (
                    <div className="flex items-center gap-2 mt-1 text-[10px]">
                      {entry.emotion && (
                        <span className="text-text-muted bg-bg-hover rounded px-1.5 py-0.5">
                          {entry.emotion}
                        </span>
                      )}
                      {entry.self_rating && (
                        <span className="text-accent-goldBright">
                          {'★'.repeat(entry.self_rating)}{'☆'.repeat(5 - entry.self_rating)}
                        </span>
                      )}
                    </div>
                  )}

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

