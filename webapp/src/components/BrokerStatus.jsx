import { useTranslation } from 'react-i18next'
import { formatPricePrecise } from '../utils/format'

export default function BrokerStatus({ connected = false, balance = null }) {
  const { t } = useTranslation()

  return (
    <div className="flex items-center gap-2">
      <div
        className={`w-2.5 h-2.5 rounded-full shrink-0 ${connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}
      />
      <span className={`text-xs font-medium ${connected ? 'text-accent-green' : 'text-accent-red'}`}>
        {connected
          ? t('broker.connected', 'Connected')
          : t('broker.notConnected', 'Not Connected')
        }
      </span>
      {connected && balance != null && (
        <span className="text-text-muted text-[10px] ml-1 tabular-nums">
          {formatPricePrecise(balance)}
        </span>
      )}
    </div>
  )
}
