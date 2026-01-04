'use client'

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { formatCurrency, formatTimestamp } from '@/lib/utils'

interface PerformanceChartProps {
  history: Array<{ timestamp: string; pnl: number }>
}

export default function PerformanceChart({ history }: PerformanceChartProps) {
  if (history.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500">
        <p>No trading history yet</p>
      </div>
    )
  }

  // Transform data for recharts
  const data = history.map((point) => ({
    time: new Date(point.timestamp).getTime(),
    pnl: point.pnl,
  }))

  // Calculate cumulative PnL
  let cumulative = 0
  const cumulativeData = data.map((point) => {
    cumulative += point.pnl
    return {
      ...point,
      cumulative,
    }
  })

  const maxPnL = Math.max(...cumulativeData.map((d) => d.cumulative))
  const minPnL = Math.min(...cumulativeData.map((d) => d.cumulative))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={cumulativeData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis
          dataKey="time"
          type="number"
          domain={['dataMin', 'dataMax']}
          tickFormatter={(timestamp) => formatTimestamp(timestamp, 'short')}
          stroke="#64748b"
          style={{ fontSize: '12px' }}
        />
        <YAxis
          domain={[minPnL * 1.1, maxPnL * 1.1]}
          tickFormatter={(value) => formatCurrency(value)}
          stroke="#64748b"
          style={{ fontSize: '12px' }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '8px',
            color: '#e2e8f0',
          }}
          formatter={(value: number) => [formatCurrency(value), 'Cumulative PnL']}
          labelFormatter={(timestamp) => formatTimestamp(timestamp)}
        />
        <Line
          type="monotone"
          dataKey="cumulative"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: '#3b82f6' }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
