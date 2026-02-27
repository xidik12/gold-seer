const API_BASE = import.meta.env.VITE_API_URL || '/api'

// ── Client-side TTL cache + in-flight dedup ──
const _cache = new Map()
const _inflight = new Map()

function cachedFetch(endpoint, ttl, options = {}) {
  const key = endpoint
  // Only cache GET requests (no body, no method or method=GET)
  if (options.method && options.method !== 'GET') {
    return fetchAPI(endpoint, options)
  }

  // Check cache
  const entry = _cache.get(key)
  if (entry && Date.now() < entry.expiry) {
    return Promise.resolve(entry.data)
  }

  // Deduplicate in-flight requests
  if (_inflight.has(key)) {
    return _inflight.get(key)
  }

  const promise = fetchAPI(endpoint, options)
    .then((data) => {
      _cache.set(key, { data, expiry: Date.now() + ttl })
      _inflight.delete(key)
      return data
    })
    .catch((err) => {
      _inflight.delete(key)
      throw err
    })

  _inflight.set(key, promise)
  return promise
}

async function fetchAPI(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  const { headers: extraHeaders, ...rest } = options
  const initData = window.Telegram?.WebApp?.initData
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(initData ? { 'X-Telegram-Init-Data': initData } : {}),
      ...extraHeaders,
    },
    ...rest,
  })
  if (!res.ok) {
    let detail = `API error: ${res.status}`
    try {
      const body = await res.json()
      if (body.detail) {
        detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      }
    } catch {}
    throw new Error(detail)
  }
  return res.json()
}

// TTL constants (ms)
const T15 = 15_000   // 15s — fast-changing (price)
const T30 = 30_000   // 30s — predictions, signals, indicators
const T60 = 60_000   // 60s — news, events
const T120 = 120_000 // 2min — macro, supply
const T300 = 300_000 // 5min — fear & greed, supply

