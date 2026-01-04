'use client'

import { useState } from 'react'
import { formatCurrency } from '@/lib/utils'

interface ControlPanelProps {
  currentMode: 'train' | 'inference'
  currentSize: number
  onConfigUpdate: (mode: 'train' | 'inference', size: number) => void
}

const TRADE_SIZES = [50, 100, 250, 500, 1000]

export default function ControlPanel({ currentMode, currentSize, onConfigUpdate }: ControlPanelProps) {
  const [mode, setMode] = useState<'train' | 'inference'>(currentMode)
  const [size, setSize] = useState<number>(currentSize)
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
        body: JSON.stringify({ mode, trade_size: size }),
      })

      if (!response.ok) {
        throw new Error('Failed to update config')
      }

      const data = await response.json()
      onConfigUpdate(data.mode, data.trade_size)
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
              <span className="text-sm text-slate-400">Current Size:</span>
              <span className="text-lg font-bold text-green-400">{formatCurrency(size)}</span>
            </div>
            <div className="flex items-center justify-between mt-1">
              <span className="text-xs text-slate-500">Max Exposure (4 markets):</span>
              <span className="text-sm font-semibold text-yellow-400">{formatCurrency(size * 4)}</span>
            </div>
          </div>
        </div>

        {/* Update Button */}
        <button
          onClick={handleUpdate}
          disabled={isUpdating || (mode === currentMode && size === currentSize)}
          className={`w-full px-6 py-3 rounded-lg font-semibold transition-all ${
            isUpdating
              ? 'bg-slate-600 cursor-wait'
              : mode === currentMode && size === currentSize
              ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
              : 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white hover:from-blue-600 hover:to-cyan-600 shadow-lg'
          }`}
        >
          {isUpdating ? (
            <span className="flex items-center justify-center gap-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
              Updating...
            </span>
          ) : mode === currentMode && size === currentSize ? (
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
          <h3 className="text-sm font-semibold text-blue-400 mb-2">Trade Sizing Info</h3>
          <ul className="text-xs text-slate-400 space-y-1">
            <li>• Each position uses the specified trade size</li>
            <li>• Bot can have up to 4 concurrent positions (one per market)</li>
            <li>• Larger sizes = higher potential profit and risk</li>
            <li>• Recommended: Start with $50-100 for testing</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
