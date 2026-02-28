import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatPricePrecise, safeFixed } from '../utils/format'

function getTrafficLight(premium) {
  if (premium == null || !isFinite(premium)) return { color: 'bg-gray-500', ring: 'ring-gray-500/30', label: '--' }
  if (premium < 2) return { color: 'bg-green-500', ring: 'ring-green-500/30', label: 'LOW' }
  if (premium < 4) return { color: 'bg-yellow-500', ring: 'ring-yellow-500/30', label: 'MODERATE' }
  return { color: 'bg-red-500', ring: 'ring-red-500/30', label: 'HIGH' }
}

export default function PhysicalPremiumWidget() {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const result = await api.getPhysicalPremium()
      setData(result)
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const iv = setInterval(fetchData, 300_000)
    return () => clearInterval(iv)
  }, [fetchData])

  if (loading) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
        <div className="h-4 w-36 bg-bg-hover rounded mb-3" />
        <div className="h-6 w-20 bg-bg-hover rounded" />
      </div>
    )
  }

  if (!data) return null

  const spotPrice = data.spot_price ?? data.spot_usd ?? null
  const cnyRate = data.cny_usd_rate ?? data.cny_rate ?? null
  const premium = data.estimated_sge_premium_pct ?? data.premium_pct ?? data.sge_premium ?? data.premium ?? null
  const light = getTrafficLight(premium)

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-text-primary text-xs font-semibold">
          {t('physical.title', 'Physical Premium')}
        </h4>
        {/* Traffic light indicator */}
        <div className="flex items-center gap-1.5">
          {[
            { threshold: 'green', active: premium != null && premium < 2 },
            { threshold: 'yellow', active: premium != null && premium >= 2 && premium < 4 },
            { threshold: 'red', active: premium != null && premium >= 4 },
          ].map((l, i) => (
            <div
              key={i}
              className={`w-3 h-3 rounded-full transition-all ${
                l.active
                  ? `${i === 0 ? 'bg-green-500 ring-2 ring-green-500/30' : i === 1 ? 'bg-yellow-500 ring-2 ring-yellow-500/30' : 'bg-red-500 ring-2 ring-red-500/30'}`
                  : 'bg-white/10'
              }`}
            />
          ))}
        </div>
      </div>

      {/* SGE Premium */}
      <div className="flex items-center gap-3 mb-3">
        <div>
          <p className="text-text-muted text-[9px]">{t('physical.sgePremium', 'SGE Premium')}</p>
          <p className={`text-xl font-bold tabular-nums ${
            premium != null && premium >= 4 ? 'text-accent-red' : premium != null && premium >= 2 ? 'text-yellow-400' : 'text-accent-green'
          }`}>
            {premium != null ? `${safeFixed(premium, 2)}%` : '--'}
          </p>
        </div>
        <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${light.color}/15 ${
          premium != null && premium >= 4 ? 'text-red-400' : premium != null && premium >= 2 ? 'text-yellow-400' : 'text-green-400'
        }`}>
          {light.label}
        </span>
      </div>

      {/* Spot price and CNY rate */}
      <div className="grid grid-cols-2 gap-3 pt-2 border-t border-white/5">
        <div>
          <p className="text-text-muted text-[9px]">{t('physical.spotPrice', 'Spot Price')}</p>
          <p className="text-text-primary text-xs font-semibold tabular-nums">
            {spotPrice != null ? formatPricePrecise(spotPrice) : '--'}
          </p>
        </div>
        <div>
          <p className="text-text-muted text-[9px]">{t('physical.cnyRate', 'CNY/USD Rate')}</p>
          <p className="text-text-primary text-xs font-semibold tabular-nums">
            {cnyRate != null ? safeFixed(cnyRate, 4) : '--'}
          </p>
        </div>
      </div>
    </div>
  )
}
