import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'

export default function Analysts() {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const result = await api.getAnalystForecasts()
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
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold text-shimmer-gold">{t('analysts.pageTitle', 'Analyst Forecasts')}</h1>
        <p className="text-text-muted text-xs">{t('analysts.subtitle', 'Institutional gold price targets')}</p>
        {/* Skeleton for consensus card */}
        <div className="bg-bg-card rounded-2xl p-5 border border-white/5 animate-pulse">
          <div className="h-4 w-32 bg-bg-hover rounded mb-3" />
          <div className="h-10 w-40 bg-bg-hover rounded mb-2" />
          <div className="h-3 w-20 bg-bg-hover rounded" />
        </div>
        {/* Skeleton for forecast cards */}
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
            <div className="h-4 w-36 bg-bg-hover rounded mb-3" />
            <div className="h-6 w-24 bg-bg-hover rounded mb-2" />
            <div className="h-3 w-48 bg-bg-hover rounded" />
          </div>
        ))}
      </div>
    )
  }

  const forecasts = data?.forecasts || data?.analysts || []
  const consensus = data?.consensus || null
  const consensusDirection = consensus?.direction || (consensus?.target > 0 ? 'bullish' : 'neutral')

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <div>
        <h1 className="text-lg font-bold text-shimmer-gold">{t('analysts.pageTitle', 'Analyst Forecasts')}</h1>
        <p className="text-text-muted text-xs mt-0.5">{t('analysts.subtitle', 'Institutional gold price targets')}</p>
      </div>

      {error && (
        <div className="bg-bg-card rounded-2xl p-3 border border-accent-red/20">
          <p className="text-accent-red text-xs">{error}</p>
          <button onClick={fetchData} className="text-accent-gold text-xs mt-1 underline">
            {t('common:app.retry', 'Retry')}
          </button>
        </div>
      )}

      {/* Consensus Target Card */}
      {consensus && (
        <div className="bg-bg-card rounded-2xl p-5 border border-accent-gold/15 slide-up">
          <p className="text-text-muted text-[10px] uppercase tracking-wider font-medium mb-2">
            {t('analysts.consensus', 'Consensus Target')}
          </p>
          <div className="flex items-center gap-3">
            <span className="text-3xl font-bold text-accent-goldBright tabular-nums">
              ${typeof consensus.target === 'number' ? consensus.target.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : consensus.target}
            </span>
            <DirectionBadge direction={consensusDirection} />
          </div>
          {consensus.timeframe && (
            <p className="text-text-muted text-[10px] mt-1">{consensus.timeframe}</p>
          )}
        </div>
      )}

      {/* Analyst Forecast Grid */}
      {forecasts.length === 0 && !error ? (
        <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
          <p className="text-text-muted text-xs">{t('analysts.noForecasts', 'No analyst forecasts available')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {forecasts.map((forecast, idx) => (
            <div
              key={forecast.id ?? idx}
              className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up"
              style={{ animationDelay: `${idx * 50}ms` }}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1 min-w-0">
                  <h4 className="text-text-primary text-sm font-semibold truncate">
                    {forecast.institution || forecast.name || t('analysts.institution', 'Institution')}
                  </h4>
                  {forecast.timeframe && (
                    <p className="text-text-muted text-[10px] mt-0.5">
                      {t('analysts.timeframe', 'Timeframe')}: {forecast.timeframe}
                    </p>
                  )}
                </div>
                <DirectionBadge direction={forecast.direction || 'neutral'} />
              </div>

              <div className="flex items-baseline gap-2 mb-2">
                <span className="text-text-muted text-[10px]">{t('analysts.target', 'Target')}:</span>
                <span className="text-lg font-bold text-accent-goldBright tabular-nums">
                  ${typeof forecast.target === 'number'
                    ? forecast.target.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                    : forecast.target_price
                      ? typeof forecast.target_price === 'number'
                        ? forecast.target_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                        : forecast.target_price
                      : '--'
                  }
                </span>
              </div>

              {(forecast.reasoning || forecast.summary || forecast.notes) && (
                <p className="text-text-muted text-[10px] leading-relaxed border-t border-white/5 pt-2 line-clamp-3">
                  {forecast.reasoning || forecast.summary || forecast.notes}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function DirectionBadge({ direction }) {
  const dir = (direction || '').toLowerCase()
  const isBullish = dir === 'bullish' || dir === 'up' || dir === 'long' || dir === 'buy'
  const isBearish = dir === 'bearish' || dir === 'down' || dir === 'short' || dir === 'sell'

  return (
    <span
      className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${
        isBullish
          ? 'bg-accent-green/10 text-accent-green'
          : isBearish
          ? 'bg-accent-red/10 text-accent-red'
          : 'bg-bg-hover text-text-muted'
      }`}
    >
      {isBullish ? 'BULLISH' : isBearish ? 'BEARISH' : 'NEUTRAL'}
    </span>
  )
}
