'use client'

import { Market } from '@/lib/types'
import { useMemo } from 'react'

interface StateMonitorProps {
  markets: Market[]
}

interface StateFeature {
  name: string
  value: number
  category: 'momentum' | 'order_flow' | 'microstructure' | 'volatility' | 'position' | 'regime'
}

export default function StateMonitor({ markets }: StateMonitorProps) {
  // Extract features from the first market (as example)
  const features = useMemo<StateFeature[]>(() => {
    if (markets.length === 0) return []

    const market = markets[0]
    const state = market.last_state

    if (!state) return []

    return [
      // Momentum
      { name: 'Returns 1m', value: state.returns_1m || 0, category: 'momentum' },
      { name: 'Returns 5m', value: state.returns_5m || 0, category: 'momentum' },
      { name: 'Returns 10m', value: state.returns_10m || 0, category: 'momentum' },
      
      // Order Flow
      { name: 'OB Imbalance L1', value: state.ob_imbalance_l1 || 0, category: 'order_flow' },
      { name: 'OB Imbalance L5', value: state.ob_imbalance_l5 || 0, category: 'order_flow' },
      { name: 'Trade Flow', value: state.trade_flow || 0, category: 'order_flow' },
      { name: 'CVD Accel', value: state.cvd_accel || 0, category: 'order_flow' },
      
      // Microstructure
      { name: 'Spread %', value: state.spread_pct || 0, category: 'microstructure' },
      { name: 'Trade Intensity', value: state.trade_intensity || 0, category: 'microstructure' },
      { name: 'Large Trade Flag', value: state.large_trade_flag || 0, category: 'microstructure' },
      
      // Volatility
      { name: 'Vol 5m', value: state.vol_5m || 0, category: 'volatility' },
      { name: 'Vol Expansion', value: state.vol_expansion || 0, category: 'volatility' },
      
      // Position
      { name: 'Has Position', value: state.has_position || 0, category: 'position' },
      { name: 'Position Side', value: state.position_side || 0, category: 'position' },
      { name: 'Position PnL', value: state.position_pnl || 0, category: 'position' },
      { name: 'Time Remaining', value: state.time_remaining || 0, category: 'position' },
      
      // Regime
      { name: 'Vol Regime', value: state.vol_regime || 0, category: 'regime' },
      { name: 'Trend Regime', value: state.trend_regime || 0, category: 'regime' },
    ]
  }, [markets])

  const categories = [
    { key: 'momentum', label: 'Momentum', color: 'blue' },
    { key: 'order_flow', label: 'Order Flow', color: 'purple' },
    { key: 'microstructure', label: 'Microstructure', color: 'cyan' },
    { key: 'volatility', label: 'Volatility', color: 'yellow' },
    { key: 'position', label: 'Position', color: 'green' },
    { key: 'regime', label: 'Regime', color: 'pink' },
  ] as const

  if (features.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500">
        <p>No state data available</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {categories.map((cat) => {
        const catFeatures = features.filter((f) => f.category === cat.key)
        if (catFeatures.length === 0) return null

        return (
          <div key={cat.key}>
            <h3 className={`text-sm font-semibold mb-3 text-${cat.color}-400`}>
              {cat.label}
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {catFeatures.map((feature) => (
                <div
                  key={feature.name}
                  className="bg-slate-800/50 rounded-lg p-3 border border-slate-700"
                >
                  <div className="text-xs text-slate-400 mb-1">
                    {feature.name}
                  </div>
                  <div className={`text-lg font-bold text-${cat.color}-400`}>
                    {feature.value.toFixed(3)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
