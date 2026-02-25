import { useState } from 'react'
import { useTranslation } from 'react-i18next'

const MODES = ['manual', 'semi-auto', 'auto']

export default function TradeControls({ onExecute, disabled = false }) {
  const { t } = useTranslation()
  const [direction, setDirection] = useState('BUY')
  const [lotSize, setLotSize] = useState('0.01')
  const [stopLoss, setStopLoss] = useState('')
  const [takeProfit, setTakeProfit] = useState('')
  const [mode, setMode] = useState('manual')

  const handleExecute = () => {
    if (onExecute) {
      onExecute({
        direction,
        lot_size: parseFloat(lotSize),
        stop_loss: stopLoss ? parseFloat(stopLoss) : null,
        take_profit: takeProfit ? parseFloat(takeProfit) : null,
        mode,
      })
    }
  }

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 space-y-3">
      <h4 className="text-text-primary text-sm font-semibold">
        {t('tradeControls.title', 'Trade Execution')}
      </h4>

      {/* Direction toggle */}
      <div className="flex rounded-xl overflow-hidden border border-white/10">
        <button
          onClick={() => setDirection('BUY')}
          className={`flex-1 py-2 text-xs font-bold transition-all ${
            direction === 'BUY'
              ? 'bg-accent-green text-white'
              : 'bg-bg-secondary text-text-muted hover:text-text-primary'
          }`}
        >
          {t('tradeControls.buy', 'BUY')}
        </button>
        <button
          onClick={() => setDirection('SELL')}
          className={`flex-1 py-2 text-xs font-bold transition-all ${
            direction === 'SELL'
              ? 'bg-accent-red text-white'
              : 'bg-bg-secondary text-text-muted hover:text-text-primary'
          }`}
        >
          {t('tradeControls.sell', 'SELL')}
        </button>
      </div>

      {/* Lot size */}
      <div>
        <label className="text-text-muted text-[10px] mb-1 block">{t('tradeControls.lotSize', 'Lot Size')}</label>
        <input
          type="number"
          step="0.01"
          min="0.01"
          value={lotSize}
          onChange={(e) => setLotSize(e.target.value)}
          className="w-full bg-bg-secondary border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary tabular-nums focus:outline-none focus:border-accent-gold/50"
        />
      </div>

      {/* SL / TP */}
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-text-muted text-[10px] mb-1 block">{t('tradeControls.sl', 'Stop Loss')}</label>
          <input
            type="number"
            step="0.1"
            value={stopLoss}
            onChange={(e) => setStopLoss(e.target.value)}
            placeholder="--"
            className="w-full bg-bg-secondary border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary tabular-nums focus:outline-none focus:border-accent-red/50"
          />
        </div>
        <div>
          <label className="text-text-muted text-[10px] mb-1 block">{t('tradeControls.tp', 'Take Profit')}</label>
          <input
            type="number"
            step="0.1"
            value={takeProfit}
            onChange={(e) => setTakeProfit(e.target.value)}
            placeholder="--"
            className="w-full bg-bg-secondary border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary tabular-nums focus:outline-none focus:border-accent-green/50"
          />
        </div>
      </div>

      {/* Mode selector */}
      <div>
        <label className="text-text-muted text-[10px] mb-1 block">{t('tradeControls.mode', 'Execution Mode')}</label>
        <div className="flex rounded-lg overflow-hidden border border-white/10">
          {MODES.map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`flex-1 py-1.5 text-[10px] font-medium capitalize transition-all ${
                mode === m
                  ? 'bg-accent-gold/20 text-accent-goldBright border-accent-gold/30'
                  : 'bg-bg-secondary text-text-muted hover:text-text-primary'
              }`}
            >
              {t(`tradeControls.${m}`, m)}
            </button>
          ))}
        </div>
      </div>

      {/* Execute button */}
      <button
        onClick={handleExecute}
        disabled={disabled}
        className={`w-full py-3 rounded-xl text-sm font-bold transition-all active:scale-95 ${
          direction === 'BUY'
            ? 'bg-accent-green text-white hover:bg-accent-green/90'
            : 'bg-accent-red text-white hover:bg-accent-red/90'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        {t('tradeControls.execute', 'Execute')} {direction}
      </button>
    </div>
  )
}
