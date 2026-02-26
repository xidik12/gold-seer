import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatPricePrecise, formatPercent, formatNumber, formatMarketCap, safeFixed } from '../utils/format'

const POLL_INTERVAL = 120_000

function TreemapChart({ miners }) {
  if (!miners || miners.length === 0) return null

  // Sort by market_cap descending, take top 12
  const sorted = [...miners]
    .filter((m) => m.market_cap > 0)
    .sort((a, b) => (b.market_cap || 0) - (a.market_cap || 0))
    .slice(0, 12)

  const totalCap = sorted.reduce((s, m) => s + (m.market_cap || 0), 0)
  if (totalCap === 0) return null

  // Simple squarified layout: horizontal strips
  const rows = []
  let remaining = [...sorted]
  let y = 0
  const totalHeight = 200
  const totalWidth = 100 // percentage

  while (remaining.length > 0) {
    const rowItems = remaining.splice(0, Math.min(remaining.length, 4))
    const rowCap = rowItems.reduce((s, m) => s + (m.market_cap || 0), 0)
    const rowHeight = (rowCap / totalCap) * totalHeight
    let x = 0
    const cells = rowItems.map((m) => {
      const w = (m.market_cap / rowCap) * totalWidth
      const cell = { ...m, x, y, w, h: rowHeight }
      x += w
      return cell
    })
    rows.push(...cells)
    y += rowHeight
  }

  return (
    <div className="relative w-full" style={{ height: totalHeight }}>
      {rows.map((cell, i) => {
        const changePct = cell.change_pct ?? cell.change_percent ?? 0
        const bgColor = changePct >= 0
          ? `rgba(34,197,94,${Math.min(0.15 + Math.abs(changePct) * 0.05, 0.5)})`
          : `rgba(239,68,68,${Math.min(0.15 + Math.abs(changePct) * 0.05, 0.5)})`
        const borderColor = changePct >= 0 ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'
        return (
          <div
            key={cell.ticker || i}
            className="absolute flex flex-col items-center justify-center overflow-hidden rounded-sm border"
            style={{
              left: `${cell.x}%`,
              top: cell.y,
              width: `${cell.w}%`,
              height: cell.h,
              backgroundColor: bgColor,
              borderColor,
            }}
          >
            <span className="text-text-primary text-[10px] font-bold leading-none">
              {cell.ticker || cell.symbol}
            </span>
            <span className={`text-[8px] font-semibold tabular-nums ${changePct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {formatPercent(changePct)}
            </span>
          </div>
        )
      })}
    </div>
  )
}

export default function Miners() {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const result = await api.getGoldMiners()
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
    const iv = setInterval(fetchData, POLL_INTERVAL)
    return () => clearInterval(iv)
  }, [fetchData])

  if (loading) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold text-shimmer-gold">{t('miners.pageTitle', 'Gold Miners')}</h1>
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
            <div className="h-5 w-32 bg-bg-hover rounded mb-3" />
            <div className="h-24 bg-bg-hover rounded" />
          </div>
        ))}
      </div>
    )
  }

  const miners = data?.miners || data?.stocks || []
  const gdxGldRatio = data?.gdx_gld_ratio ?? null
  const ratioChange = data?.ratio_change ?? data?.ratio_change_pct ?? null

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <h1 className="text-lg font-bold text-shimmer-gold">{t('miners.pageTitle', 'Gold Miners')}</h1>
      <p className="text-text-muted text-xs -mt-2">
        {t('miners.subtitle', 'Gold mining stocks & leading indicators')}
      </p>

      {error && (
        <div className="bg-bg-card rounded-2xl p-3 border border-accent-red/20">
          <p className="text-accent-red text-xs">{error}</p>
          <button onClick={fetchData} className="text-accent-gold text-xs mt-1 underline">
            {t('common:app.retry', 'Retry')}
          </button>
        </div>
      )}

      {/* GDX/GLD Ratio Card */}
      {gdxGldRatio != null && (
        <div className="bg-bg-card rounded-2xl p-4 border border-accent-gold/15 slide-up">
          <div className="flex items-center justify-between mb-1">
            <h4 className="text-text-primary text-sm font-semibold">
              {t('miners.gdxGldRatio', 'GDX/GLD Ratio')}
            </h4>
            {ratioChange != null && (
              <span className={`text-xs font-bold tabular-nums ${ratioChange >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                {formatPercent(ratioChange)}
              </span>
            )}
          </div>
          <p className="text-accent-goldBright text-2xl font-bold tabular-nums">{safeFixed(gdxGldRatio, 4)}</p>
          <p className="text-text-muted text-[10px] mt-1">
            {t('miners.leadingIndicator', 'Leading indicator for gold')}
          </p>
        </div>
      )}

      {/* Treemap visualization */}
      {miners.length > 0 && (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
          <h4 className="text-text-primary text-sm font-semibold mb-3">
            {t('miners.pageTitle', 'Gold Miners')}
          </h4>
          <TreemapChart miners={miners} />
        </div>
      )}

      {/* Miner cards grid */}
      {miners.length > 0 ? (
        <div className="grid grid-cols-2 gap-3">
          {miners.map((miner, i) => {
            const changePct = miner.change_pct ?? miner.change_percent ?? 0
            return (
              <div key={miner.ticker || i} className="bg-bg-card rounded-xl p-3 border border-white/5 slide-up">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-text-primary text-xs font-bold">{miner.ticker || miner.symbol}</span>
                  <span className={`text-[10px] font-bold tabular-nums ${changePct >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                    {formatPercent(changePct)}
                  </span>
                </div>
                <p className="text-text-muted text-[9px] mb-2 truncate">{miner.name || '--'}</p>
                <div className="space-y-0.5">
                  <div className="flex justify-between">
                    <span className="text-text-muted text-[9px]">{t('price.price', 'Price')}</span>
                    <span className="text-text-primary text-[10px] font-semibold tabular-nums">
                      {miner.price != null ? formatPricePrecise(miner.price) : '--'}
                    </span>
                  </div>
                  {miner.market_cap != null && (
                    <div className="flex justify-between">
                      <span className="text-text-muted text-[9px]">{t('price.marketCap', 'Market Cap')}</span>
                      <span className="text-text-primary text-[10px] font-semibold tabular-nums">
                        {formatMarketCap(miner.market_cap)}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        !error && (
          <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
            <p className="text-text-muted text-xs">{t('miners.noData', 'No miners data available')}</p>
          </div>
        )
      )}
    </div>
  )
}
