import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'

export default function CentralBankWidget() {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const result = await api.getCentralBankData()
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
        <div className="h-6 w-24 bg-bg-hover rounded" />
      </div>
    )
  }

  const netPurchases = data?.cb_net_purchases ?? data?.central_bank_purchases ?? null
  const trend = data?.cb_trend ?? null
  const sparkData = data?.cb_history ?? []

  // Mini sparkline SVG
  const sparkWidth = 80
  const sparkHeight = 24
  let sparkPath = ''
  if (sparkData.length > 1) {
    const max = Math.max(...sparkData.map((d) => d.value ?? d))
    const min = Math.min(...sparkData.map((d) => d.value ?? d))
    const range = max - min || 1
    sparkPath = sparkData
      .map((d, i) => {
        const val = d.value ?? d
        const x = (i / (sparkData.length - 1)) * sparkWidth
        const y = sparkHeight - ((val - min) / range) * sparkHeight
        return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
      })
      .join(' ')
  }

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <h4 className="text-text-primary text-xs font-semibold mb-2">
        {t('centralBank.title', 'Central Bank Purchases')}
      </h4>

      <div className="flex items-center justify-between">
        <div>
          <span className="text-xl font-bold text-accent-goldBright tabular-nums">
            {netPurchases != null ? `${netPurchases > 0 ? '+' : ''}${netPurchases.toFixed(1)}t` : '--'}
          </span>
          <p className="text-text-muted text-[10px] mt-0.5">
            {t('centralBank.netMonthly', 'Net monthly (tonnes)')}
          </p>
        </div>

        {sparkPath && (
          <svg width={sparkWidth} height={sparkHeight} className="shrink-0">
            <path
              d={sparkPath}
              fill="none"
              stroke="#D4AF37"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </div>

      {trend && (
        <p className={`text-[10px] mt-2 font-medium ${
          trend === 'buying' ? 'text-accent-green' : trend === 'selling' ? 'text-accent-red' : 'text-text-muted'
        }`}>
          {trend === 'buying'
            ? t('centralBank.buying', 'Net buyers this quarter')
            : trend === 'selling'
            ? t('centralBank.selling', 'Net sellers this quarter')
            : t('centralBank.neutral', 'Neutral positioning')
          }
        </p>
      )}

      {data?.top_buyers?.length > 0 && (
        <div className="mt-3 border-t border-white/5 pt-2">
          <p className="text-text-muted text-[9px] font-medium mb-1">
            {t('centralBank.topBuyers', 'Top Buyers')}
          </p>
          <div className="flex flex-wrap gap-1">
            {data.top_buyers.slice(0, 5).map((buyer, i) => (
              <span key={i} className="text-[9px] bg-bg-hover rounded px-1.5 py-0.5 text-text-secondary">
                {typeof buyer === 'string' ? buyer : buyer.name || buyer.country}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
