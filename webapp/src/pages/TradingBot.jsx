import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useTelegram } from '../hooks/useTelegram'
import { api } from '../utils/api'
import { formatPricePrecise, formatPercent } from '../utils/format'
import BrokerStatus from '../components/BrokerStatus'
import TradeControls from '../components/TradeControls'

const POLL_INTERVAL = 15_000

export default function TradingBot() {
  const { t } = useTranslation()
  const { tg } = useTelegram()
  const [account, setAccount] = useState(null)
  const [positions, setPositions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [closingId, setClosingId] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const [acctRes, posRes] = await Promise.allSettled([
        api.getBrokerAccount(),
        api.getBrokerPositions(),
      ])
      if (acctRes.status === 'fulfilled') setAccount(acctRes.value)
      if (posRes.status === 'fulfilled') setPositions(posRes.value?.positions || [])
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

  const handleClosePosition = async (positionId) => {
    setClosingId(positionId)
    try {
      await api.closeBrokerPosition(positionId)
      await fetchData()
    } catch (err) {
      setError(err.message)
    } finally {
      setClosingId(null)
    }
  }

  const handleExecuteTrade = async (trade) => {
    try {
      await api.placeBrokerOrder(trade)
      await fetchData()
    } catch (err) {
      setError(err.message)
    }
  }

  const connected = account?.connected ?? false
  const acctData = account?.account || {}
  const balance = acctData.balance ?? null
  const equity = acctData.equity ?? null
  const margin = acctData.margin ?? null
  const freeMargin = acctData.free_margin ?? null

  if (loading) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold text-shimmer-gold">{t('tradingBot.pageTitle', 'Trading Bot')}</h1>
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
      <h1 className="text-lg font-bold text-shimmer-gold">{t('tradingBot.pageTitle', 'Trading Bot')}</h1>

      {/* Connection Status */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-text-primary text-sm font-semibold">{t('tradingBot.broker', 'Broker')}</h4>
          <BrokerStatus connected={connected} balance={balance} />
        </div>

        {connected && (
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: t('tradingBot.balance', 'Balance'), value: balance != null ? formatPricePrecise(balance) : '--' },
              { label: t('tradingBot.equity', 'Equity'), value: equity != null ? formatPricePrecise(equity) : '--' },
              { label: t('tradingBot.margin', 'Used Margin'), value: margin != null ? formatPricePrecise(margin) : '--' },
              { label: t('tradingBot.freeMargin', 'Free Margin'), value: freeMargin != null ? formatPricePrecise(freeMargin) : '--' },
            ].map((item) => (
              <div key={item.label} className="bg-bg-secondary/50 rounded-lg px-3 py-2">
                <p className="text-text-muted text-[10px]">{item.label}</p>
                <p className="text-text-primary text-sm font-semibold tabular-nums">{item.value}</p>
              </div>
            ))}
          </div>
        )}

        {!connected && (
          <p className="text-text-muted text-xs">
            {t('tradingBot.notConnectedDesc', 'Broker is not connected. Configure your broker API credentials in the backend settings.')}
          </p>
        )}
      </div>

      {error && (
        <div className="bg-bg-card rounded-2xl p-3 border border-accent-red/20">
          <p className="text-accent-red text-xs">{error}</p>
          <button onClick={fetchData} className="text-accent-gold text-xs mt-1 underline">
            {t('common:app.retry', 'Retry')}
          </button>
        </div>
      )}

      {/* Active Positions */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h4 className="text-text-primary text-sm font-semibold mb-3">
          {t('tradingBot.positions', 'Active Positions')} ({positions.length})
        </h4>
        {positions.length === 0 ? (
          <p className="text-text-muted text-xs">{t('tradingBot.noPositions', 'No open positions')}</p>
        ) : (
          <div className="space-y-2">
            {positions.map((pos) => {
              const pnl = pos.profit ?? pos.pnl ?? 0
              return (
                <div
                  key={pos.id ?? pos.ticket}
                  className="flex items-center justify-between bg-bg-secondary/50 rounded-lg px-3 py-2"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        pos.direction === 'buy' || pos.type === 'buy'
                          ? 'bg-accent-green/10 text-accent-green'
                          : 'bg-accent-red/10 text-accent-red'
                      }`}>
                        {(pos.direction || pos.type || '').toUpperCase()}
                      </span>
                      <span className="text-text-primary text-xs font-medium">{pos.symbol || 'XAUUSD'}</span>
                      <span className="text-text-muted text-[10px]">{pos.lot_size ?? pos.volume ?? '--'} lot</span>
                    </div>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-text-muted text-[10px]">
                        {t('tradingBot.entry', 'Entry')}: {pos.open_price ? formatPricePrecise(pos.open_price) : '--'}
                      </span>
                      {pos.stop_loss && (
                        <span className="text-accent-red text-[10px]">SL: {formatPricePrecise(pos.stop_loss)}</span>
                      )}
                      {pos.take_profit && (
                        <span className="text-accent-green text-[10px]">TP: {formatPricePrecise(pos.take_profit)}</span>
                      )}
                    </div>
                  </div>
                  <div className="text-right shrink-0 ml-2">
                    <p className={`text-sm font-bold tabular-nums ${pnl >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                      {pnl >= 0 ? '+' : ''}{formatPricePrecise(pnl)}
                    </p>
                    <button
                      onClick={() => handleClosePosition(pos.id ?? pos.ticket)}
                      disabled={closingId === (pos.id ?? pos.ticket)}
                      className="text-accent-red text-[10px] font-medium mt-0.5 hover:underline disabled:opacity-50"
                    >
                      {closingId === (pos.id ?? pos.ticket)
                        ? t('tradingBot.closing', 'Closing...')
                        : t('tradingBot.close', 'Close')
                      }
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Trade Controls */}
      <TradeControls onExecute={handleExecuteTrade} disabled={!connected} />

      {/* Risk Settings (compact) */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h4 className="text-text-primary text-xs font-semibold mb-2">{t('tradingBot.riskSettings', 'Risk Settings')}</h4>
        <div className="grid grid-cols-2 gap-2">
          {[
            { label: t('tradingBot.maxRisk', 'Max Risk %'), value: acctData.risk_pct ?? '2.0' },
            { label: t('tradingBot.maxPositions', 'Max Positions'), value: acctData.max_positions ?? '3' },
            { label: t('tradingBot.dailyLoss', 'Daily Loss Limit'), value: acctData.daily_loss_limit ? formatPricePrecise(acctData.daily_loss_limit) : '--' },
            { label: t('tradingBot.trailingStop', 'Trailing Stop'), value: acctData.trailing_stop ? 'On' : 'Off' },
          ].map((item) => (
            <div key={item.label} className="bg-bg-secondary/50 rounded-lg px-2.5 py-1.5">
              <p className="text-text-muted text-[9px]">{item.label}</p>
              <p className="text-text-primary text-xs font-semibold tabular-nums">{item.value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

