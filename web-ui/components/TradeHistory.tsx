'use client'

import { Trade } from '@/lib/types'
import { formatCurrency, formatPercent, formatTimestamp } from '@/lib/utils'

interface TradeHistoryProps {
  trades: Trade[]
}

export default function TradeHistory({ trades }: TradeHistoryProps) {
  if (trades.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500">
        <p>No trades yet</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-slate-700">
            <th className="text-left py-3 px-4 text-sm font-semibold text-slate-400">
              Time
            </th>
            <th className="text-left py-3 px-4 text-sm font-semibold text-slate-400">
              Asset
            </th>
            <th className="text-left py-3 px-4 text-sm font-semibold text-slate-400">
              Side
            </th>
            <th className="text-right py-3 px-4 text-sm font-semibold text-slate-400">
              Entry
            </th>
            <th className="text-right py-3 px-4 text-sm font-semibold text-slate-400">
              Exit
            </th>
            <th className="text-right py-3 px-4 text-sm font-semibold text-slate-400">
              Size
            </th>
            <th className="text-right py-3 px-4 text-sm font-semibold text-slate-400">
              PnL
            </th>
          </tr>
        </thead>
        <tbody>
          {trades.map((trade, idx) => (
            <tr
              key={idx}
              className="border-b border-slate-800 hover:bg-slate-800/30 transition-colors"
            >
              <td className="py-3 px-4 text-sm text-slate-300">
                {formatTimestamp(trade.exit_time)}
              </td>
              <td className="py-3 px-4 text-sm font-semibold text-slate-200">
                {trade.asset}
              </td>
              <td className="py-3 px-4">
                <span
                  className={`text-xs font-semibold px-2 py-1 rounded ${
                    trade.side === 'UP'
                      ? 'bg-green-900/30 text-green-400'
                      : 'bg-red-900/30 text-red-400'
                  }`}
                >
                  {trade.side}
                </span>
              </td>
              <td className="py-3 px-4 text-sm text-right text-slate-300">
                {formatPercent(trade.entry_prob * 100)}
              </td>
              <td className="py-3 px-4 text-sm text-right text-slate-300">
                {formatPercent(trade.exit_prob * 100)}
              </td>
              <td className="py-3 px-4 text-sm text-right text-slate-300">
                {formatCurrency(trade.size)}
              </td>
              <td
                className={`py-3 px-4 text-sm text-right font-semibold ${
                  trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'
                }`}
              >
                {formatCurrency(trade.pnl)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