export const api = {
  // Predictions
  getCurrentPredictions: () => cachedFetch('/predictions/current', T30),
  getQuantPrediction: () => cachedFetch('/predictions/quant', T30),
  getQuantHistory: (days = 7) => cachedFetch(`/predictions/quant/history?days=${days}`, T60),
  getPredictionHistory: (timeframe = '1h', days = 7) =>
    cachedFetch(`/predictions/history?timeframe=${timeframe}&days=${days}`, T60),
  getPredictionAnalysis: (timeframe = '1h', days = 30) =>
    cachedFetch(`/predictions/analysis?timeframe=${timeframe}&days=${days}`, T120),
  getPredictionPatterns: () => cachedFetch('/predictions/patterns', T120),
  getLearningProgress: (days = 30) =>
    cachedFetch(`/predictions/learning-progress?days=${days}`, T120),

  // Signals
  getCurrentSignals: () => cachedFetch('/signals/current', T30),
  getSignalHistory: (timeframe = '1h', days = 7) =>
    cachedFetch(`/signals/history?timeframe=${timeframe}&days=${days}`, T60),

  // News
  getLatestNews: (limit = 20) => cachedFetch(`/news/latest?limit=${limit}`, T60),
  getNewsSentiment: (hours = 24) => cachedFetch(`/news/sentiment?hours=${hours}`, T60),

  // Market
  getCurrentPrice: () => cachedFetch('/market/price', T15),
  getPriceStats: (timeframe = '1d') => cachedFetch(`/market/stats?timeframe=${timeframe}`, T15),
  getCandles: (hours = 168) => cachedFetch(`/market/candles?hours=${hours}`, T30),
  getIndicators: () => cachedFetch('/market/indicators', T30),
  getMacroData: () => cachedFetch('/market/macro', T120),

  // History
  getAccuracy: (days = 30) => cachedFetch(`/history/accuracy?days=${days}`, T120),

  // Events
  getRecentEvents: (hours = 24) => cachedFetch(`/events/recent?hours=${hours}`, T60),
  getEventCategoryStats: () => cachedFetch('/events/category-stats', T60),
  getEventMemory: () => cachedFetch('/events/memory', T120),

  // Advisor (user-specific, no cache — requires Telegram auth)
  getPortfolio: (initData, telegramId) => fetchAPI(`/advisor/portfolio/${telegramId}`, {
    headers: { 'X-Telegram-Init-Data': initData },
  }),
  getActiveTrades: (initData, telegramId) => fetchAPI(`/advisor/trades/${telegramId}`, {
    headers: { 'X-Telegram-Init-Data': initData },
  }),
  getTradeHistory: (initData, telegramId) => fetchAPI(`/advisor/trades/${telegramId}/history`, {
    headers: { 'X-Telegram-Init-Data': initData },
  }),
  openTrade: (initData, tradeId) => fetchAPI(`/advisor/trades/${tradeId}/opened`, {
    method: 'POST',
    headers: { 'X-Telegram-Init-Data': initData },
  }),
  closeTrade: (initData, tradeId, exitPrice, reason = 'manual_close') =>
    fetchAPI(`/advisor/trades/${tradeId}/close`, {
      method: 'POST',
      headers: { 'X-Telegram-Init-Data': initData },
      body: JSON.stringify({ exit_price: exitPrice, reason }),
    }),

  setupPortfolio: (initData, telegramId, settings) =>
    fetchAPI(`/advisor/portfolio/${telegramId}/setup`, {
      method: 'POST',
      headers: { 'X-Telegram-Init-Data': initData },
      body: JSON.stringify(settings),
    }),
  updatePortfolio: (initData, telegramId, settings) =>
    fetchAPI(`/advisor/portfolio/${telegramId}/update`, {
      method: 'POST',
      headers: { 'X-Telegram-Init-Data': initData },
      body: JSON.stringify(settings),
    }),
  getSuggestion: (initData, telegramId) =>
    fetchAPI(`/advisor/suggest/${telegramId}`, {
      method: 'POST',
      headers: { 'X-Telegram-Init-Data': initData },
    }),
  getFeedback: (initData, days = 30) => fetchAPI(`/advisor/feedback?days=${days}`, {
    headers: { 'X-Telegram-Init-Data': initData },
  }),

  // Mock/Paper Trading (user-specific, no cache)
  getMockTrades: (initData, telegramId) => fetchAPI(`/advisor/trades/${telegramId}?mock=true`, {
    headers: { 'X-Telegram-Init-Data': initData },
  }),
  getMockHistory: (initData, telegramId) => fetchAPI(`/advisor/trades/${telegramId}/history?mock=true`, {
    headers: { 'X-Telegram-Init-Data': initData },
  }),
  createMockTrade: (initData, telegramId, trade) =>
    fetchAPI(`/advisor/trades/${telegramId}/mock`, {
      method: 'POST',
      headers: { 'X-Telegram-Init-Data': initData },
      body: JSON.stringify(trade),
    }),

  // Admin (no cache — needs fresh data)
  getAdminStats: (initData) => fetchAPI('/admin/stats', { headers: { 'X-Telegram-Init-Data': initData } }),
  getAdminUsers: (initData, page = 1, search = '') =>
    fetchAPI(`/admin/users?page=${page}&search=${encodeURIComponent(search)}`, { headers: { 'X-Telegram-Init-Data': initData } }),
  adminBanUser: (initData, telegramId, reason) =>
    fetchAPI(`/admin/users/${telegramId}/ban`, {
      method: 'POST',
      headers: { 'X-Telegram-Init-Data': initData },
      body: JSON.stringify({ reason }),
    }),
  adminUnbanUser: (initData, telegramId) =>
    fetchAPI(`/admin/users/${telegramId}/unban`, {
      method: 'POST',
      headers: { 'X-Telegram-Init-Data': initData },
    }),
  adminGrantPremium: (initData, telegramId, days) =>
    fetchAPI(`/admin/users/${telegramId}/grant-premium`, {
      method: 'POST',
      headers: { 'X-Telegram-Init-Data': initData },
      body: JSON.stringify({ days }),
    }),
  getAdminPredictions: (initData, limit = 50) =>
    fetchAPI(`/admin/predictions?limit=${limit}`, { headers: { 'X-Telegram-Init-Data': initData } }),
  getAdminSystem: (initData) => fetchAPI('/admin/system', { headers: { 'X-Telegram-Init-Data': initData } }),
  getAdminBotStatus: (initData) => fetchAPI('/admin/bot-status', { headers: { 'X-Telegram-Init-Data': initData } }),

  // Public config (long cache — bot username etc.)
  getPublicConfig: () => cachedFetch('/config/public', T300),

  // Auth (no cache)
  registerUser: (initData) => fetchAPI('/auth/register', {
    method: 'POST',
    headers: { 'X-Telegram-Init-Data': initData },
  }),
  getCurrentUser: (initData) => fetchAPI('/auth/me', {
    headers: { 'X-Telegram-Init-Data': initData },
  }),

  // Alert Preferences (no cache — user-specific)
  getAlertPreferences: (initData) => fetchAPI('/auth/alerts/preferences', {
    headers: { 'X-Telegram-Init-Data': initData },
  }),
  updateAlertPreferences: (initData, subscribed, alertInterval) => fetchAPI('/auth/alerts/preferences', {
    method: 'POST',
    headers: { 'X-Telegram-Init-Data': initData },
    body: JSON.stringify({ subscribed, alert_interval: alertInterval }),
  }),

  // Subscription (no cache)
  createInvoice: (tier) => fetchAPI(`/subscription/create-invoice?tier=${tier}`),
  getSubscriptionStatus: (initData) => fetchAPI('/subscription/status', {
    headers: { 'X-Telegram-Init-Data': initData },
  }),

  // Fear & Greed
  getFearGreed: (days = 30) => cachedFetch(`/market/fear-greed?days=${days}`, T300),

  // Indicator History
  getIndicatorHistory: () => cachedFetch('/market/indicator-history', T60),

  // Public API (no cache)
  getApiUsage: (apiKey) => fetchAPI('/v1/usage', { headers: { 'X-API-Key': apiKey } }),

  // Elliott Wave
  getElliottWaveCurrent: (timeframe = '4h') => cachedFetch(`/elliott-wave/current?timeframe=${timeframe}`, T120),
  getElliottWaveHistorical: (days = 90, timeframe = '4h') => cachedFetch(`/elliott-wave/historical?days=${days}&timeframe=${timeframe}`, T120),

  // Partner Dashboard (Telegram auth — only the linked partner can access)
  getPartnerStats: (initData, code) => fetchAPI(`/partner/${code}/stats`, {
    headers: { 'X-Telegram-Init-Data': initData },
  }),
  getPartnerReferrals: (initData, code) => fetchAPI(`/partner/${code}/referrals`, {
    headers: { 'X-Telegram-Init-Data': initData },
  }),

  // Partner Admin (requires initData)
  getAdminPartners: (initData) => fetchAPI('/admin/partners', { headers: { 'X-Telegram-Init-Data': initData } }),
  createAdminPartner: (initData, data) => fetchAPI('/admin/partners', {
    method: 'POST',
    headers: { 'X-Telegram-Init-Data': initData },
    body: JSON.stringify(data),
  }),
  updateAdminPartner: (initData, id, data) => fetchAPI(`/admin/partners/${id}`, {
    method: 'PUT',
    headers: { 'X-Telegram-Init-Data': initData },
    body: JSON.stringify(data),
  }),
  deleteAdminPartner: (initData, id) => fetchAPI(`/admin/partners/${id}`, {
    method: 'DELETE',
    headers: { 'X-Telegram-Init-Data': initData },
  }),
  getAdminPartnerStats: (initData, id) => fetchAPI(`/admin/partners/${id}/stats`, { headers: { 'X-Telegram-Init-Data': initData } }),
  getAdminPartnerReferrals: (initData, id) => fetchAPI(`/admin/partners/${id}/referrals`, { headers: { 'X-Telegram-Init-Data': initData } }),

  // Referral
  getReferralInfo: (initData) => fetchAPI('/referral/info', { headers: { 'X-Telegram-Init-Data': initData } }),
  getReferralLeaderboard: () => cachedFetch('/referral/leaderboard', T120),

  // Price Alerts (user-specific, no cache)
  getUserAlerts: (initData) => fetchAPI('/alerts/', { headers: { 'X-Telegram-Init-Data': initData } }),
  createAlert: (initData, body) => fetchAPI('/alerts/', {
    method: 'POST',
    headers: { 'X-Telegram-Init-Data': initData },
    body: JSON.stringify(body),
  }),
  deleteAlert: (initData, alertId) => fetchAPI(`/alerts/${alertId}`, {
    method: 'DELETE',
    headers: { 'X-Telegram-Init-Data': initData },
  }),
  updateAlert: (initData, alertId, body) => fetchAPI(`/alerts/${alertId}`, {
    method: 'PATCH',
    headers: { 'X-Telegram-Init-Data': initData },
    body: JSON.stringify(body),
  }),

  // Daily Briefings
  getLatestBriefing: () => cachedFetch('/briefings/latest', T120),
  getBriefingHistory: (days = 7) => cachedFetch(`/briefings/history?days=${days}`, T300),
  getBriefingByDate: (date) => cachedFetch(`/briefings/${date}`, T300),

  // Prediction Game
  makeGamePrediction: (initData, direction, timeframe = '24h') => fetchAPI('/game/predict', {
    method: 'POST',
    headers: { 'X-Telegram-Init-Data': initData },
    body: JSON.stringify({ direction, timeframe }),
  }),
  getGameStatus: (initData) => fetchAPI('/game/status', {
    headers: { 'X-Telegram-Init-Data': initData },
  }),
  getGameLeaderboard: (period = 'all_time', limit = 20) =>
    cachedFetch(`/game/leaderboard?period=${period}&limit=${limit}`, T60),
  getGameConsensus: (timeframe = '24h') =>
    cachedFetch(`/game/consensus?timeframe=${timeframe}`, T30),
  getGameHistory: (initData, limit = 30) => fetchAPI(`/game/history?limit=${limit}`, {
    headers: { 'X-Telegram-Init-Data': initData },
  }),

  // Market Overview (TradingView-style)
  getForexData: () => cachedFetch('/market/forex', T120),
  getCommoditiesData: () => cachedFetch('/market/commodities', T120),
  getYieldCurve: () => cachedFetch('/market/yields', T120),
  getTASummary: () => cachedFetch('/market/ta-summary', T60),
  getEconomicCalendar: (days = 14) => cachedFetch(`/market/calendar/upcoming?days=${days}`, T300),

  // Gold Calculators
  getCalculatorPipValue: (lotSize = 1.0) => cachedFetch(`/calculators/pip-value?lot_size=${lotSize}`, T120),
  getCalculatorLotSize: (params) => {
    const qs = new URLSearchParams(params).toString()
    return cachedFetch(`/calculators/lot-size?${qs}`, T120)
  },
  getCalculatorMargin: (params) => {
    const qs = new URLSearchParams(params).toString()
    return cachedFetch(`/calculators/margin?${qs}`, T120)
  },
  getCalculatorPnl: (params) => {
    const qs = new URLSearchParams(params).toString()
    return cachedFetch(`/calculators/pnl?${qs}`, T120)
  },
  getCalculatorWeightConvert: (params) => {
    const qs = new URLSearchParams(params).toString()
    return cachedFetch(`/calculators/weight-convert?${qs}`, T120)
  },
  getCalculatorMeltValue: (params) => {
    const qs = new URLSearchParams(params).toString()
    return cachedFetch(`/calculators/melt-value?${qs}`, T120)
  },

  // Correlations
  getCorrelations: () => cachedFetch('/market/correlations', T120),

  // Silver
  getSilverData: () => cachedFetch('/market/silver', T120),

  // Gold Supply
  getGoldSupply: () => cachedFetch('/market/supply', T300),

  // COT (Commitment of Traders)
  getCOTLatest: () => cachedFetch('/cot/latest', T300),

  // Upcoming Events
  getUpcomingEvents: () => cachedFetch('/events/recent', T60),

  // Trade Journal CRUD
  createJournalEntry: (body) => fetchAPI('/trade-journal/entries', {
    method: 'POST',
    body: JSON.stringify(body),
  }),
  updateJournalEntry: (id, body) => fetchAPI(`/trade-journal/entries/${id}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  }),
  deleteJournalEntry: (id) => fetchAPI(`/trade-journal/entries/${id}`, {
    method: 'DELETE',
  }),

  // Central Bank
  getCentralBankData: () => cachedFetch('/market/central-bank', T300),

  // Analyst Forecasts
  getAnalystForecasts: () => cachedFetch('/analysts/forecasts', T300),

  // Macro Regime
  getMacroRegime: () => cachedFetch('/market/regime', T120),

  // Gold Miners
  getGoldMiners: () => cachedFetch('/market/miners', T120),

  // Sessions
  getSessionsCurrent: () => cachedFetch('/sessions/current', T60),

  // Intraday Patterns
  getIntradayPatterns: () => cachedFetch('/market/intraday-patterns', T300),

  // ETF
  getGoldETFLatest: () => cachedFetch('/gold-etf/latest', T120),
  getETFMomentum: () => cachedFetch('/gold-etf/momentum', T120),

  // Physical Gold Premium
  getPhysicalPremium: () => cachedFetch('/market/physical-premium', T300),

  // Supply & Demand
  getSupplyDemand: () => cachedFetch('/fundamentals/supply-demand', T300),

  // Forward Curve
  getForwardCurve: () => cachedFetch('/market/forward-curve', T300),

  // Backtest
  runBacktest: (params) => fetchAPI('/backtest/run', {
    method: 'POST',
    body: JSON.stringify(params),
  }),

  // Community
  getCommunityTrades: () => cachedFetch('/community/trades', T60),
  shareTrade: (body) => fetchAPI('/community/trades', {
    method: 'POST',
    body: JSON.stringify(body),
  }),
  getCommunityLeaderboard: () => cachedFetch('/community/leaderboard', T120),
  likeTrade: (tradeId) => fetchAPI(`/community/trades/${tradeId}/like`, {
    method: 'POST',
  }),

  // Broker Settings (user-specific, no cache)
  getBrokerSettings: () => fetchAPI('/broker/settings'),
  saveBrokerSettings: (body) => fetchAPI('/broker/settings', {
    method: 'POST',
    body: JSON.stringify(body),
  }),
  deleteBrokerSettings: () => fetchAPI('/broker/settings', {
    method: 'DELETE',
  }),
  connectBroker: () => fetchAPI('/broker/connect', { method: 'POST' }),
  disconnectBroker: () => fetchAPI('/broker/disconnect', { method: 'POST' }),
  getBrokerAccount: () => fetchAPI('/broker/account'),
}
