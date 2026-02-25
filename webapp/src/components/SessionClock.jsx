import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'

const SESSIONS = [
  { key: 'asian', label: 'Asian', openHour: 0, closeHour: 9, color: '#FFD700' },
  { key: 'london', label: 'London', openHour: 8, closeHour: 17, color: '#D4AF37' },
  { key: 'newYork', label: 'New York', openHour: 13, closeHour: 22, color: '#B8860B' },
]

function getUTCHour() {
  return new Date().getUTCHours()
}

function isSessionActive(session) {
  const h = getUTCHour()
  if (session.openHour < session.closeHour) {
    return h >= session.openHour && h < session.closeHour
  }
  return h >= session.openHour || h < session.closeHour
}

function getNextSessionEvent(sessions) {
  const now = new Date()
  const utcH = now.getUTCHours()
  const utcM = now.getUTCMinutes()
  const currentMinutes = utcH * 60 + utcM

  let closest = null
  let closestDiff = Infinity

  for (const s of sessions) {
    const openMin = s.openHour * 60
    const closeMin = s.closeHour * 60
    for (const target of [openMin, closeMin]) {
      let diff = target - currentMinutes
      if (diff <= 0) diff += 24 * 60
      if (diff < closestDiff) {
        closestDiff = diff
        closest = { session: s, minutesUntil: diff, isOpen: target === openMin }
      }
    }
  }
  return closest
}

function formatCountdown(minutes) {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

export default function SessionClock() {
  const { t } = useTranslation()
  const [, setTick] = useState(0)

  useEffect(() => {
    const iv = setInterval(() => setTick((n) => n + 1), 60_000)
    return () => clearInterval(iv)
  }, [])

  const next = getNextSessionEvent(SESSIONS)

  return (
    <div className="bg-bg-card rounded-2xl p-3 border border-white/5">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-text-primary text-xs font-semibold">
          {t('sessionClock.title', 'Trading Sessions')}
        </h4>
        {next && (
          <span className="text-text-muted text-[10px]">
            {next.isOpen ? t('sessionClock.opens', 'Opens') : t('sessionClock.closes', 'Closes')}{' '}
            {next.session.label} {t('sessionClock.in', 'in')} {formatCountdown(next.minutesUntil)}
          </span>
        )}
      </div>
      <div className="flex gap-3">
        {SESSIONS.map((s) => {
          const active = isSessionActive(s)
          return (
            <div key={s.key} className="flex items-center gap-1.5">
              <div
                className={`w-2 h-2 rounded-full ${active ? 'animate-pulse' : ''}`}
                style={{ backgroundColor: active ? '#22c55e' : '#4b5563' }}
              />
              <span className={`text-[10px] font-medium ${active ? 'text-text-primary' : 'text-text-muted'}`}>
                {s.label}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
