import { useMemo } from 'react'

// 20-year average monthly gold returns (approximate, well-documented)
const MONTHLY_RETURNS = [
  { month: 'Jan', avg: 1.4 },
  { month: 'Feb', avg: 0.8 },
  { month: 'Mar', avg: -0.2 },
  { month: 'Apr', avg: 0.9 },
  { month: 'May', avg: -0.1 },
  { month: 'Jun', avg: -0.3 },
  { month: 'Jul', avg: 0.5 },
  { month: 'Aug', avg: 1.2 },
  { month: 'Sep', avg: -0.8 },
  { month: 'Oct', avg: 0.2 },
  { month: 'Nov', avg: 0.4 },
  { month: 'Dec', avg: 0.9 },
]

export default function SeasonalityWidget() {
  const currentMonth = useMemo(() => new Date().getMonth(), [])
  const maxAbs = Math.max(...MONTHLY_RETURNS.map(m => Math.abs(m.avg)))

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-1">GOLD SEASONALITY</h3>
      <p className="text-text-muted text-[9px] mb-3">20-year average monthly returns for gold</p>
      <div className="space-y-1">
        {MONTHLY_RETURNS.map((m, i) => {
          const isCurrent = i === currentMonth
          const barWidth = (Math.abs(m.avg) / maxAbs) * 100
          const isPositive = m.avg >= 0
          return (
            <div key={m.month} className={`flex items-center gap-2 py-0.5 px-1 rounded ${isCurrent ? 'bg-accent-gold/10 border border-accent-gold/20' : ''}`}>
              <span className={`text-[10px] w-7 font-medium ${isCurrent ? 'text-accent-gold' : 'text-text-muted'}`}>
                {m.month}
              </span>
              <div className="flex-1 flex items-center">
                <div className="w-1/2 flex justify-end">
                  {!isPositive && (
                    <div className="h-2.5 bg-accent-red/60 rounded-l" style={{ width: `${barWidth}%` }} />
                  )}
                </div>
                <div className="w-px h-4 bg-white/10 mx-0.5" />
                <div className="w-1/2">
                  {isPositive && (
                    <div className="h-2.5 bg-accent-green/60 rounded-r" style={{ width: `${barWidth}%` }} />
                  )}
                </div>
              </div>
              <span className={`text-[10px] font-bold tabular-nums w-10 text-right ${
                isPositive ? 'text-accent-green' : 'text-accent-red'
              }`}>
                {m.avg > 0 ? '+' : ''}{m.avg.toFixed(1)}%
              </span>
            </div>
          )
        })}
      </div>
      <p className="text-text-muted text-[9px] mt-2 text-center">
        Based on historical data. Past performance does not predict future results.
      </p>
    </div>
  )
}
