import { useState } from 'react'
import { useTranslation } from 'react-i18next'

const CATEGORIES = [
  { key: 'marketData', labelKey: 'resources:categories.marketData' },
  { key: 'economicData', labelKey: 'resources:categories.economicData' },
  { key: 'analysis', labelKey: 'resources:categories.analysis' },
  { key: 'etf', labelKey: 'resources:categories.etf' },
  { key: 'platforms', labelKey: 'resources:categories.platforms' },
  { key: 'learn', labelKey: 'resources:categories.learn' },
]

const RESOURCES = {
  marketData: {
    titleKey: 'resources:marketData.title',
    descriptionKey: 'resources:marketData.description',
    items: [
      {
        name: 'Kitco',
        url: 'https://www.kitco.com',
        tier: 'Essential',
        tags: ['Live prices', 'Charts', 'News'],
        desc: 'The gold standard for precious metals data. Live spot prices, interactive charts, market news, and analysis. Every gold trader bookmarks this.',
      },
      {
        name: 'GoldPrice.org',
        url: 'https://goldprice.org',
        tier: 'Essential',
        tags: ['Spot price', 'Multi-currency', 'Historical'],
        desc: 'Real-time gold price in 50+ currencies. Clean historical charts, price alerts, and comparison with silver and platinum.',
      },
      {
        name: 'BullionVault',
        url: 'https://www.bullionvault.com/gold-price-chart.do',
        tier: 'Pro',
        tags: ['Physical gold', 'Bid/ask', 'Storage'],
        desc: 'Live physical gold market with real bid/ask spreads. Also a platform to buy and store allocated gold. Institutional-grade pricing.',
      },
      {
        name: 'World Gold Council',
        url: 'https://www.gold.org',
        tier: 'Essential',
        tags: ['Research', 'Demand data', 'ETF flows'],
        desc: 'The authoritative source for gold market intelligence. Quarterly demand reports, ETF flow data, central bank buying, and investment research.',
      },
      {
        name: 'LBMA',
        url: 'https://www.lbma.org.uk',
        tier: 'Pro',
        tags: ['Benchmark price', 'OTC data', 'Clearing'],
        desc: 'London Bullion Market Association — sets the global gold price benchmark (LBMA Gold Price). OTC trading statistics, vault data, and market standards.',
      },
    ],
  },
  economicData: {
    titleKey: 'resources:economicData.title',
    descriptionKey: 'resources:economicData.description',
    items: [
      {
        name: 'FRED (St. Louis Fed)',
        url: 'https://fred.stlouisfed.org',
        tier: 'Essential',
        tags: ['Real yields', 'CPI', 'DXY'],
        desc: 'Federal Reserve Economic Data — the definitive macro database. Real yields (TIPS), inflation, Fed funds rate, M2 money supply. Free and comprehensive.',
      },
      {
        name: 'TradingEconomics',
        url: 'https://tradingeconomics.com',
        tier: 'Essential',
        tags: ['Macro indicators', 'Calendar', 'Forecasts'],
        desc: 'Global economic calendar and macro data aggregator. CPI, GDP, interest rates, PMI for 200 countries. Excellent for tracking gold drivers.',
      },
      {
        name: 'CFTC COT Reports',
        url: 'https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm',
        tier: 'Pro',
        tags: ['Positioning', 'Commercials', 'Large specs'],
        desc: 'Commitments of Traders — weekly report showing how commercial hedgers, large speculators, and small traders are positioned in gold futures. Top contrarian tool.',
      },
      {
        name: 'CME Group (Gold Futures)',
        url: 'https://www.cmegroup.com/markets/metals/precious/gold.html',
        tier: 'Pro',
        tags: ['Futures', 'Options', 'Open interest'],
        desc: 'COMEX gold futures hub. Contract specs, settlement prices, open interest, volume, and options data. The world\'s primary gold futures exchange.',
      },
    ],
  },
  analysis: {
    titleKey: 'resources:analysis.title',
    descriptionKey: 'resources:analysis.description',
    items: [
      {
        name: 'FXStreet — Gold',
        url: 'https://www.fxstreet.com/rates-charts/commodities/xauusd',
        tier: 'Essential',
        tags: ['XAUUSD analysis', 'Forecasts', 'News'],
        desc: 'Best dedicated XAUUSD coverage. Daily technical analysis, fundamental forecasts, expert opinions, and real-time price. Trusted by forex and gold traders.',
      },
      {
        name: 'DailyFX',
        url: 'https://www.dailyfx.com/gold',
        tier: 'Essential',
        tags: ['Technical analysis', 'Sentiment', 'Education'],
        desc: 'IG Group\'s research arm. Top-tier XAUUSD technical and fundamental analysis, SSI (retail sentiment), and educational guides. Free and high quality.',
      },
      {
        name: 'Investing.com — Gold',
        url: 'https://www.investing.com/commodities/gold',
        tier: 'All',
        tags: ['Prices', 'News', 'Community'],
        desc: 'Comprehensive gold hub. Live prices, interactive charts, analyst forecasts, economic calendar integration, and a large community of traders.',
      },
      {
        name: 'ForexLive',
        url: 'https://www.forexlive.com',
        tier: 'Pro',
        tags: ['Real-time news', 'Central banks', 'Fast alerts'],
        desc: 'The fastest forex and commodities news wire. Real-time central bank headlines, risk-off flows, and price-moving macro events that affect gold.',
      },
      {
        name: 'Reuters Commodities',
        url: 'https://www.reuters.com/markets/commodities',
        tier: 'All',
        tags: ['Institutional news', 'Macro', 'Reports'],
        desc: 'Institutional-grade commodities news. Central bank policy, geopolitical risk, ETF flow updates, and mining news that moves gold markets.',
      },
    ],
  },
  etf: {
    titleKey: 'resources:etf.title',
    descriptionKey: 'resources:etf.description',
    items: [
      {
        name: 'SPDR Gold Shares (GLD)',
        url: 'https://www.spdrgoldshares.com',
        tier: 'Essential',
        tags: ['Largest ETF', 'Holdings data', 'Daily updates'],
        desc: 'World\'s largest gold ETF. Daily holdings in tonnes, NAV, and price. GLD inflows/outflows are a leading indicator of institutional gold demand.',
      },
      {
        name: 'iShares Gold Trust (IAU)',
        url: 'https://www.ishares.com/us/products/239561/ISHARES-GOLD-TRUST-FUND',
        tier: 'All',
        tags: ['Low cost', 'Holdings', 'BlackRock'],
        desc: 'BlackRock\'s gold ETF — lower expense ratio than GLD. Track IAU holdings as a complementary signal to GLD for total ETF flow picture.',
      },
      {
        name: 'WGC ETF Data Hub',
        url: 'https://www.gold.org/goldhub/data/gold-etfs/holdings',
        tier: 'Essential',
        tags: ['All ETFs', 'Flows', 'Tonnes'],
        desc: 'World Gold Council aggregates all global gold ETF holdings. Total tonnes held across all products, weekly flows, and historical trend data.',
      },
      {
        name: 'ETF.com — Gold ETFs',
        url: 'https://www.etf.com/channels/gold-etfs',
        tier: 'Beginner',
        tags: ['Comparison', 'Fees', 'Rankings'],
        desc: 'Compare all gold ETFs side-by-side. Expense ratios, AUM, performance, liquidity, and analyst ratings. Best for choosing the right gold ETF product.',
      },
    ],
  },
  platforms: {
    titleKey: 'resources:platforms.title',
    descriptionKey: 'resources:platforms.description',
    items: [
      {
        name: 'MetaTrader 4 / 5',
        url: 'https://www.metatrader4.com',
        tier: 'Essential',
        tags: ['EA automation', 'Industry standard', 'XAUUSD'],
        desc: 'The industry standard for forex and gold trading. Expert Advisors (EAs) for automation, custom indicators, strategy tester. Supported by every broker.',
      },
      {
        name: 'TradingView (XAUUSD)',
        url: 'https://www.tradingview.com/chart/?symbol=OANDA%3AXAUUSD',
        tier: 'Essential',
        tags: ['Charts', '100+ indicators', 'Alerts'],
        desc: 'Best charting platform for XAUUSD. 100+ indicators, Pine Script strategies, price alerts, and community-shared gold trading setups.',
      },
      {
        name: 'OANDA — Gold',
        url: 'https://www.oanda.com/us-en/trading/instruments/xauusd/',
        tier: 'All',
        tags: ['Regulated', 'Tight spreads', 'XAUUSD CFD'],
        desc: 'Top regulated gold CFD broker. Tight XAUUSD spreads, no commissions, fxTrade platform, and excellent historical data access for backtesting.',
      },
      {
        name: 'cTrader',
        url: 'https://ctrader.com',
        tier: 'Pro',
        tags: ['ECN', 'Algo trading', 'Depth of market'],
        desc: 'Professional ECN trading platform. Depth of market (DOM) for gold futures, cBots for automation, advanced order types, and tight institutional spreads.',
      },
    ],
  },
  learn: {
    titleKey: 'resources:learn.title',
    descriptionKey: 'resources:learn.description',
    items: [
      {
        name: 'BabyPips — Commodities',
        url: 'https://www.babypips.com/learn/forex/commodities',
        tier: 'Beginner',
        tags: ['Free course', 'Gold basics', 'Guided'],
        desc: 'The best free forex and commodities education. School of Pipsology covers gold trading fundamentals, how macro events move gold, and practical strategies.',
      },
      {
        name: 'Investopedia — Gold',
        url: 'https://www.investopedia.com/articles/basics/09/gold-market.asp',
        tier: 'Beginner',
        tags: ['Education', 'Guides', 'Free'],
        desc: 'Comprehensive gold trading education. How gold markets work, what drives prices, trading vehicles (futures, ETFs, CFDs), and risk management.',
      },
      {
        name: 'School of Pipsology',
        url: 'https://www.babypips.com/learn/forex',
        tier: 'Beginner',
        tags: ['Structured course', 'Forex + Gold', 'Free'],
        desc: 'BabyPips\' flagship free course. 10-grade structured curriculum from beginner to pro. Covers technical analysis, fundamental drivers, and trading psychology.',
      },
      {
        name: 'CME Institute — Gold',
        url: 'https://www.cmegroup.com/education/courses/introduction-to-precious-metals.html',
        tier: 'All',
        tags: ['Futures education', 'Official', 'Certificates'],
        desc: 'CME Group\'s official precious metals education. How gold futures work, hedging strategies, contract mechanics, and risk management. Free with registration.',
      },
      {
        name: 'r/Gold & r/Commodities',
        url: 'https://reddit.com/r/gold',
        tier: 'Free',
        tags: ['Community', 'Discussion', 'Sentiment'],
        desc: 'Largest gold and commodities communities on Reddit. Real-time discussion, news sharing, sentiment gauge, and community-vetted analysis.',
      },
    ],
  },
}

