import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { safeFixed } from '../utils/format'

const REGIME_COLORS = {
  RISK_ON: { bg: 'bg-green-500/15', border: 'border-green-500/30', text: 'text-green-400', dot: 'bg-green-500' },
  RISK_OFF: { bg: 'bg-red-500/15', border: 'border-red-500/30', text: 'text-red-400', dot: 'bg-red-500' },
  STAGFLATION: { bg: 'bg-orange-500/15', border: 'border-orange-500/30', text: 'text-orange-400', dot: 'bg-orange-500' },
  DEFLATION: { bg: 'bg-blue-500/15', border: 'border-blue-500/30', text: 'text-blue-400', dot: 'bg-blue-500' },
  REFLATION: { bg: 'bg-amber-500/15', border: 'border-amber-500/30', text: 'text-amber-400', dot: 'bg-amber-500' },
  NEUTRAL: { bg: 'bg-gray-500/15', border: 'border-gray-500/30', text: 'text-gray-400', dot: 'bg-gray-500' },
}

const REGIME_KEYS = {
  RISK_ON: 'regime.riskOn',
  RISK_OFF: 'regime.riskOff',
  STAGFLATION: 'regime.stagflation',
  DEFLATION: 'regime.deflation',
  REFLATION: 'regime.reflation',
  NEUTRAL: 'regime.neutral',
}

const REGIME_DEFAULTS = {
  RISK_ON: 'Risk-On',
  RISK_OFF: 'Risk-Off',
  STAGFLATION: 'Stagflation',
  DEFLATION: 'Deflation',
  REFLATION: 'Reflation',
  NEUTRAL: 'Neutral',
}

export default function MacroRegimeWidget() {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const result = await api.getMacroRegime()
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
        <div className="h-6 w-20 bg-bg-hover rounded" />
      </div>
    )
  }

  if (!data) return null

  const regime = data.regime || data.name || 'NEUTRAL'
  const regimeKey = regime.toUpperCase().replace(/[\s-]+/g, '_')
  const colors = REGIME_COLORS[regimeKey] || REGIME_COLORS.NEUTRAL
  const confidence = data.confidence ?? null
  const goldReturn = data.gold_historical_avg_return ?? data.gold_avg_return ?? data.avg_return ?? null
  const description = data.description || null

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <h4 className="text-text-primary text-xs font-semibold mb-3">
        {t('regime.title', 'Macro Regime')}
      </h4>

      <div className="flex items-center justify-between mb-3">
        <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full ${colors.bg} ${colors.border} border`}>
          <div className={`w-2 h-2 rounded-full ${colors.dot}`} />
          <span className={`text-sm font-bold ${colors.text}`}>
            {t(REGIME_KEYS[regimeKey] || 'regime.neutral', REGIME_DEFAULTS[regimeKey] || 'Neutral')}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {confidence != null && (
          <div>
            <p className="text-text-muted text-[9px]">{t('regime.confidence', 'Confidence')}</p>
            <p className="text-text-primary text-sm font-semibold tabular-nums">
              {safeFixed(confidence * (confidence <= 1 ? 100 : 1), 1)}%
            </p>
          </div>
        )}
        {goldReturn != null && (
          <div>
            <p className="text-text-muted text-[9px]">{t('regime.goldReturn', 'Gold Avg Return')}</p>
            <p className={`text-sm font-semibold tabular-nums ${goldReturn >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
              {goldReturn >= 0 ? '+' : ''}{safeFixed(goldReturn, 2)}%
            </p>
          </div>
        )}
      </div>

      {description && (
        <p className="text-text-muted text-[10px] mt-2 leading-relaxed">{description}</p>
      )}
    </div>
  )
}
