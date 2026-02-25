import { useTranslation } from 'react-i18next'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'

export default function COTChart({ data = [] }) {
  const { t } = useTranslation()

  if (!data.length) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h4 className="text-text-primary text-sm font-semibold mb-2">
          {t('cot.managedMoney', 'Managed Money Positioning')}
        </h4>
        <p className="text-text-muted text-xs">{t('common:app.noData', 'No data available')}</p>
      </div>
    )
  }

  const chartData = data.map((d) => ({
    date: d.report_date ? new Date(d.report_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '--',
    mm_long: d.mm_long ?? 0,
    mm_short: d.mm_short ?? 0,
  }))

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h4 className="text-text-primary text-sm font-semibold mb-3">
        {t('cot.managedMoney', 'Managed Money Positioning')}
      </h4>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData} barGap={2}>
          <XAxis
            dataKey="date"
            tick={{ fill: '#8884d8', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: '#8884d8', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(0)}K` : v)}
          />
          <Tooltip
            contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
            labelStyle={{ color: '#D4AF37' }}
          />
          <Legend
            wrapperStyle={{ fontSize: 10, color: '#999' }}
          />
          <Bar dataKey="mm_long" name={t('cot.long', 'Long')} fill="#22c55e" radius={[2, 2, 0, 0]} />
          <Bar dataKey="mm_short" name={t('cot.short', 'Short')} fill="#ef4444" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
