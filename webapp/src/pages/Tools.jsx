import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import SubTabBar from '../components/SubTabBar'

const MARKET_TABS = [
  { path: '/elliott-wave', labelKey: 'common:link.elliottWave' },
  { path: '/events', labelKey: 'common:link.events' },
  { path: '/tools', labelKey: 'common:link.tools' },
  { path: '/learn', labelKey: 'common:link.learn' },
]

function PositionSizeCalc() {
  const { t } = useTranslation(['tools', 'common'])
  const [capital, setCapital] = useState('')
  const [riskPct, setRiskPct] = useState('2')
  const [entry, setEntry] = useState('')
  const [stopLoss, setStopLoss] = useState('')

  const capitalNum = parseFloat(capital) || 0
  const riskNum = parseFloat(riskPct) || 0
  const entryNum = parseFloat(entry) || 0
  const slNum = parseFloat(stopLoss) || 0

  const riskAmount = capitalNum * (riskNum / 100)
  const stopDist = Math.abs(entryNum - slNum)
  const positionSize = stopDist > 0 ? riskAmount / stopDist : 0
  const positionValue = positionSize * entryNum

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">{t('tools:positionSize.title').toUpperCase()}</h3>
      <p className="text-text-muted text-[10px] mb-3">
        {t('tools:positionSize.description')}
      </p>
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div>
          <label className="text-text-muted text-[10px]">{t('tools:positionSize.accountBalance')}</label>
          <input type="number" value={capital} onChange={e => setCapital(e.target.value)}
            placeholder="10000" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">{t('tools:positionSize.riskPercent')}</label>
          <input type="number" value={riskPct} onChange={e => setRiskPct(e.target.value)}
            placeholder="2" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">{t('tools:positionSize.entryPrice')}</label>
          <input type="number" value={entry} onChange={e => setEntry(e.target.value)}
            placeholder="2900" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">{t('tools:positionSize.stopLoss')}</label>
          <input type="number" value={stopLoss} onChange={e => setStopLoss(e.target.value)}
            placeholder="2850" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
      </div>
      {capitalNum > 0 && entryNum > 0 && slNum > 0 && (
        <div className="grid grid-cols-2 gap-2">
          <ResultBox label={t('tools:positionSize.riskAmount')} value={`$${riskAmount.toFixed(2)}`} />
          <ResultBox label={t('tools:positionSize.stopDistance')} value={`$${stopDist.toFixed(2)}`} />
          <ResultBox label={t('tools:positionSize.result')} value={`${positionSize.toFixed(2)} oz`} highlight />
          <ResultBox label={t('tools:positionSize.positionValue')} value={`$${positionValue.toFixed(2)}`} highlight />
        </div>
      )}
    </div>
  )
}