const TIER_COLORS = {
  Essential: 'bg-accent-gold/15 text-accent-gold border-accent-gold/30',
  Pro: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
  Beginner: 'bg-accent-green/15 text-accent-green border-accent-green/30',
  Free: 'bg-accent-goldBright/15 text-accent-goldBright border-accent-goldBright/30',
  All: 'bg-white/10 text-text-secondary border-white/20',
}

function ResourceCard({ item }) {
  const tierClass = TIER_COLORS[item.tier] || TIER_COLORS.All

  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block bg-bg-card rounded-xl p-3 border border-white/5 hover:border-white/15 active:scale-[0.98] transition-all"
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-text-primary text-sm font-bold">{item.name}</span>
        <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded border ${tierClass}`}>
          {item.tier}
        </span>
      </div>
      <p className="text-text-muted text-[10px] leading-relaxed mb-2">{item.desc}</p>
      <div className="flex flex-wrap gap-1">
        {item.tags.map(tag => (
          <span key={tag} className="text-[8px] bg-white/5 text-text-muted px-1.5 py-0.5 rounded">
            {tag}
          </span>
        ))}
      </div>
    </a>
  )
}

export default function Resources() {
  const { t } = useTranslation(['resources', 'common'])
  const [activeCategory, setActiveCategory] = useState('marketData')
  const category = RESOURCES[activeCategory]

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      <h1 className="text-lg font-bold">{t('resources:title')}</h1>
      <p className="text-text-muted text-[11px]">
        {t('resources:subtitle')}
      </p>

      {/* Category tabs */}
      <div className="flex gap-1 overflow-x-auto no-scrollbar">
        {CATEGORIES.map(c => (
          <button key={c.key} onClick={() => setActiveCategory(c.key)}
            className={`flex-shrink-0 px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-all ${
              activeCategory === c.key
                ? 'bg-accent-gold/20 text-accent-gold border border-accent-gold/30'
                : 'text-text-muted border border-white/5'
            }`}>
            {t(c.labelKey)}
          </button>
        ))}
      </div>

      {/* Category content */}
      <div>
        <h2 className="text-text-secondary text-xs font-semibold mb-1">{t(`resources:${activeCategory}.title`)}</h2>
        <p className="text-text-muted text-[10px] mb-3">{t(`resources:${activeCategory}.description`)}</p>
        <div className="space-y-2">
          {category.items.map(item => (
            <ResourceCard key={item.name} item={item} />
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-2">{t('resources:tierGuide').toUpperCase()}</h3>
        <div className="grid grid-cols-2 gap-2">
          {[
            { tier: 'Essential', descKey: 'resources:tiers.essential.desc' },
            { tier: 'Beginner', descKey: 'resources:tiers.beginner.desc' },
            { tier: 'Pro', descKey: 'resources:tiers.pro.desc' },
            { tier: 'Free', descKey: 'resources:tiers.free.desc' },
          ].map(tier => (
            <div key={tier.tier} className="flex items-start gap-2">
              <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded border flex-shrink-0 mt-0.5 ${TIER_COLORS[tier.tier]}`}>
                {tier.tier}
              </span>
              <span className="text-text-muted text-[10px]">{t(tier.descKey)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Getting started guide */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">{t('resources:gettingStarted.title').toUpperCase()}</h3>
        <div className="space-y-2 text-[11px] text-text-muted">
          <div className="flex gap-2">
            <span className="text-accent-green font-bold text-xs w-4">1</span>
            <p><span className="text-text-secondary font-semibold">{t('resources:gettingStarted.beginner_label')}</span>{t('resources:gettingStarted.beginner_desc')}</p>
          </div>
          <div className="flex gap-2">
            <span className="text-accent-gold font-bold text-xs w-4">2</span>
            <p><span className="text-text-secondary font-semibold">{t('resources:gettingStarted.intermediate_label')}</span>{t('resources:gettingStarted.intermediate_desc')}</p>
          </div>
          <div className="flex gap-2">
            <span className="text-purple-400 font-bold text-xs w-4">3</span>
            <p><span className="text-text-secondary font-semibold">{t('resources:gettingStarted.advanced_label')}</span>{t('resources:gettingStarted.advanced_desc')}</p>
          </div>
        </div>
      </div>

      {/* Key metrics every trader should track */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">{t('resources:keyMetrics.title').toUpperCase()}</h3>
        <div className="space-y-2">
          {[
            'goldSilverRatio', 'realYields', 'dxy', 'vix',
            'cotNetPositioning', 'etfHoldings', 'centralBankBuying', 'rsiMacd',
          ].map((key) => (
            <div key={key} className="bg-white/[0.02] rounded-lg p-2.5">
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-text-primary text-[11px] font-semibold">{t(`resources:keyMetrics.${key}.name`)}</span>
                <span className="text-text-muted text-[8px]">{t(`resources:keyMetrics.${key}.source`)}</span>
              </div>
              <p className="text-text-muted text-[10px]">{t(`resources:keyMetrics.${key}.why`)}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
