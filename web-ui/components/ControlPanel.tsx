'use client'

import { useState } from 'react'
import { formatCurrency } from '@/lib/utils'

interface ControlPanelProps {
  currentMode: 'train' | 'inference'
  currentSize: number
  enabledMarkets?: string[]
  onConfigUpdate: (mode: 'train' | 'inference', size: number, markets?: string[]) => void
}

const TRADE_SIZES = [50, 100, 250, 500, 1000]
const MARKETS = [
  { symbol: 'BTC', name: 'Bitcoin', color: 'orange' },
  { symbol: 'ETH', name: 'Ethereum', color: 'blue' },
  { symbol: 'SOL', name: 'Solana', color: 'purple' },
  { symbol: 'XRP', name: 'Ripple', color: 'cyan' },
]

export default function ControlPanel({ currentMode, currentSize, enabledMarkets = ['BTC', 'ETH', 'SOL', 'XRP'], onConfigUpdate }: ControlPanelProps) {
  const [mode, setMode] = useState<'train' | 'inference'>(currentMode)
  const [size, setSize] = useState<number>(currentSize)
  const [markets, setMarkets] = useState<string[]>(enabledMarkets)
  const [customSize, setCustomSize] = useState<string>('')
  const [showCustomInput, setShowCustomInput] = useState(false)
  const [isUpdating, setIsUpdating] = useState(false)
  const [updateStatus, setUpdateStatus] = useState<string | null>(null)

  const handleUpdate = async () => {
    setIsUpdating(true)
    setUpdateStatus(null)

    try {
      const response = await fetch('/api/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          mode, 
          trade_size: size,
          enabled_markets: markets 
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to update config')
      }

      const data = await response.json()
      onConfigUpdate(data.mode, data.trade_size, data.enabled_markets)
      setUpdateStatus('success')
      setTimeout(() => setUpdateStatus(null), 3000)
    } catch (error) {
      console.error('Config update error:', error)
      setUpdateStatus('error')
      setTimeout(() => setUpdateStatus(null), 3000)
    } finally {
      setIsUpdating(false)
    }
  }

  const handleSizeSelect = (selectedSize: number) => {
    setSize(selectedSize)
    setShowCustomInput(false)
    setCustomSize('')
  }

  const handleCustomSize = () => {
    const parsedSize = parseFloat(customSize)
    if (!isNaN(parsedSize) && parsedSize > 0 && parsedSize <= 10000) {
      setSize(parsedSize)
      setShowCustomInput(false)
      setCustomSize('')
    }
  }

  const toggleMarket = (symbol: string) => {
    if (markets.includes(symbol)) {
      // Don't allow disabling all markets
      if (markets.length > 1) {
        setMarkets(markets.filter(m => m !== symbol))
      }
    } else {
      setMarkets([...markets, symbol])
    }
  }

  const hasChanges = () => {
    return mode !== currentMode || 
           size !== currentSize || 
           JSON.stringify(markets.sort()) !== JSON.stringify(enabledMarkets.sort())
  }

  return (
    <div className="glass rounded-xl p-6">
      <h2 className="text-xl font-semibold mb-4 text-slate-200">Bot Controls</h2>
      
      <div className="space-y-6">
        {/* Mode Selection */}
        <div>
          <label className="block text-sm font-medium text-slate-400 mb-2">
            Mode
          </label>
          <div className="flex gap-3">
            <button
              onClick={() => setMode('train')}
              className={`flex-1 px-4 py-3 rounded-lg font-semibold transition-all ${
                mode === 'train'
                  ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/30'
                  : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
              }`}
            >
              <div className="text-sm">Training</div>
              <div className="text-xs opacity-75 mt-1">Learn from trades</div>
            </button>
            <button
              onClick={() => setMode('inference')}
              className={`flex-1 px-4 py-3 rounded-lg font-semibold transition-all ${
                mode === 'inference'
                  ? 'bg-purple-500 text-white shadow-lg shadow-purple-500/30'
                  : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
              }`}
            >
              <div className="text-sm">Inference</div>
              <div className="text-xs opacity-75 mt-1">Use trained model</div>
            </button>
          </div>
        </div>

        {/* Market Selection */}
        <div>
          <label className="block text-sm font-medium text-slate-400 mb-2">
            Active Markets
          </label>
          <div className="grid grid-cols-2 gap-2">
            {MARKETS.map((market) => {
              const isEnabled = markets.includes(market.symbol)
              const isOnlyOne = markets.length === 1 && isEnabled
              
              return (
                <button
                  key={market.symbol}
                  onClick={() => toggleMarket(market.symbol)}
                  disabled={isOnlyOne}
                  className={`px-4 py-3 rounded-lg font-semibold transition-all flex items-center justify-between ${
                    isEnabled
                      ? `bg-${market.color}-500 text-white shadow-lg shadow-${market.color}-500/30`
                      : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
                  } ${isOnlyOne ? 'opacity-50 cursor-not-allowed' : ''}`}
                  style={{
                    backgroundColor: isEnabled ? 
                      (market.color === 'orange' ? '#f97316' : 
                       market.color === 'blue' ? '#3b82f6' : 
                       market.color === 'purple' ? '#a855f7' : '#06b6d4') : undefined,
                    boxShadow: isEnabled ? 
                      (market.color === 'orange' ? '0 10px 25px -5px rgba(249, 115, 22, 0.3)' : 
                       market.color === 'blue' ? '0 10px 25px -5px rgba(59, 130, 246, 0.3)' : 
                       market.color === 'purple' ? '0 10px 25px -5px rgba(168, 85, 247, 0.3)' : '0 10px 25px -5px rgba(6, 182, 212, 0.3)') : undefined
                  }}
                >
                  <div>
                    <div className="text-sm">{market.symbol}</div>
                    <div className="text-xs opacity-75">{market.name}</div>
                  </div>
                  <div className="text-lg">
                    {isEnabled ? '✓' : '○'}
                  </div>
                </button>
              )
            })}
          </div>
          <p className="text-xs text-slate-500 mt-2">
            {markets.length} market{markets.length !== 1 ? 's' : ''} active • Max exposure: {formatCurrency(size * markets.length)}
          </p>
        </div>

        {/* Trade Size Selection */}
        <div>
          <label className="block text-sm font-medium text-slate-400 mb-2">
            Trade Size (per position)
          </label>
          <div className="grid grid-cols-3 gap-2 mb-2">
            {TRADE_SIZES.map((tradeSize) => (
              <button
                key={tradeSize}
                onClick={() => handleSizeSelect(tradeSize)}
                className={`px-4 py-3 rounded-lg font-semibold transition-all ${
                  size === tradeSize
                    ? 'bg-green-500 text-white shadow-lg shadow-green-500/30'
                    : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
                }`}
              >
                {formatCurrency(tradeSize)}
              </button>
            ))}
            <button
              onClick={() => setShowCustomInput(!showCustomInput)}
              className={`px-4 py-3 rounded-lg font-semibold transition-all ${
                showCustomInput
                  ? 'bg-yellow-500 text-white shadow-lg shadow-yellow-500/30'
                  : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
              }`}
            >
              Custom
            </button>
          </div>

          {/* Custom Size Input */}
          {showCustomInput && (
            <div className="flex gap-2 mt-2">
              <input
                type="number"
                value={customSize}
                onChange={(e) => setCustomSize(e.target.value)}
                placeholder="Enter amount"
                min="1"
                max="10000"
                className="flex-1 px-4 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
              />
              <button
                onClick={handleCustomSize}
                disabled={!customSize || parseFloat(customSize) <= 0}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg font-semibold hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                Set
              </button>
            </div>
          )}

          {/* Current Selection Display */}
          <div className="mt-3 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">Per Market:</span>
              <span className="text-lg font-bold text-green-400">{formatCurrency(size)}</span>
            </div>
            <div className="flex items-center justify-between mt-1">
              <span className="text-xs text-slate-500">Max Exposure ({markets.length} markets):</span>
              <span className="text-sm font-semibold text-yellow-400">{formatCurrency(size * markets.length)}</span>
            </div>
          </div>
        </div>

        {/* Update Button */}
        <button
          onClick={handleUpdate}
          disabled={isUpdating || !hasChanges()}
          className={`w-full px-6 py-3 rounded-lg font-semibold transition-all ${
            isUpdating
              ? 'bg-slate-600 cursor-wait'
              : !hasChanges()
              ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
              : 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white hover:from-blue-600 hover:to-cyan-600 shadow-lg'
          }`}
        >
          {isUpdating ? (
            <span className="flex items-center justify-center gap-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
              Updating...
            </span>
          ) : !hasChanges() ? (
            'No Changes'
          ) : (
            'Apply Changes'
          )}
        </button>

        {/* Status Message */}
        {updateStatus && (
          <div
            className={`p-3 rounded-lg text-sm font-medium text-center ${
              updateStatus === 'success'
                ? 'bg-green-900/30 border border-green-500/50 text-green-400'
                : 'bg-red-900/30 border border-red-500/50 text-red-400'
            }`}
          >
            {updateStatus === 'success'
              ? '✓ Configuration updated successfully'
              : '✗ Failed to update configuration'}
          </div>
        )}

        {/* Info Box */}
        <div className="p-4 bg-blue-900/20 border border-blue-500/30 rounded-lg">
          <h3 className="text-sm font-semibold text-blue-400 mb-2">Configuration Info</h3>
          <ul className="text-xs text-slate-400 space-y-1">
            <li>• Each enabled market uses the specified trade size</li>
            <li>• Bot trades {markets.length} concurrent market{markets.length !== 1 ? 's' : ''} (15-min windows)</li>
            <li>• Larger sizes = higher potential profit and risk</li>
            <li>• At least one market must remain enabled</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