function PnLCalc() {
  const { t } = useTranslation(['tools', 'common'])
  const [entry, setEntry] = useState('')
  const [exit, setExit] = useState('')
  const [amount, setAmount] = useState('')
  const [direction, setDirection] = useState('long')
  const [leverage, setLeverage] = useState('1')

  const entryNum = parseFloat(entry) || 0
  const exitNum = parseFloat(exit) || 0
  const amountNum = parseFloat(amount) || 0
  const leverageNum = parseFloat(leverage) || 1

  let pnl = 0
  let pnlPct = 0
  if (entryNum > 0 && exitNum > 0) {
    const diff = direction === 'long' ? exitNum - entryNum : entryNum - exitNum
    pnlPct = (diff / entryNum) * 100 * leverageNum
    pnl = amountNum * (pnlPct / 100)
  }

  const liqPrice = direction === 'long'
    ? entryNum * (1 - 1 / leverageNum)
    : entryNum * (1 + 1 / leverageNum)

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">{t('tools:pnl.title').toUpperCase()}</h3>
      <div className="flex gap-1 mb-3">
        {['long', 'short'].map(d => (
          <button key={d} onClick={() => setDirection(d)}
            className={`flex-1 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              direction === d
                ? d === 'long' ? 'bg-accent-green/20 text-accent-green border border-accent-green/30' : 'bg-accent-red/20 text-accent-red border border-accent-red/30'
                : 'text-text-muted border border-white/5'
            }`}>
            {d === 'long' ? t('tools:pnl.long').toUpperCase() : t('tools:pnl.short').toUpperCase()}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div>
          <label className="text-text-muted text-[10px]">{t('tools:pnl.entryPrice')}</label>
          <input type="number" value={entry} onChange={e => setEntry(e.target.value)}
            placeholder="2900" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">{t('tools:pnl.exitPrice')}</label>
          <input type="number" value={exit} onChange={e => setExit(e.target.value)}
            placeholder="3000" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">{t('tools:pnl.positionSize')}</label>
          <input type="number" value={amount} onChange={e => setAmount(e.target.value)}
            placeholder="1000" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">{t('tools:pnl.leverage')}</label>
          <input type="number" value={leverage} onChange={e => setLeverage(e.target.value)}
            placeholder="1" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
      </div>
      {entryNum > 0 && exitNum > 0 && (
        <div className="grid grid-cols-2 gap-2">
          <ResultBox label={t('tools:pnl.pnl')} value={`${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}`}
            color={pnl >= 0 ? 'text-accent-green' : 'text-accent-red'} highlight />
          <ResultBox label={t('tools:pnl.roi')} value={`${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%`}
            color={pnlPct >= 0 ? 'text-accent-green' : 'text-accent-red'} highlight />
          {leverageNum > 1 && (
            <ResultBox label={t('common:trade.liqPrice')} value={`$${liqPrice.toFixed(2)}`} color="text-accent-red" />
          )}
          <ResultBox label={t('tools:pnl.breakEven')} value={`$${entryNum.toFixed(2)}`} />
        </div>
      )}
    </div>
  )
}

function RiskRewardCalc() {
  const { t } = useTranslation(['tools', 'common'])
  const [entry, setEntry] = useState('')
  const [target, setTarget] = useState('')
  const [stopLoss, setStopLoss] = useState('')

  const entryNum = parseFloat(entry) || 0
  const targetNum = parseFloat(target) || 0
  const slNum = parseFloat(stopLoss) || 0

  const reward = Math.abs(targetNum - entryNum)
  const risk = Math.abs(entryNum - slNum)
  const rrRatio = risk > 0 ? reward / risk : 0
  const winRateNeeded = risk > 0 ? (1 / (1 + rrRatio)) * 100 : 0

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">{t('tools:riskReward.title').toUpperCase()}</h3>
      <p className="text-text-muted text-[10px] mb-3">
        {t('tools:riskReward.description')}
      </p>
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div>
          <label className="text-text-muted text-[10px]">{t('tools:riskReward.entryPrice')}</label>
          <input type="number" value={entry} onChange={e => setEntry(e.target.value)}
            placeholder="2900" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">{t('tools:riskReward.takeProfit')}</label>
          <input type="number" value={target} onChange={e => setTarget(e.target.value)}
            placeholder="3050" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">{t('tools:riskReward.stopLoss')}</label>
          <input type="number" value={stopLoss} onChange={e => setStopLoss(e.target.value)}
            placeholder="2850" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
      </div>
      {entryNum > 0 && targetNum > 0 && slNum > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="flex-1 h-3 bg-accent-red/20 rounded-full overflow-hidden">
              <div className="h-full bg-accent-red rounded-full" style={{ width: `${Math.min(risk / (risk + reward) * 100, 100)}%` }} />
            </div>
            <span className="text-accent-red text-[10px] font-bold w-16 text-right">-${risk.toFixed(0)}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-3 bg-accent-green/20 rounded-full overflow-hidden">
              <div className="h-full bg-accent-green rounded-full" style={{ width: `${Math.min(reward / (risk + reward) * 100, 100)}%` }} />
            </div>
            <span className="text-accent-green text-[10px] font-bold w-16 text-right">+${reward.toFixed(0)}</span>
          </div>
          <div className="grid grid-cols-3 gap-2 mt-2">
            <ResultBox label={t('tools:riskReward.ratio')}
              value={`1:${rrRatio.toFixed(2)}`}
              color={rrRatio >= 2 ? 'text-accent-green' : rrRatio >= 1 ? 'text-accent-goldBright' : 'text-accent-red'}
              highlight />
            <ResultBox label={t('tools:riskReward.winRateNeeded')} value={`${winRateNeeded.toFixed(1)}%`} />
            <ResultBox label={t('tools:riskReward.quality')}
              value={rrRatio >= 3 ? t('tools:riskReward.qualityExcellent') : rrRatio >= 2 ? t('tools:riskReward.qualityGood') : rrRatio >= 1 ? t('tools:riskReward.qualityFair') : t('tools:riskReward.qualityPoor')}
              color={rrRatio >= 2 ? 'text-accent-green' : rrRatio >= 1 ? 'text-accent-goldBright' : 'text-accent-red'} />
          </div>
        </div>
      )}
    </div>
  )
}

