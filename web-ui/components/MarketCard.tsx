'use client'

import { Market } from '@/lib/types'
import { formatCurrency, formatPercent, formatTimeRemaining } from '@/lib/utils'

interface MarketCardProps {
  market: Market
}

export default function MarketCard({ market }: MarketCardProps) {
  const timeRemaining = formatTimeRemaining(market.end_date)
  const hasPosition = market.position !== null
  const unrealizedPnL = market.unrealized_pnl || 0

  return (
    <div className="glass rounded-xl p-6 hover:bg-slate-800/30 transition-all">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-100">
            {market.asset}
          </h3>
          <p className="text-sm text-slate-400 mt-1">
            {market.question}
          </p>
        </div>
        <div className="text-right">
          <div className="text-xs text-slate-500">Expires in</div>
          <div className="text-sm font-semibold text-yellow-400">
            {timeRemaining}
          </div>
        </div>
      </div>

      {/* Current Prices */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-3">
          <div className="text-xs text-green-400 mb-1">UP Token</div>
          <div className="text-2xl font-bold text-green-300">
            {formatPercent(market.prob_up * 100)}
          </div>
        </div>
        <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3">
          <div className="text-xs text-red-400 mb-1">DOWN Token</div>
          <div className="text-2xl font-bold text-red-300">
            {formatPercent(market.prob_down * 100)}
          </div>
        </div>
      </div>

      {/* Position Info */}
      {hasPosition && market.position ? (
        <div className="border-t border-slate-700 pt-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-slate-400">Position</span>
            <span
              className={`text-sm font-semibold px-2 py-1 rounded ${
                market.position.side === 'UP'
                  ? 'bg-green-900/30 text-green-400'
                  : 'bg-red-900/30 text-red-400'
              }`}
            >
              {market.position.side}
            </span>
          </div>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">Entry:</span>
              <span className="text-slate-200">
                {formatPercent(market.position.entry_prob * 100)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Size:</span>
              <span className="text-slate-200">
                {formatCurrency(market.position.size)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Unrealized PnL:</span>
              <span
                className={`font-semibold ${
                  unrealizedPnL >= 0 ? 'text-green-400' : 'text-red-400'
                }`}
              >
                {formatCurrency(unrealizedPnL)}
              </span>
            </div>
          </div>
        </div>
      ) : (
        <div className="border-t border-slate-700 pt-4 text-center">
          <span className="text-sm text-slate-500">No active position</span>
        </div>
      )}

      {/* Last Action */}
      {market.last_action && (
        <div className="mt-3 pt-3 border-t border-slate-700">
          <div className="text-xs text-slate-500">Last Action</div>
          <div className="text-sm text-slate-300 mt-1">
            <span className="font-semibold text-blue-400">
              {market.last_action.action}
            </span>
            {market.last_action.confidence && (
              <span className="text-slate-400 ml-2">
                ({formatPercent(market.last_action.confidence * 100)} confidence)
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
