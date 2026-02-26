import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { safeFixed } from '../utils/format'

const TABS = ['trades', 'leaderboard']

function CommunitySkeleton({ t }) {
  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <div>
        <h1 className="text-lg font-bold text-shimmer-gold">{t('community.pageTitle')}</h1>
        <p className="text-text-muted text-xs mt-0.5">{t('community.subtitle')}</p>
      </div>
      <div className="flex gap-2">
        <div className="h-8 w-24 bg-bg-hover rounded-full animate-pulse" />
        <div className="h-8 w-28 bg-bg-hover rounded-full animate-pulse" />
      </div>
      {[1, 2, 3].map((i) => (
        <div key={i} className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
          <div className="h-4 w-32 bg-bg-hover rounded mb-3" />
          <div className="h-6 w-24 bg-bg-hover rounded mb-2" />
          <div className="h-3 w-full bg-bg-hover rounded" />
        </div>
      ))}
    </div>
  )
}

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diff = now - then
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  return `${d}d ago`
}

export default function Community() {
  const { t } = useTranslation('common')
  const [tab, setTab] = useState('trades')
  const [trades, setTrades] = useState([])
  const [leaderboard, setLeaderboard] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Share form state
  const [showForm, setShowForm] = useState(false)
  const [formDirection, setFormDirection] = useState('long')
  const [formEntry, setFormEntry] = useState('')
  const [formTarget, setFormTarget] = useState('')
  const [formStopLoss, setFormStopLoss] = useState('')
  const [formReasoning, setFormReasoning] = useState('')
  const [sharing, setSharing] = useState(false)

  const fetchTrades = useCallback(async () => {
    try {
      const result = await api.getCommunityTrades()
      setTrades(result?.trades || result || [])
    } catch (err) {
      setError(err.message)
    }
  }, [])

  const fetchLeaderboard = useCallback(async () => {
    try {
      const result = await api.getCommunityLeaderboard()
      setLeaderboard(result?.leaderboard || result?.users || result || [])
    } catch (err) {
      setError(err.message)
    }
  }, [])

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      await Promise.all([fetchTrades(), fetchLeaderboard()])
      setLoading(false)
    }
    load()
  }, [fetchTrades, fetchLeaderboard])

  const handleShare = useCallback(async () => {
    if (!formEntry) return
    try {
      setSharing(true)
      await api.shareTrade({
        direction: formDirection,
        entry_price: parseFloat(formEntry),
        target_price: formTarget ? parseFloat(formTarget) : undefined,
        stop_loss: formStopLoss ? parseFloat(formStopLoss) : undefined,
        reasoning: formReasoning || undefined,
      })
      setShowForm(false)
      setFormEntry('')
      setFormTarget('')
      setFormStopLoss('')
      setFormReasoning('')
      // Refresh trades
      await fetchTrades()
    } catch (err) {
      setError(err.message)
    } finally {
      setSharing(false)
    }
  }, [formDirection, formEntry, formTarget, formStopLoss, formReasoning, fetchTrades])

  const handleLike = useCallback(async (tradeId) => {
    try {
      await api.likeTrade(tradeId)
      // Optimistic update
      setTrades((prev) =>
        prev.map((tr) =>
          (tr.id === tradeId)
            ? { ...tr, likes: (tr.likes || 0) + 1 }
            : tr
        )
      )
    } catch {
      // silently ignore
    }
  }, [])

  if (loading) return <CommunitySkeleton t={t} />

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <div>
        <h1 className="text-lg font-bold text-shimmer-gold">{t('community.pageTitle')}</h1>
        <p className="text-text-muted text-xs mt-0.5">{t('community.subtitle')}</p>
      </div>

      {error && (
        <div className="bg-bg-card rounded-2xl p-3 border border-accent-red/20">
          <p className="text-accent-red text-xs">{error}</p>
        </div>
      )}

      {/* Tab Bar */}
      <div className="flex gap-2">
        {TABS.map((tb) => (
          <button
            key={tb}
            onClick={() => setTab(tb)}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all ${
              tab === tb
                ? 'bg-accent-gold/20 text-accent-goldBright border border-accent-gold/30'
                : 'bg-bg-card text-text-muted border border-white/5 hover:border-white/10'
            }`}
          >
            {tb === 'trades' ? t('community.trades') : t('community.leaderboard')}
          </button>
        ))}
      </div>

      {/* ─── Trades Tab ─── */}
      {tab === 'trades' && (
        <div className="space-y-3">
          {/* Share Trade Button */}
          {!showForm && (
            <button
              onClick={() => setShowForm(true)}
              className="w-full py-2.5 rounded-xl text-sm font-bold text-white bg-accent-gold/80 hover:bg-accent-gold active:scale-95 transition-all"
            >
              + {t('community.shareTrade')}
            </button>
          )}

          {/* Share Form */}
          {showForm && (
            <div className="bg-bg-card rounded-2xl p-4 border border-accent-gold/20 space-y-3 slide-up">
              <h4 className="text-text-primary text-sm font-semibold">{t('community.shareTrade')}</h4>

              {/* Direction */}
              <div>
                <label className="text-text-muted text-[10px] uppercase tracking-wider font-medium block mb-1">
                  {t('community.direction')}
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setFormDirection('long')}
                    className={`py-2 rounded-xl text-xs font-bold transition-all ${
                      formDirection === 'long'
                        ? 'bg-accent-green/20 text-accent-green border border-accent-green/30'
                        : 'bg-bg-secondary text-text-muted border border-white/5'
                    }`}
                  >
                    LONG
                  </button>
                  <button
                    onClick={() => setFormDirection('short')}
                    className={`py-2 rounded-xl text-xs font-bold transition-all ${
                      formDirection === 'short'
                        ? 'bg-accent-red/20 text-accent-red border border-accent-red/30'
                        : 'bg-bg-secondary text-text-muted border border-white/5'
                    }`}
                  >
                    SHORT
                  </button>
                </div>
              </div>

              {/* Entry Price */}
              <div>
                <label className="text-text-muted text-[10px] uppercase tracking-wider font-medium block mb-1">
                  {t('community.entryPrice')}
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={formEntry}
                  onChange={(e) => setFormEntry(e.target.value)}
                  placeholder="2650.00"
                  className="w-full bg-bg-secondary text-text-primary text-sm rounded-xl px-3 py-2.5 border border-white/10 focus:border-accent-gold/40 focus:outline-none"
                />
              </div>

              {/* Target & Stop Loss */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-text-muted text-[10px] uppercase tracking-wider font-medium block mb-1">
                    {t('community.targetPrice')}
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={formTarget}
                    onChange={(e) => setFormTarget(e.target.value)}
                    placeholder="2700.00"
                    className="w-full bg-bg-secondary text-text-primary text-sm rounded-xl px-3 py-2.5 border border-white/10 focus:border-accent-gold/40 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-text-muted text-[10px] uppercase tracking-wider font-medium block mb-1">
                    {t('community.stopLoss')}
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={formStopLoss}
                    onChange={(e) => setFormStopLoss(e.target.value)}
                    placeholder="2620.00"
                    className="w-full bg-bg-secondary text-text-primary text-sm rounded-xl px-3 py-2.5 border border-white/10 focus:border-accent-gold/40 focus:outline-none"
                  />
                </div>
              </div>

              {/* Reasoning */}
              <div>
                <label className="text-text-muted text-[10px] uppercase tracking-wider font-medium block mb-1">
                  {t('community.reasoning')}
                </label>
                <textarea
                  rows={3}
                  value={formReasoning}
                  onChange={(e) => setFormReasoning(e.target.value)}
                  placeholder="Why are you taking this trade?"
                  className="w-full bg-bg-secondary text-text-primary text-sm rounded-xl px-3 py-2.5 border border-white/10 focus:border-accent-gold/40 focus:outline-none resize-none"
                />
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                <button
                  onClick={() => setShowForm(false)}
                  className="flex-1 py-2.5 rounded-xl text-sm font-medium text-text-muted bg-bg-secondary border border-white/5"
                >
                  {t('btn.cancel')}
                </button>
                <button
                  onClick={handleShare}
                  disabled={sharing || !formEntry}
                  className="flex-1 py-2.5 rounded-xl text-sm font-bold text-white bg-accent-gold disabled:opacity-50 active:scale-95 transition-all"
                >
                  {sharing ? t('community.sharing') : t('community.share')}
                </button>
              </div>
            </div>
          )}

          {/* Trade Feed */}
          {trades.length === 0 ? (
            <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
              <p className="text-text-muted text-xs">{t('community.noTrades')}</p>
            </div>
          ) : (
            trades.map((trade, i) => {
              const isLong = (trade.direction || '').toLowerCase() === 'long' || (trade.direction || '').toLowerCase() === 'buy'
              const pnl = trade.pnl ?? trade.profit ?? null
              return (
                <div
                  key={trade.id ?? i}
                  className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up"
                  style={{ animationDelay: `${i * 30}ms` }}
                >
                  {/* Header */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-text-primary text-xs font-semibold">
                        {trade.username || trade.user || 'Anonymous'}
                      </span>
                      <span className="text-text-muted text-[9px]">
                        {timeAgo(trade.created_at || trade.timestamp)}
                      </span>
                    </div>
                    <span
                      className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${
                        isLong
                          ? 'bg-accent-green/10 text-accent-green'
                          : 'bg-accent-red/10 text-accent-red'
                      }`}
                    >
                      {isLong ? 'LONG' : 'SHORT'}
                    </span>
                  </div>

                  {/* Prices */}
                  <div className="flex gap-3 text-[10px] mb-2">
                    <div>
                      <span className="text-text-muted">{t('community.entryPrice')}: </span>
                      <span className="text-text-primary font-semibold tabular-nums">
                        ${safeFixed(trade.entry_price, 2)}
                      </span>
                    </div>
                    {trade.target_price != null && (
                      <div>
                        <span className="text-text-muted">{t('community.targetPrice')}: </span>
                        <span className="text-accent-green font-semibold tabular-nums">
                          ${safeFixed(trade.target_price, 2)}
                        </span>
                      </div>
                    )}
                    {trade.stop_loss != null && (
                      <div>
                        <span className="text-text-muted">SL: </span>
                        <span className="text-accent-red font-semibold tabular-nums">
                          ${safeFixed(trade.stop_loss, 2)}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* PnL if closed */}
                  {pnl != null && (
                    <div className="mb-2">
                      <span className={`text-xs font-bold tabular-nums ${pnl >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                        P&L: {pnl >= 0 ? '+' : ''}${safeFixed(pnl, 2)}
                      </span>
                    </div>
                  )}

                  {/* Reasoning */}
                  {trade.reasoning && (
                    <p className="text-text-muted text-[10px] leading-relaxed border-t border-white/5 pt-2 line-clamp-3">
                      {trade.reasoning}
                    </p>
                  )}

                  {/* Like Button */}
                  <div className="flex items-center gap-2 mt-2 pt-2 border-t border-white/5">
                    <button
                      onClick={() => handleLike(trade.id)}
                      className="flex items-center gap-1 text-text-muted hover:text-accent-gold transition-colors"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
                        <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z" />
                      </svg>
                      <span className="text-[10px] tabular-nums">{trade.likes || 0}</span>
                    </button>
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}

      {/* ─── Leaderboard Tab ─── */}
      {tab === 'leaderboard' && (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
          {leaderboard.length === 0 ? (
            <p className="text-text-muted text-xs text-center py-4">{t('app.noData')}</p>
          ) : (
            <div className="space-y-1">
              {/* Header */}
              <div className="flex items-center gap-2 text-text-muted text-[9px] uppercase tracking-wider font-medium px-2 pb-2 border-b border-white/5">
                <span className="w-8 text-center">{t('community.rank')}</span>
                <span className="flex-1">{t('community.user')}</span>
                <span className="w-24 text-right">{t('community.totalPnl')}</span>
                <span className="w-14 text-right">{t('community.tradeCount')}</span>
              </div>
              {leaderboard.slice(0, 10).map((user, i) => {
                const pnl = user.total_pnl ?? user.pnl ?? 0
                const rank = user.rank ?? i + 1
                return (
                  <div
                    key={user.id ?? user.username ?? i}
                    className="flex items-center gap-2 px-2 py-2 rounded-lg hover:bg-bg-secondary transition-colors"
                  >
                    <span className={`w-8 text-center text-xs font-bold ${rank <= 3 ? 'text-accent-goldBright' : 'text-text-muted'}`}>
                      {rank <= 3 ? ['', '1st', '2nd', '3rd'][rank] : `#${rank}`}
                    </span>
                    <span className="flex-1 text-text-primary text-xs font-medium truncate">
                      {user.username || user.user || `User ${rank}`}
                    </span>
                    <span className={`w-24 text-right text-xs font-bold tabular-nums ${pnl >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                      {pnl >= 0 ? '+' : ''}${safeFixed(pnl, 2)}
                    </span>
                    <span className="w-14 text-right text-text-muted text-xs tabular-nums">
                      {user.trade_count ?? user.trades ?? 0}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