function DCACalc() {
  const { t } = useTranslation(['tools', 'common'])
  const [investment, setInvestment] = useState('100')
  const [frequency, setFrequency] = useState('weekly')
  const [months, setMonths] = useState('12')
  const [currentPrice, setCurrentPrice] = useState('2900')

  const invNum = parseFloat(investment) || 0
  const monthsNum = parseInt(months) || 0
  const priceNum = parseFloat(currentPrice) || 0

  const freqMultiplier = { daily: 30, weekly: 4.33, biweekly: 2.17, monthly: 1 }
  const buysPerMonth = freqMultiplier[frequency] || 1
  const totalBuys = Math.round(buysPerMonth * monthsNum)
  const totalInvested = invNum * totalBuys
  const goldAccumulated = priceNum > 0 ? totalInvested / priceNum : 0

  // Simulate scenarios
  const scenarios = [
    { label: t('tools:dca.scenarioBear'), pct: -30, color: 'text-accent-red' },
    { label: t('tools:dca.scenarioFlat'), pct: 0, color: 'text-text-muted' },
    { label: t('tools:dca.scenarioBull'), pct: 50, color: 'text-accent-green' },
    { label: t('tools:dca.scenarioMoon'), pct: 100, color: 'text-accent-green' },
  ]

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">{t('tools:dca.title').toUpperCase()}</h3>
      <p className="text-text-muted text-[10px] mb-3">
        {t('tools:dca.description')}
      </p>
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div>
          <label className="text-text-muted text-[10px]">{t('tools:dca.investmentAmount')}</label>
          <input type="number" value={investment} onChange={e => setInvestment(e.target.value)}
            placeholder="100" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">{t('tools:dca.frequency')}</label>
          <select value={frequency} onChange={e => setFrequency(e.target.value)}
            className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5">
            <option value="daily">{t('tools:dca.daily')}</option>
            <option value="weekly">{t('tools:dca.weekly')}</option>
            <option value="biweekly">{t('tools:dca.biweekly')}</option>
            <option value="monthly">{t('tools:dca.monthly')}</option>
          </select>
        </div>
        <div>
          <label className="text-text-muted text-[10px]">{t('tools:dca.duration')}</label>
          <input type="number" value={months} onChange={e => setMonths(e.target.value)}
            placeholder="12" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">Gold Price ($)</label>
          <input type="number" value={currentPrice} onChange={e => setCurrentPrice(e.target.value)}
            placeholder="2900" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
      </div>
      {invNum > 0 && monthsNum > 0 && (
        <>
          <div className="grid grid-cols-3 gap-2 mb-3">
            <ResultBox label={t('tools:dca.totalInvested')} value={`$${totalInvested.toLocaleString()}`} />
            <ResultBox label={t('tools:dca.totalBuys')} value={totalBuys.toString()} />
            <ResultBox label={t('tools:dca.totalGold')} value={`${goldAccumulated.toFixed(6)}`} highlight />
          </div>
          <div className="text-text-muted text-[9px] font-semibold mb-1.5">{t('tools:dca.priceScenarios')}</div>
          <div className="grid grid-cols-2 gap-2">
            {scenarios.map(s => {
              const futurePrice = priceNum * (1 + s.pct / 100)
              const futureValue = goldAccumulated * futurePrice
              const pnl = futureValue - totalInvested
              return (
                <div key={s.label} className="bg-white/[0.02] rounded-lg p-2">
                  <div className="text-text-muted text-[9px]">{s.label}</div>
                  <div className={`text-xs font-bold ${s.color}`}>
                    ${futureValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </div>
                  <div className={`text-[9px] ${pnl >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                    {pnl >= 0 ? '+' : ''}{((pnl / totalInvested) * 100).toFixed(1)}%
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

function WeightConverter() {
  const [amount, setAmount] = useState('1')
  const [fromUnit, setFromUnit] = useState('troy_oz')
  const amountNum = parseFloat(amount) || 0

  // Conversion factors to grams
  const toGrams = {
    troy_oz: 31.1035,
    gram: 1,
    kg: 1000,
    tola: 11.6638,
    tael: 37.429,
    baht: 15.244,
  }
  const labels = {
    troy_oz: 'Troy Oz',
    gram: 'Grams',
    kg: 'Kilograms',
    tola: 'Tola',
    tael: 'Tael (HK)',
    baht: 'Baht (Thai)',
  }

  const baseGrams = amountNum * (toGrams[fromUnit] || 1)

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">GOLD WEIGHT CONVERTER</h3>
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div>
          <label className="text-text-muted text-[10px]">Amount</label>
          <input type="number" value={amount} onChange={e => setAmount(e.target.value)}
            placeholder="1" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">From Unit</label>
          <select value={fromUnit} onChange={e => setFromUnit(e.target.value)}
            className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5">
            {Object.entries(labels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
      </div>
      {amountNum > 0 && (
        <div className="grid grid-cols-3 gap-2">
          {Object.entries(toGrams).filter(([k]) => k !== fromUnit).map(([unit, factor]) => (
            <ResultBox key={unit} label={labels[unit]} value={(baseGrams / factor).toFixed(4)} />
          ))}
        </div>
      )}
    </div>
  )
}

function MeltValueCalc() {
  const [weight, setWeight] = useState('1')
  const [purity, setPurity] = useState('24')
  const [spotPrice, setSpotPrice] = useState('2900')

  const weightNum = parseFloat(weight) || 0
  const spotNum = parseFloat(spotPrice) || 0
  const purityMap = { '24': 0.999, '22': 0.9167, '18': 0.75, '14': 0.5833, '10': 0.4167 }
  const purityFactor = purityMap[purity] || 0.999
  const meltValue = weightNum * spotNum * purityFactor

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">GOLD MELT VALUE</h3>
      <p className="text-text-muted text-[10px] mb-3">Calculate the intrinsic gold value based on weight and purity.</p>
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div>
          <label className="text-text-muted text-[10px]">Weight (oz)</label>
          <input type="number" value={weight} onChange={e => setWeight(e.target.value)}
            placeholder="1" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">Karat</label>
          <select value={purity} onChange={e => setPurity(e.target.value)}
            className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5">
            <option value="24">24K (99.9%)</option>
            <option value="22">22K (91.7%)</option>
            <option value="18">18K (75%)</option>
            <option value="14">14K (58.3%)</option>
            <option value="10">10K (41.7%)</option>
          </select>
        </div>
        <div>
          <label className="text-text-muted text-[10px]">Spot $/oz</label>
          <input type="number" value={spotPrice} onChange={e => setSpotPrice(e.target.value)}
            placeholder="2900" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
      </div>
      {weightNum > 0 && spotNum > 0 && (
        <div className="grid grid-cols-2 gap-2">
          <ResultBox label="Melt Value" value={`$${meltValue.toFixed(2)}`} highlight />
          <ResultBox label="Pure Gold" value={`${(weightNum * purityFactor).toFixed(4)} oz`} />
        </div>
      )}
    </div>
  )
}

function PipValueCalc() {
  const [lotSize, setLotSize] = useState('1.0')
  const lotNum = parseFloat(lotSize) || 0
  // XAUUSD: 1 pip = $0.01, 1 lot = 100 oz
  const pipValue = lotNum * 100 * 0.01
  const tickValue = lotNum * 100 * 0.10

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">XAUUSD PIP VALUE</h3>
      <p className="text-text-muted text-[10px] mb-3">1 pip = $0.01 move. 1 standard lot = 100 troy ounces.</p>
      <div className="mb-3">
        <label className="text-text-muted text-[10px]">Lot Size</label>
        <input type="number" value={lotSize} onChange={e => setLotSize(e.target.value)} step="0.01"
          placeholder="1.0" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
      </div>
      {lotNum > 0 && (
        <div className="grid grid-cols-3 gap-2">
          <ResultBox label="Pip Value" value={`$${pipValue.toFixed(2)}`} highlight />
          <ResultBox label="10-pip Move" value={`$${(pipValue * 10).toFixed(2)}`} />
          <ResultBox label="$1 Move" value={`$${tickValue.toFixed(2)}`} highlight />
        </div>
      )}
    </div>
  )
}

function ResultBox({ label, value, color, highlight }) {
  return (
    <div className={`rounded-xl p-2.5 text-center ${highlight ? 'bg-accent-gold/5 border border-accent-gold/15' : 'bg-white/[0.02] border border-white/5'}`}>
      <div className="text-text-muted text-[9px] font-medium">{label}</div>
      <div className={`text-sm font-bold tabular-nums ${color || 'text-text-primary'}`}>{value}</div>
    </div>
  )
}

export default function Tools() {
  const { t } = useTranslation(['tools', 'common'])
  const [activeCalc, setActiveCalc] = useState('position')

  const calcs = [
    { key: 'position', label: t('tools:positionSize.title') },
    { key: 'pnl', label: t('tools:pnl.title') },
    { key: 'rr', label: t('tools:riskReward.title') },
    { key: 'dca', label: t('tools:dca.title') },
    { key: 'weight', label: 'Weight Convert' },
    { key: 'melt', label: 'Melt Value' },
    { key: 'pip', label: 'Pip Value' },
  ]

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      <SubTabBar tabs={MARKET_TABS.map(tab => ({ ...tab, label: t(tab.labelKey) }))} />
      <h1 className="text-lg font-bold">{t('tools:title')}</h1>

      {/* Calculator tabs — horizontally scrollable on mobile */}
      <div className="overflow-x-auto">
        <div className="flex gap-1 bg-bg-card rounded-xl p-1 border border-white/5 min-w-max">
          {calcs.map(c => (
            <button key={c.key} onClick={() => setActiveCalc(c.key)}
              className={`px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-all whitespace-nowrap ${
                activeCalc === c.key
                  ? 'bg-accent-gold/20 text-accent-gold border border-accent-gold/30'
                  : 'text-text-muted'
              }`}>
              {c.label}
            </button>
          ))}
        </div>
      </div>

      {activeCalc === 'position' && <PositionSizeCalc />}
      {activeCalc === 'pnl' && <PnLCalc />}
      {activeCalc === 'rr' && <RiskRewardCalc />}
      {activeCalc === 'dca' && <DCACalc />}
      {activeCalc === 'weight' && <WeightConverter />}
      {activeCalc === 'melt' && <MeltValueCalc />}
      {activeCalc === 'pip' && <PipValueCalc />}

      {/* Pro tips */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">{t('tools:proRules.title').toUpperCase()}</h3>
        <div className="space-y-2 text-[11px] text-text-muted">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="flex gap-2">
              <span className="text-accent-gold font-bold">{i}</span>
              <p>{t(`tools:proRules.rules.rule${i}`)}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Common mistakes */}
      <div className="bg-bg-card rounded-2xl p-4 border border-accent-red/10">
        <h3 className="text-accent-red text-xs font-semibold mb-3">{t('tools:mistakes.title').toUpperCase()}</h3>
        <div className="space-y-1.5 text-[11px] text-text-muted">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="flex items-start gap-2">
              <span className="text-accent-red mt-0.5">x</span>
              <p>{t(`tools:mistakes.items.item${i}`)}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
