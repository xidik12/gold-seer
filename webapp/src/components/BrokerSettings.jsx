import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { useTelegram } from '../hooks/useTelegram'

export default function BrokerSettings() {
  const { t } = useTranslation('common')
  const { hapticFeedback } = useTelegram()

  // Form state
  const [brokerType, setBrokerType] = useState('demo')
  const [token, setToken] = useState('')
  const [accountId, setAccountId] = useState('')
  const [server, setServer] = useState('')
  const [login, setLogin] = useState('')
  const [showToken, setShowToken] = useState(false)

  // Status state
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [connected, setConnected] = useState(false)
  const [accountInfo, setAccountInfo] = useState(null)
  const [error, setError] = useState(null)
  const [hasSettings, setHasSettings] = useState(false)

  // Load broker settings on mount
  useEffect(() => {
    let cancelled = false
    api.getBrokerSettings()
      .then((data) => {
        if (cancelled) return
        if (data && data.broker_type) {
          setBrokerType(data.broker_type || 'demo')
          setToken(data.token || '')
          setAccountId(data.account_id || '')
          setServer(data.server || '')
          setLogin(data.login || '')
          setConnected(data.is_connected || data.connected || false)
          setHasSettings(true)
        }
      })
      .catch(() => {
        // No settings yet — that's fine
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [])

  // Load account info when connected
  useEffect(() => {
    if (!connected) {
      setAccountInfo(null)
      return
    }
    api.getBrokerAccount()
      .then((data) => setAccountInfo(data))
      .catch(() => setAccountInfo(null))
  }, [connected])

  const handleSave = useCallback(async () => {
    hapticFeedback?.impactOccurred('light')
    setSaving(true)
    setError(null)
    try {
      await api.saveBrokerSettings({
        broker_type: brokerType,
        metaapi_token: brokerType === 'metaapi' ? token : undefined,
        account_id: brokerType === 'metaapi' ? accountId : undefined,
        server: brokerType === 'metaapi' ? server : undefined,
        login: brokerType === 'metaapi' ? login : undefined,
      })
      setHasSettings(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }, [brokerType, token, accountId, server, login, hapticFeedback])

  const handleConnect = useCallback(async () => {
    hapticFeedback?.impactOccurred('medium')
    setConnecting(true)
    setError(null)
    try {
      await api.connectBroker()
      setConnected(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setConnecting(false)
    }
  }, [hapticFeedback])

  const handleDisconnect = useCallback(async () => {
    hapticFeedback?.impactOccurred('medium')
    setConnecting(true)
    setError(null)
    try {
      await api.disconnectBroker()
      setConnected(false)
      setAccountInfo(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setConnecting(false)
    }
  }, [hapticFeedback])

  const handleDelete = useCallback(async () => {
    if (!window.confirm(t('broker.deleteConfirm'))) return
    hapticFeedback?.impactOccurred('heavy')
    setError(null)
    try {
      await api.deleteBrokerSettings()
      setBrokerType('demo')
      setToken('')
      setAccountId('')
      setServer('')
      setLogin('')
      setConnected(false)
      setAccountInfo(null)
      setHasSettings(false)
    } catch (err) {
      setError(err.message)
    }
  }, [hapticFeedback, t])

  if (loading) {
    return (
      <div className="bg-bg-card rounded-xl border border-white/5 p-4 animate-pulse">
        <div className="h-5 w-40 bg-bg-hover rounded mb-3" />
        <div className="h-10 bg-bg-hover rounded mb-2" />
        <div className="h-10 bg-bg-hover rounded" />
      </div>
    )
  }

  return (
    <div className="bg-bg-card rounded-xl border border-white/5 p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <svg className="w-4 h-4 text-accent-gold" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83" />
        </svg>
        <h3 className="text-text-primary font-semibold text-sm">
          {t('broker.title')}
        </h3>
        {/* Connection status dot */}
        <div className="ml-auto flex items-center gap-1.5">
          <div className={`w-2 h-2 rounded-full ${connected ? 'bg-accent-green animate-pulse' : 'bg-accent-red'}`} />
          <span className={`text-[10px] font-medium ${connected ? 'text-accent-green' : 'text-text-muted'}`}>
            {connected ? t('broker.connected') : t('broker.disconnected')}
          </span>
        </div>
      </div>

      {/* Broker Type Selector */}
      <div>
        <div className="text-[10px] text-text-muted font-semibold uppercase tracking-wider mb-1.5">
          {t('broker.type')}
        </div>
        <div className="flex bg-bg-hover rounded-lg p-0.5">
          <button
            onClick={() => { setBrokerType('demo'); hapticFeedback?.selectionChanged() }}
            className={`flex-1 py-1.5 text-[10px] font-semibold rounded-md transition-all ${
              brokerType === 'demo' ? 'bg-accent-gold text-white' : 'text-text-muted'
            }`}
          >
            {t('broker.demo')}
          </button>
          <button
            onClick={() => { setBrokerType('metaapi'); hapticFeedback?.selectionChanged() }}
            className={`flex-1 py-1.5 text-[10px] font-semibold rounded-md transition-all ${
              brokerType === 'metaapi' ? 'bg-accent-gold text-white' : 'text-text-muted'
            }`}
          >
            {t('broker.metaapi')}
          </button>
        </div>
      </div>

      {/* MetaAPI Fields */}
      {brokerType === 'metaapi' && (
        <div className="space-y-2">
          {/* Token */}
          <div>
            <label className="text-[10px] text-text-muted font-medium block mb-1">
              {t('broker.token')}
            </label>
            <div className="relative">
              <input
                type={showToken ? 'text' : 'password'}
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="eyJ..."
                className="w-full bg-bg-secondary border border-white/5 rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-muted/50 focus:outline-none focus:border-accent-gold/40 pr-9"
              />
              <button
                type="button"
                onClick={() => setShowToken(!showToken)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary"
              >
                {showToken ? (
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* Account ID */}
          <div>
            <label className="text-[10px] text-text-muted font-medium block mb-1">
              {t('broker.accountId')}
            </label>
            <input
              type="text"
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              placeholder="abc123..."
              className="w-full bg-bg-secondary border border-white/5 rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-muted/50 focus:outline-none focus:border-accent-gold/40"
            />
          </div>

          {/* Server (optional) */}
          <div>
            <label className="text-[10px] text-text-muted font-medium block mb-1">
              {t('broker.server')}
              <span className="text-text-muted/40 ml-1">(optional)</span>
            </label>
            <input
              type="text"
              value={server}
              onChange={(e) => setServer(e.target.value)}
              placeholder="ATFX-Demo"
              className="w-full bg-bg-secondary border border-white/5 rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-muted/50 focus:outline-none focus:border-accent-gold/40"
            />
          </div>

          {/* Login (optional) */}
          <div>
            <label className="text-[10px] text-text-muted font-medium block mb-1">
              {t('broker.login')}
              <span className="text-text-muted/40 ml-1">(optional)</span>
            </label>
            <input
              type="text"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              placeholder="12345678"
              className="w-full bg-bg-secondary border border-white/5 rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-muted/50 focus:outline-none focus:border-accent-gold/40"
            />
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="bg-accent-red/10 border border-accent-red/30 rounded-lg px-3 py-2">
          <p className="text-accent-red text-[10px]">{error}</p>
        </div>
      )}

      {/* Save button */}
      <button
        onClick={handleSave}
        disabled={saving}
        className={`w-full py-2 rounded-lg text-xs font-semibold transition-all ${
          saving
            ? 'bg-accent-gold/30 text-white/40 cursor-not-allowed'
            : 'bg-accent-gold text-white active:scale-[0.98]'
        }`}
      >
        {saving ? t('broker.saving') : t('broker.save')}
      </button>

      {/* Connect / Disconnect button */}
      {hasSettings && (
        <button
          onClick={connected ? handleDisconnect : handleConnect}
          disabled={connecting}
          className={`w-full py-2 rounded-lg text-xs font-semibold transition-all ${
            connecting
              ? 'bg-bg-hover text-text-muted cursor-not-allowed'
              : connected
                ? 'bg-accent-red/15 text-accent-red border border-accent-red/30 active:scale-[0.98]'
                : 'bg-accent-green/15 text-accent-green border border-accent-green/30 active:scale-[0.98]'
          }`}
        >
          {connecting
            ? t('broker.connecting')
            : connected
              ? t('broker.disconnect')
              : t('broker.connect')
          }
        </button>
      )}

      {/* Account Info when connected */}
      {connected && accountInfo && (
        <div className="bg-bg-secondary rounded-lg p-3 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-text-muted text-[10px]">{t('broker.balance')}</span>
            <span className="text-text-primary text-xs font-semibold tabular-nums">
              ${accountInfo.balance?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? '—'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-text-muted text-[10px]">{t('broker.equity')}</span>
            <span className="text-text-primary text-xs font-semibold tabular-nums">
              ${accountInfo.equity?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? '—'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-text-muted text-[10px]">{t('broker.leverage')}</span>
            <span className="text-text-primary text-xs font-semibold tabular-nums">
              1:{accountInfo.leverage ?? '—'}
            </span>
          </div>
        </div>
      )}

      {/* No settings hint */}
      {!hasSettings && (
        <p className="text-text-muted text-[10px] text-center">
          {t('broker.noSettings')}
        </p>
      )}

      {/* Delete button */}
      {hasSettings && (
        <button
          onClick={handleDelete}
          className="w-full py-1.5 text-[10px] text-accent-red/70 hover:text-accent-red transition-colors"
        >
          {t('broker.deleteSettings')}
        </button>
      )}
    </div>
  )
}
