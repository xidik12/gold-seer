import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { safeFixed } from '../utils/format'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
const HOURS = Array.from({ length: 24 }, (_, i) => i)

function getHeatColor(val) {
  if (val == null || !isFinite(val)) return 'rgba(128,128,128,0.15)'
  const abs = Math.min(Math.abs(val), 0.5)
  const intensity = abs / 0.5
  if (val > 0) {
    const r = Math.round(34 * (1 - intensity) + 34)
    const g = Math.round(197 * intensity + 80 * (1 - intensity))
    const b = Math.round(94 * intensity + 80 * (1 - intensity))
    return `rgba(${r},${g},${b},${0.2 + intensity * 0.6})`
  }
  const r = Math.round(239 * intensity + 80 * (1 - intensity))
  const g = Math.round(68 * intensity + 80 * (1 - intensity))
  const b = Math.round(68 * intensity + 80 * (1 - intensity))
  return `rgba(${r},${g},${b},${0.2 + intensity * 0.6})`
}

export default function IntradayHeatmap() {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [tooltip, setTooltip] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const result = await api.getIntradayPatterns()
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
        <div className="h-4 w-32 bg-bg-hover rounded mb-3" />
        <div className="h-48 bg-bg-hover rounded" />
      </div>
    )
  }

  if (!data) return null

  // Build lookup: patterns array or matrix
  const patterns = data.patterns || data.hours || data
  const lookup = {}
  if (Array.isArray(patterns)) {
    for (const p of patterns) {
      const h = p.hour ?? p.utc_hour
      const d = p.weekday ?? p.day
      if (h != null && d != null) {
        lookup[`${h}-${d}`] = p
      }
    }
  }

  const getCell = (hour, dayIdx) => {
    // dayIdx: 0=Mon, 4=Fri
    return lookup[`${hour}-${dayIdx}`] || lookup[`${hour}-${dayIdx + 1}`] || null
  }

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <h4 className="text-text-primary text-xs font-semibold mb-3">
        {t('intraday.title', 'Intraday Heatmap')}
      </h4>

      <div className="overflow-x-auto -mx-1">
        <table className="w-full text-[8px] border-collapse min-w-[260px]">
          <thead>
            <tr>
              <th className="text-text-muted font-normal p-0.5 text-left w-8">UTC</th>
              {DAYS.map((d) => (
                <th key={d} className="text-text-muted font-normal p-0.5 text-center">{d}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {HOURS.map((hour) => (
              <tr key={hour}>
                <td className="text-text-muted p-0.5 tabular-nums text-right pr-1">
                  {String(hour).padStart(2, '0')}
                </td>
                {DAYS.map((day, dayIdx) => {
                  const cell = getCell(hour, dayIdx)
                  const avgReturn = cell?.avg_return ?? null
                  return (
                    <td
                      key={dayIdx}
                      className="p-0.5 relative"
                      onMouseEnter={() => setTooltip({ hour, day, cell })}
                      onMouseLeave={() => setTooltip(null)}
                      onTouchStart={() => setTooltip({ hour, day, cell })}
                      onTouchEnd={() => setTooltip(null)}
                    >
                      <div
                        className="w-full h-3.5 rounded-[2px]"
                        style={{ backgroundColor: getHeatColor(avgReturn) }}
                      />
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-2 mt-2">
        <span className="text-text-muted text-[8px]">Bearish</span>
        <div className="flex gap-0.5">
          {[-0.4, -0.2, 0, 0.2, 0.4].map((v) => (
            <div key={v} className="w-4 h-2 rounded-[1px]" style={{ backgroundColor: getHeatColor(v) }} />
          ))}
        </div>
        <span className="text-text-muted text-[8px]">Bullish</span>
      </div>

      {/* Tooltip */}
      {tooltip && tooltip.cell && (
        <div className="mt-2 bg-bg-secondary rounded-lg px-3 py-2 border border-white/10">
          <p className="text-text-primary text-[10px] font-medium mb-1">
            {tooltip.day} {String(tooltip.hour).padStart(2, '0')}:00 UTC
          </p>
          <div className="flex gap-4 text-[9px]">
            <span className="text-text-muted">
              {t('intraday.avgReturn', 'Avg Return')}: <span className={`font-semibold ${(tooltip.cell.avg_return ?? 0) >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                {safeFixed(tooltip.cell.avg_return, 4)}%
              </span>
            </span>
            {tooltip.cell.positive_rate != null && (
              <span className="text-text-muted">
                {t('intraday.positiveRate', 'Positive Rate')}: <span className="text-text-primary font-semibold">
                  {safeFixed(tooltip.cell.positive_rate * (tooltip.cell.positive_rate <= 1 ? 100 : 1), 1)}%
                </span>
              </span>
            )}
            {tooltip.cell.trade_count != null && (
              <span className="text-text-muted">
                {t('intraday.trades', 'Trades')}: <span className="text-text-primary font-semibold">
                  {tooltip.cell.trade_count}
                </span>
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
