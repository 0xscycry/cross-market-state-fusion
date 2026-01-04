'use client'

import { BotStatus } from '@/lib/types'
import MarketCard from './MarketCard'
import TradeHistory from './TradeHistory'
import PerformanceChart from './PerformanceChart'
import StateMonitor from './StateMonitor'
import { formatCurrency, formatPercent } from '@/lib/utils'

interface DashboardProps {
  status: BotStatus
}

export default function Dashboard({ status }: DashboardProps) {
  const stats = status.performance
  const roi = stats.max_exposure > 0 ? (stats.total_pnl / stats.max_exposure) * 100 : 0

  return (
    <div className="space-y-6">
      {/* Performance Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass rounded-xl p-6">
          <div className="text-sm text-slate-400 mb-1">Total PnL</div>
          <div
            className={`text-3xl font-bold ${
              stats.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'
            }`}
          >
            {formatCurrency(stats.total_pnl)}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            ROI: {formatPercent(roi)}
          </div>
        </div>

        <div className="glass rounded-xl p-6">
          <div className="text-sm text-slate-400 mb-1">Win Rate</div>
          <div className="text-3xl font-bold text-blue-400">
            {formatPercent(stats.win_rate)}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {stats.num_wins} / {stats.num_trades} trades
          </div>
        </div>

        <div className="glass rounded-xl p-6">
          <div className="text-sm text-slate-400 mb-1">Avg Trade</div>
          <div
            className={`text-3xl font-bold ${
              stats.avg_pnl >= 0 ? 'text-green-400' : 'text-red-400'
            }`}
          >
            {formatCurrency(stats.avg_pnl)}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Win: {formatCurrency(stats.avg_win)} | Loss: {formatCurrency(stats.avg_loss)}
          </div>
        </div>

        <div className="glass rounded-xl p-6">
          <div className="text-sm text-slate-400 mb-1">Exposure</div>
          <div className="text-3xl font-bold text-yellow-400">
            {formatCurrency(stats.max_exposure)}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Trade size: {formatCurrency(status.trade_size)}
          </div>
        </div>
      </div>

      {/* Performance Chart */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-xl font-semibold mb-4 text-slate-200">Equity Curve</h2>
        <PerformanceChart history={status.pnl_history} />
      </div>

      {/* Active Markets */}
      <div>
        <h2 className="text-xl font-semibold mb-4 text-slate-200">
          Active Markets ({status.markets.length})
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {status.markets.map((market) => (
            <MarketCard key={market.condition_id} market={market} />
          ))}
        </div>
      </div>

      {/* State Monitor */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-xl font-semibold mb-4 text-slate-200">
          Model State (18-dimensional)
        </h2>
        <StateMonitor markets={status.markets} />
      </div>

      {/* Recent Trades */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-xl font-semibold mb-4 text-slate-200">
          Recent Trades
        </h2>
        <TradeHistory trades={status.recent_trades} />
      </div>

      {/* Training Stats (if in training mode) */}
      {status.mode === 'train' && status.training_stats && (
        <div className="glass rounded-xl p-6">
          <h2 className="text-xl font-semibold mb-4 text-slate-200">
            Training Progress
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-sm text-slate-400">Update</div>
              <div className="text-2xl font-bold text-blue-400">
                {status.training_stats.update}
              </div>
            </div>
            <div>
              <div className="text-sm text-slate-400">Policy Loss</div>
              <div className="text-2xl font-bold text-purple-400">
                {status.training_stats.policy_loss.toFixed(4)}
              </div>
            </div>
            <div>
              <div className="text-sm text-slate-400">Value Loss</div>
              <div className="text-2xl font-bold text-pink-400">
                {status.training_stats.value_loss.toFixed(4)}
              </div>
            </div>
            <div>
              <div className="text-sm text-slate-400">Entropy</div>
              <div className="text-2xl font-bold text-cyan-400">
                {status.training_stats.entropy.toFixed(3)}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
