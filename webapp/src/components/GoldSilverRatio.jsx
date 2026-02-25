import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'

export default function GoldSilverRatio() {
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
        <div className="h-4 w-32 bg-bg-hover rounded mb-3" />
        <div className="h-8 w-20 bg-bg-hover rounded mb-2" />
        <div className="h-3 w-full bg-bg-hover rounded" />
      </div>
    )
  }

  const ratio = data?.gold_silver_ratio ?? data?.gs_ratio ?? 82
  const bbHigh = data?.gs_bb_high ?? 95
  const bbLow = data?.gs_bb_low ?? 70
  const range = bbHigh - bbLow
  const position = range > 0 ? ((ratio - bbLow) / range) * 100 : 50
  const clampedPos = Math.max(0, Math.min(100, position))
  const isExtended = ratio > bbHigh || ratio < bbLow

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <h4 className="text-text-primary text-xs font-semibold mb-2">
        {t('goldSilverRatio.title', 'Gold/Silver Ratio')}
      </h4>

      <div className="flex items-baseline gap-2 mb-3">
        <span className="text-2xl font-bold text-accent-goldBright tabular-nums">{ratio.toFixed(1)}</span>
        {isExtended && (
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-accent-red/10 text-accent-red">
            {t('goldSilverRatio.extended', 'Extended')}
          </span>
        )}
      </div>

      {/* Bollinger Band visual */}
      <div className="relative h-3 bg-bg-secondary rounded-full overflow-hidden">
        {/* Band range */}
        <div className="absolute inset-y-0 bg-accent-gold/15 rounded-full" style={{ left: '0%', right: '0%' }} />
        {/* Marker */}
        <div
          className="absolute top-0 bottom-0 w-1.5 rounded-full bg-accent-goldBright transition-all duration-500"
          style={{ left: `calc(${clampedPos}% - 3px)` }}
        />
      </div>

      <div className="flex justify-between mt-1">
        <span className="text-text-muted text-[9px] tabular-nums">{bbLow.toFixed(0)}</span>
        <span className="text-text-muted text-[9px]">{t('goldSilverRatio.range', 'BB Range')}</span>
        <span className="text-text-muted text-[9px] tabular-nums">{bbHigh.toFixed(0)}</span>
      </div>
    </div>
  )
}
