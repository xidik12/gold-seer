import { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts'
import { safeFixed } from '../utils/format'

const STRATEGIES = [
  { value: 'ai_signals', labelKey: 'backtest.aiSignals' },
  { value: 'rsi_oversold', labelKey: 'backtest.rsiOversold' },
  { value: 'ma_cross', labelKey: 'backtest.maCross' },
]

function BacktestSkeleton({ t }) {
  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <div>
        <h1 className="text-lg font-bold text-shimmer-gold">{t('backtest.pageTitle')}</h1>
        <p className="text-text-muted text-xs mt-0.5">{t('backtest.subtitle')}</p>
      </div>
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse space-y-3">
        <div className="h-10 bg-bg-hover rounded" />
        <div className="h-10 bg-bg-hover rounded" />
        <div className="h-10 bg-bg-hover rounded" />
        <div className="h-10 bg-bg-hover rounded-xl" />
      </div>
    </div>
  )
}

export default function Backtest() {
  const { t } = useTranslation('common')
  const [strategy, setStrategy] = useState('ai_signals')
  const [startDays, setStartDays] = useState(90)
  const [initialBalance, setInitialBalance] = useState(10000)

  // Strategy-specific params
  const [rsiThreshold, setRsiThreshold] = useState(30)
  const [maFast, setMaFast] = useState(9)
  const [maSlow, setMaSlow] = useState(21)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [results, setResults] = useState(null)

  const runBacktest = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params = {
        strategy,
        start_days: startDays,
        initial_balance: initialBalance,
      }

      if (strategy === 'rsi_oversold') {
        params.rsi_threshold = rsiThreshold
      } else if (strategy === 'ma_cross') {
        params.ma_fast = maFast
        params.ma_slow = maSlow
      }

      const result = await api.runBacktest(params)
      setResults(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [strategy, startDays, initialBalance, rsiThreshold, maFast, maSlow])

  const equityCurve = results?.equity_curve || results?.equity || []
  const trades = results?.trades || results?.recent_trades || []
  const metrics = results?.metrics || results || {}

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <div>
        <h1 className="text-lg font-bold text-shimmer-gold">{t('backtest.pageTitle')}</h1>
        <p className="text-text-muted text-xs mt-0.5">{t('backtest.subtitle')}</p>
      </div>

      {/* Strategy Config Form */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 space-y-3 slide-up">
        {/* Strategy Selector */}
        <div>
          <label className="text-text-muted text-[10px] uppercase tracking-wider font-medium block mb-1">
            {t('backtest.strategy')}
          </label>
          <select
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            className="w-full bg-bg-secondary text-text-primary text-sm rounded-xl px-3 py-2.5 border border-white/10 focus:border-accent-gold/40 focus:outline-none"
          >
            {STRATEGIES.map((s) => (
              <option key={s.value} value={s.value}>
                {t(s.labelKey)}
              </option>
            ))}
          </select>
        </div>

        {/* Strategy-specific params */}
        {strategy === 'rsi_oversold' && (
          <div>
            <label className="text-text-muted text-[10px] uppercase tracking-wider font-medium block mb-1">
              RSI Threshold
            </label>
            <input
              type="number"
              min={10}
              max={50}
              value={rsiThreshold}
              onChange={(e) => setRsiThreshold(Number(e.target.value))}
              className="w-full bg-bg-secondary text-text-primary text-sm rounded-xl px-3 py-2.5 border border-white/10 focus:border-accent-gold/40 focus:outline-none"
            />
          </div>
        )}

        {strategy === 'ma_cross' && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-text-muted text-[10px] uppercase tracking-wider font-medium block mb-1">
                Fast MA
              </label>
              <input
                type="number"
                min={2}
                max={50}
                value={maFast}
                onChange={(e) => setMaFast(Number(e.target.value))}
                className="w-full bg-bg-secondary text-text-primary text-sm rounded-xl px-3 py-2.5 border border-white/10 focus:border-accent-gold/40 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-text-muted text-[10px] uppercase tracking-wider font-medium block mb-1">
                Slow MA
              </label>
              <input
                type="number"
                min={5}
                max={200}
                value={maSlow}
                onChange={(e) => setMaSlow(Number(e.target.value))}
                className="w-full bg-bg-secondary text-text-primary text-sm rounded-xl px-3 py-2.5 border border-white/10 focus:border-accent-gold/40 focus:outline-none"
              />
            </div>
          </div>
        )}

        {/* Period Slider */}
        <div>
          <label className="text-text-muted text-[10px] uppercase tracking-wider font-medium block mb-1">
            {t('backtest.startDays')}: <span className="text-accent-goldBright">{startDays}</span>
          </label>
          <input
            type="range"
            min={30}
            max={365}
            step={1}
            value={startDays}
            onChange={(e) => setStartDays(Number(e.target.value))}
            className="w-full accent-amber-500"
          />
          <div className="flex justify-between text-text-muted text-[8px] mt-0.5">
            <span>30d</span>
            <span>365d</span>
          </div>
        </div>

        {/* Initial Balance */}
        <div>
          <label className="text-text-muted text-[10px] uppercase tracking-wider font-medium block mb-1">
            {t('backtest.initialBalance')}
          </label>
          <input
            type="number"
            min={100}
            max={1000000}
            value={initialBalance}
            onChange={(e) => setInitialBalance(Number(e.target.value))}
            className="w-full bg-bg-secondary text-text-primary text-sm rounded-xl px-3 py-2.5 border border-white/10 focus:border-accent-gold/40 focus:outline-none"
          />
        </div>

        {/* Run Button */}
        <button
          onClick={runBacktest}
          disabled={loading}
          className="w-full py-3 rounded-xl text-sm font-bold text-white bg-accent-gold disabled:opacity-50 active:scale-95 transition-all"
        >
          {loading ? t('backtest.running') : t('backtest.run')}
        </button>
      </div>

      {error && (
        <div className="bg-bg-card rounded-2xl p-3 border border-accent-red/20">
          <p className="text-accent-red text-xs">{error}</p>
        </div>
      )}

      {/* Results */}
      {results && !loading && (
        <>
          {/* Key Metrics Row */}
          <div className="grid grid-cols-2 gap-3 slide-up">
            <MetricCard
              label={t('backtest.totalReturn')}
              value={`${safeFixed(metrics.total_return ?? metrics.total_return_pct, 2)}%`}
              positive={(metrics.total_return ?? metrics.total_return_pct ?? 0) >= 0}
            />
            <MetricCard
              label={t('backtest.winRate')}
              value={`${safeFixed(metrics.win_rate ?? metrics.win_rate_pct, 1)}%`}
              positive={(metrics.win_rate ?? metrics.win_rate_pct ?? 0) >= 50}
            />
            <MetricCard
              label={t('backtest.maxDrawdown')}
              value={`${safeFixed(metrics.max_drawdown ?? metrics.max_drawdown_pct, 2)}%`}
              positive={false}
            />
            <MetricCard
              label={t('backtest.sharpe')}
              value={safeFixed(metrics.sharpe_ratio ?? metrics.sharpe, 2)}
              positive={(metrics.sharpe_ratio ?? metrics.sharpe ?? 0) >= 1}
            />
          </div>

          {/* Equity Curve */}
          {equityCurve.length > 0 && (
            <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up" style={{ animationDelay: '50ms' }}>
              <h4 className="text-text-primary text-xs font-semibold mb-3">{t('backtest.equityCurve')}</h4>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={equityCurve}>
                  <XAxis
                    dataKey={equityCurve[0]?.date ? 'date' : 'day'}
                    tick={{ fill: '#999', fontSize: 8 }}
                    axisLine={false}
                    tickLine={false}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    tick={{ fill: '#999', fontSize: 9 }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v) => v != null && isFinite(v) ? `$${safeFixed(v, 0)}` : '--'}
                  />
                  <Tooltip
                    contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
                    formatter={(value) => [value != null && isFinite(value) ? `$${safeFixed(value, 2)}` : '--', 'Equity']}
                  />
                  <Line
                    type="monotone"
                    dataKey={equityCurve[0]?.equity != null ? 'equity' : 'balance'}
                    stroke="#d4a017"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Recent Trades */}
          {trades.length > 0 && (
            <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up" style={{ animationDelay: '100ms' }}>
              <h4 className="text-text-primary text-xs font-semibold mb-3">{t('backtest.trades')}</h4>
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {trades.slice(0, 20).map((trade, i) => {
                  const isLong = (trade.direction || trade.side || '').toLowerCase() === 'long' || (trade.direction || trade.side || '').toLowerCase() === 'buy'
                  const pnl = trade.pnl ?? trade.profit ?? 0
                  return (
                    <div key={i} className="flex items-center justify-between bg-bg-secondary rounded-xl px-3 py-2">
                      <div className="flex items-center gap-2">
                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${isLong ? 'bg-accent-green/10 text-accent-green' : 'bg-accent-red/10 text-accent-red'}`}>
                          {isLong ? 'LONG' : 'SHORT'}
                        </span>
                        <span className="text-text-muted text-[10px]">
                          {trade.date || trade.entry_date || `#${i + 1}`}
                        </span>
                      </div>
                      <div className="text-right">
                        <span className={`text-xs font-bold tabular-nums ${pnl >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                          {pnl >= 0 ? '+' : ''}{safeFixed(pnl, 2)}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </>
      )}

      {/* No results state */}
      {!results && !loading && !error && (
        <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
          <p className="text-text-muted text-xs">{t('backtest.noResults')}</p>
        </div>
      )}
    </div>
  )
}

function MetricCard({ label, value, positive }) {
  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 text-center">
      <p className="text-text-muted text-[10px] uppercase tracking-wider font-medium mb-1">{label}</p>
      <p className={`text-lg font-bold tabular-nums ${positive ? 'text-accent-green' : 'text-accent-red'}`}>
        {value}
      </p>
    </div>
  )
}
