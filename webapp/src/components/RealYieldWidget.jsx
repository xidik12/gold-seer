import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'

export default function RealYieldWidget() {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const result = await api.getMacroData()
      setData(result)
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const iv = setInterval(fetchData, 120_000)
    return () => clearInterval(iv)
  }, [fetchData])

  if (loading) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
        <div className="h-4 w-28 bg-bg-hover rounded mb-3" />
        <div className="h-6 w-16 bg-bg-hover rounded mb-2" />
        <div className="h-3 w-24 bg-bg-hover rounded" />
      </div>
    )
  }

  const realYield = data?.real_yield_10y ?? data?.real_yield ?? null
  const tipsBreakeven = data?.tips_breakeven ?? data?.breakeven_10y ?? null
  const trend = data?.real_yield_trend ?? (realYield != null && realYield < 0 ? 'falling' : 'rising')
  const isBullishGold = trend === 'falling' || (realYield != null && realYield < 1.0)

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <h4 className="text-text-primary text-xs font-semibold mb-2">
        {t('realYield.title', 'Real Yield (10Y)')}
      </h4>

      <div className="flex items-center gap-3 mb-2">
        <span className="text-xl font-bold tabular-nums text-accent-goldBright">
          {realYield != null ? `${realYield.toFixed(2)}%` : '--'}
        </span>
        {/* Trend arrow */}
        <span className={`text-lg ${trend === 'falling' ? 'text-accent-green' : 'text-accent-red'}`}>
          {trend === 'falling' ? '\u2193' : '\u2191'}
        </span>
        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
          isBullishGold
            ? 'bg-accent-green/10 text-accent-green'
            : 'bg-accent-red/10 text-accent-red'
        }`}>
          {isBullishGold
            ? t('realYield.bullishGold', 'Bullish Gold')
            : t('realYield.bearishGold', 'Bearish Gold')
          }
        </span>
      </div>

      {tipsBreakeven != null && (
        <p className="text-text-muted text-[10px]">
          {t('realYield.tipsBreakeven', 'TIPS Breakeven')}: {tipsBreakeven.toFixed(2)}%
        </p>
      )}
    </div>
  )
}
