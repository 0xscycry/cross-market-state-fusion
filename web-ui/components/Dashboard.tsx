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
        <div className="glass rounded-xl p-6 hover:shadow-lg hover:shadow-blue-500/10 transition-all">
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

        <div className="glass rounded-xl p-6 hover:shadow-lg hover:shadow-blue-500/10 transition-all">
          <div className="text-sm text-slate-400 mb-1">Win Rate</div>
          <div className="text-3xl font-bold text-blue-400">
            {formatPercent(stats.win_rate)}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {stats.num_wins} / {stats.num_trades} trades
          </div>
        </div>

        <div className="glass rounded-xl p-6 hover:shadow-lg hover:shadow-blue-500/10 transition-all">
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

        <div className="glass rounded-xl p-6 hover:shadow-lg hover:shadow-blue-500/10 transition-all">
          <div className="text-sm text-slate-400 mb-1">Position Sizing</div>
          <div className="text-3xl font-bold text-cyan-400">
            {formatCurrency(status.trade_size)}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Max Exposure: {formatCurrency(stats.max_exposure)}
          </div>
        </div>
      </div>

      {/* Performance Chart */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-xl font-semibold mb-4 text-slate-200 flex items-center gap-2">
          <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
          </svg>
          Equity Curve
        </h2>
        <PerformanceChart history={status.pnl_history} />
      </div>

      {/* Active Markets */}
      <div>
        <h2 className="text-xl font-semibold mb-4 text-slate-200 flex items-center gap-2">
          <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
          Active Markets
          <span className="text-sm font-normal text-slate-400">({status.markets.length})</span>
        </h2>
        {status.markets.length === 0 ? (
          <div className="glass rounded-xl p-12 text-center">
            <div className="text-slate-500 mb-2">
              <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
              </svg>
            </div>
            <p className="text-lg text-slate-400">No active markets</p>
            <p className="text-sm text-slate-500 mt-1">Waiting for 15-minute binary markets to become available</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {status.markets.map((market) => (
              <MarketCard key={market.condition_id} market={market} />
            ))}
          </div>
        )}
      </div>

      {/* State Monitor */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-xl font-semibold mb-4 text-slate-200 flex items-center gap-2">
          <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Model State
          <span className="text-sm font-normal text-slate-400">(18-dimensional)</span>
        </h2>
        <StateMonitor markets={status.markets} />
      </div>

      {/* Recent Trades */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-xl font-semibold mb-4 text-slate-200 flex items-center gap-2">
          <svg className="w-5 h-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
          </svg>
          Recent Trades
        </h2>
        <TradeHistory trades={status.recent_trades} />
      </div>

      {/* Training Stats (if in training mode) */}
      {status.mode === 'train' && status.training_stats && (
        <div className="glass rounded-xl p-6">
          <h2 className="text-xl font-semibold mb-4 text-slate-200 flex items-center gap-2">
            <svg className="w-5 h-5 text-pink-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            Training Progress
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
              <div className="text-sm text-slate-400 mb-1">Update</div>
              <div className="text-2xl font-bold text-blue-400">
                {status.training_stats.update}
              </div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
              <div className="text-sm text-slate-400 mb-1">Policy Loss</div>
              <div className="text-2xl font-bold text-purple-400">
                {status.training_stats.policy_loss.toFixed(4)}
              </div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
              <div className="text-sm text-slate-400 mb-1">Value Loss</div>
              <div className="text-2xl font-bold text-pink-400">
                {status.training_stats.value_loss.toFixed(4)}
              </div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
              <div className="text-sm text-slate-400 mb-1">Entropy</div>
              <div className="text-2xl font-bold text-cyan-400">
                {status.training_stats.entropy.toFixed(3)}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                {status.training_stats.entropy > 1.0 ? 'Healthy' : 'Low'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
