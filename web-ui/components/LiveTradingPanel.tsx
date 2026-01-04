'use client'

import { useState, useEffect } from 'react'
import { LiveTradingStatus, RiskLimits } from '@/lib/live-trading-types'

interface LiveTradingPanelProps {
  onToggle?: (enabled: boolean) => void
}

export default function LiveTradingPanel({ onToggle }: LiveTradingPanelProps) {
  const [status, setStatus] = useState<LiveTradingStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showRiskConfig, setShowRiskConfig] = useState(false)
  const [showApiConfig, setShowApiConfig] = useState(false)
  const [editingLimits, setEditingLimits] = useState<Partial<RiskLimits>>({})
  
  // API Key configuration
  const [apiKey, setApiKey] = useState('')
  const [privateKey, setPrivateKey] = useState('')
  const [showPrivateKey, setShowPrivateKey] = useState(false)
  const [savingCredentials, setSavingCredentials] = useState(false)

  // Fetch live trading status
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch('/api/live-trading')
        if (!response.ok) throw new Error('Failed to fetch status')
        const data = await response.json()
        setStatus(data)
        setError(null)
      } catch (err) {
        console.error('Error fetching live trading status:', err)
        setError(err instanceof Error ? err.message : 'Unknown error')
      }
    }

    fetchStatus()
    const interval = setInterval(fetchStatus, 5000) // Poll every 5s
    return () => clearInterval(interval)
  }, [])

  const handleToggleLiveTrading = async () => {
    if (!status) return

    setLoading(true)
    try {
      const newEnabled = !status.config.enabled
      const response = await fetch('/api/live-trading', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: newEnabled })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to toggle live trading')
      }

      const data = await response.json()
      setStatus(data)
      onToggle?.(newEnabled)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const handleSaveCredentials = async () => {
    if (!apiKey && !privateKey) {
      setError('Please enter at least one credential')
      return
    }

    setSavingCredentials(true)
    try {
      const response = await fetch('/api/live-trading', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          credentials: {
            api_key: apiKey || undefined,
            private_key: privateKey || undefined
          }
        })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to save credentials')
      }

      const data = await response.json()
      setStatus(data)
      setApiKey('')
      setPrivateKey('')
      setShowApiConfig(false)
      setError(null)
      alert('Credentials saved successfully! They are stored in environment variables.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setSavingCredentials(false)
    }
  }

  const handleUpdateRiskLimits = async () => {
    if (!status || Object.keys(editingLimits).length === 0) return

    setLoading(true)
    try {
      const response = await fetch('/api/live-trading', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ risk_limits: editingLimits })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to update risk limits')
      }

      const data = await response.json()
      setStatus(data)
      setEditingLimits({})
      setShowRiskConfig(false)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const handleResetCircuitBreaker = async () => {
    if (!confirm('Are you sure you want to reset the circuit breaker?')) return

    setLoading(true)
    try {
      const response = await fetch('/api/live-trading/reset-circuit-breaker', {
        method: 'POST'
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to reset circuit breaker')
      }

      const data = await response.json()
      setStatus(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  if (!status) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <div className="flex items-center gap-3">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500" />
          <span className="text-slate-300">Loading live trading status...</span>
        </div>
      </div>
    )
  }

  const isLive = status.config.mode === 'live' && status.config.enabled
  const isPaper = status.config.mode === 'paper'
  const isMock = status.config.executor_type === 'mock'

  return (
    <div className="space-y-4">
      {/* Header Card */}
      <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-lg p-6 border border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <span className={`w-3 h-3 rounded-full ${
                isLive ? 'bg-green-500 pulse-glow' : isPaper ? 'bg-yellow-500' : 'bg-slate-500'
              }`} />
              Live Trading Controls
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              {isLive ? 'Real orders on Polymarket CLOB' : isPaper ? 'Paper trading (simulated)' : 'Mock executor (testing)'}
            </p>
          </div>
          <button
            onClick={handleToggleLiveTrading}
            disabled={loading || !status.config.api_key_configured}
            className={`px-6 py-3 rounded-lg font-semibold transition-all flex items-center gap-2 ${
              isLive
                ? 'bg-red-600 hover:bg-red-700 text-white'
                : 'bg-green-600 hover:bg-green-700 text-white'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                <span>Processing...</span>
              </>
            ) : isLive ? (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                </svg>
                <span>Stop Live Trading</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Enable Live Trading</span>
              </>
            )}
          </button>
        </div>

        {/* Configuration Info */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
          <div className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-xs text-slate-400 uppercase">Mode</div>
            <div className="text-lg font-semibold text-white mt-1">
              {status.config.mode === 'live' ? '🔴 Live' : '📄 Paper'}
            </div>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-xs text-slate-400 uppercase">Executor</div>
            <div className="text-lg font-semibold text-white mt-1">
              {isMock ? '🧪 Mock' : '✅ Real'}
            </div>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-xs text-slate-400 uppercase">API Status</div>
            <div className="text-lg font-semibold text-white mt-1">
              {status.config.api_key_configured ? '✅ Ready' : '❌ Not Set'}
            </div>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-xs text-slate-400 uppercase">Trading</div>
            <div className="text-lg font-semibold text-white mt-1">
              {status.can_trade ? '✅ Allowed' : '🚫 Blocked'}
            </div>
          </div>
        </div>

        {!status.config.api_key_configured && (
          <div className="mt-4 p-3 bg-yellow-900/30 border border-yellow-500/50 rounded-lg">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="text-sm text-yellow-300">
                  ⚠️ API credentials not configured. Click "Configure API Keys" to set up your Polymarket CLOB credentials.
                </p>
              </div>
              <button
                onClick={() => setShowApiConfig(true)}
                className="ml-4 px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white text-sm rounded-lg font-semibold transition-all whitespace-nowrap"
              >
                Configure API Keys
              </button>
            </div>
          </div>
        )}

        {status.config.wallet_address && (
          <div className="mt-4 p-3 bg-slate-700/50 rounded-lg">
            <div className="text-xs text-slate-400 uppercase mb-1">Wallet Address</div>
            <div className="font-mono text-sm text-slate-300">{status.config.wallet_address}</div>
          </div>
        )}
      </div>

      {/* API Configuration Modal */}
      {showApiConfig && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-white">Configure Polymarket API Credentials</h3>
              <button
                onClick={() => setShowApiConfig(false)}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div className="p-4 bg-blue-900/30 border border-blue-500/50 rounded-lg">
                <p className="text-sm text-blue-300">
                  <strong>ℹ️ How to get credentials:</strong>
                </p>
                <ol className="text-sm text-blue-200 mt-2 space-y-1 list-decimal list-inside">
                  <li>Create a Polymarket account at <a href="https://polymarket.com" target="_blank" rel="noopener noreferrer" className="underline">polymarket.com</a></li>
                  <li>Go to Settings → API Keys to generate an API key</li>
                  <li>Your private key is your Ethereum wallet private key (used for signing orders)</li>
                  <li>Make sure your wallet is funded with USDC on Polygon network</li>
                </ol>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-300 mb-2">
                  Polymarket API Key
                </label>
                <input
                  type="text"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Enter your Polymarket API key"
                  className="w-full bg-slate-700 text-white rounded px-4 py-3 border border-slate-600 focus:border-blue-500 focus:outline-none font-mono text-sm"
                />
                <p className="text-xs text-slate-400 mt-1">
                  This is your Polymarket CLOB API key (looks like: pk_...)
                </p>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-300 mb-2">
                  Ethereum Private Key
                </label>
                <div className="relative">
                  <input
                    type={showPrivateKey ? 'text' : 'password'}
                    value={privateKey}
                    onChange={(e) => setPrivateKey(e.target.value)}
                    placeholder="0x..."
                    className="w-full bg-slate-700 text-white rounded px-4 py-3 border border-slate-600 focus:border-blue-500 focus:outline-none font-mono text-sm pr-12"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPrivateKey(!showPrivateKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors"
                  >
                    {showPrivateKey ? (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    )}
                  </button>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Your Ethereum wallet private key (starts with 0x...)
                </p>
              </div>

              <div className="p-4 bg-red-900/30 border border-red-500/50 rounded-lg">
                <p className="text-sm text-red-300">
                  <strong>⚠️ Security Warning:</strong> Never share your private key with anyone. These credentials will be stored in environment variables on the server. Make sure your server is secure.
                </p>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={handleSaveCredentials}
                  disabled={savingCredentials || (!apiKey && !privateKey)}
                  className="flex-1 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {savingCredentials ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span>Save Credentials</span>
                    </>
                  )}
                </button>
                <button
                  onClick={() => {
                    setShowApiConfig(false)
                    setApiKey('')
                    setPrivateKey('')
                  }}
                  className="px-4 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-semibold transition-all"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Risk State Card */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-white">Risk Status</h3>
          <div className="flex gap-2">
            {status.risk_state.circuit_breaker_active && (
              <button
                onClick={handleResetCircuitBreaker}
                disabled={loading}
                className="text-sm px-3 py-1 bg-orange-600 hover:bg-orange-700 text-white rounded transition-colors disabled:opacity-50"
              >
                Reset Circuit Breaker
              </button>
            )}
            <button
              onClick={() => setShowRiskConfig(!showRiskConfig)}
              className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
            >
              {showRiskConfig ? 'Hide' : 'Configure Limits'}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-xs text-slate-400 uppercase">Session PnL</div>
            <div className={`text-xl font-bold mt-1 ${
              status.risk_state.session_pnl >= 0 ? 'text-green-400' : 'text-red-400'
            }`}>
              ${status.risk_state.session_pnl >= 0 ? '+' : ''}{status.risk_state.session_pnl.toFixed(2)}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-400 uppercase">Daily PnL</div>
            <div className={`text-xl font-bold mt-1 ${
              status.risk_state.daily_pnl >= 0 ? 'text-green-400' : 'text-red-400'
            }`}>
              ${status.risk_state.daily_pnl >= 0 ? '+' : ''}{status.risk_state.daily_pnl.toFixed(2)}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-400 uppercase">Drawdown</div>
            <div className={`text-xl font-bold mt-1 ${
              status.risk_state.drawdown_pct <= -20 ? 'text-red-400' : status.risk_state.drawdown_pct <= -10 ? 'text-yellow-400' : 'text-green-400'
            }`}>
              {status.risk_state.drawdown_pct.toFixed(1)}%
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-400 uppercase">Exposure</div>
            <div className="text-xl font-bold text-white mt-1">
              ${status.risk_state.total_exposure.toFixed(0)}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-400 uppercase">Positions</div>
            <div className="text-xl font-bold text-white mt-1">
              {status.risk_state.open_positions}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-400 uppercase">Consecutive Losses</div>
            <div className={`text-xl font-bold mt-1 ${
              status.risk_state.consecutive_losses >= 5 ? 'text-red-400' : 'text-slate-300'
            }`}>
              {status.risk_state.consecutive_losses}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-400 uppercase">Violations</div>
            <div className={`text-xl font-bold mt-1 ${
              status.risk_state.violations > 0 ? 'text-yellow-400' : 'text-green-400'
            }`}>
              {status.risk_state.violations}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-400 uppercase">Circuit Breaker</div>
            <div className={`text-xl font-bold mt-1 ${
              status.risk_state.circuit_breaker_active ? 'text-red-400' : 'text-green-400'
            }`}>
              {status.risk_state.circuit_breaker_active ? '🔴 Active' : '✅ Off'}
            </div>
          </div>
        </div>

        {status.risk_state.circuit_breaker_active && (
          <div className="mt-4 p-3 bg-red-900/30 border border-red-500/50 rounded-lg">
            <p className="text-sm text-red-300">
              🔴 Circuit breaker triggered due to consecutive losses. Trading paused for 30 minutes.
            </p>
          </div>
        )}
      </div>

      {/* Risk Limits Configuration */}
      {showRiskConfig && (
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h3 className="text-lg font-bold text-white mb-4">Risk Limits Configuration</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-slate-300 mb-1">Max Position Size ($)</label>
              <input
                type="number"
                value={editingLimits.max_position_size ?? status.risk_limits.max_position_size}
                onChange={(e) => setEditingLimits({ ...editingLimits, max_position_size: parseFloat(e.target.value) })}
                className="w-full bg-slate-700 text-white rounded px-3 py-2 border border-slate-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-300 mb-1">Max Total Exposure ($)</label>
              <input
                type="number"
                value={editingLimits.max_total_exposure ?? status.risk_limits.max_total_exposure}
                onChange={(e) => setEditingLimits({ ...editingLimits, max_total_exposure: parseFloat(e.target.value) })}
                className="w-full bg-slate-700 text-white rounded px-3 py-2 border border-slate-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-300 mb-1">Max Daily Loss ($)</label>
              <input
                type="number"
                value={editingLimits.max_daily_loss ?? status.risk_limits.max_daily_loss}
                onChange={(e) => setEditingLimits({ ...editingLimits, max_daily_loss: parseFloat(e.target.value) })}
                className="w-full bg-slate-700 text-white rounded px-3 py-2 border border-slate-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-300 mb-1">Max Drawdown (%)</label>
              <input
                type="number"
                step="0.01"
                value={editingLimits.max_drawdown_pct ?? status.risk_limits.max_drawdown_pct}
                onChange={(e) => setEditingLimits({ ...editingLimits, max_drawdown_pct: parseFloat(e.target.value) })}
                className="w-full bg-slate-700 text-white rounded px-3 py-2 border border-slate-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-300 mb-1">Max Consecutive Losses</label>
              <input
                type="number"
                value={editingLimits.max_consecutive_losses ?? status.risk_limits.max_consecutive_losses}
                onChange={(e) => setEditingLimits({ ...editingLimits, max_consecutive_losses: parseInt(e.target.value) })}
                className="w-full bg-slate-700 text-white rounded px-3 py-2 border border-slate-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-300 mb-1">Emergency Stop Loss ($)</label>
              <input
                type="number"
                value={editingLimits.emergency_stop_loss ?? status.risk_limits.emergency_stop_loss}
                onChange={(e) => setEditingLimits({ ...editingLimits, emergency_stop_loss: parseFloat(e.target.value) })}
                className="w-full bg-slate-700 text-white rounded px-3 py-2 border border-slate-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="flex gap-3 mt-6">
            <button
              onClick={handleUpdateRiskLimits}
              disabled={loading || Object.keys(editingLimits).length === 0}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Updating...' : 'Update Limits'}
            </button>
            <button
              onClick={() => {
                setEditingLimits({})
                setShowRiskConfig(false)
              }}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-semibold transition-all"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Executor Stats */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h3 className="text-lg font-bold text-white mb-4">Executor Statistics</h3>
        
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <div className="text-xs text-slate-400 uppercase">Orders Placed</div>
            <div className="text-xl font-bold text-white mt-1">
              {status.executor_stats.total_orders_placed}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-400 uppercase">Orders Filled</div>
            <div className="text-xl font-bold text-green-400 mt-1">
              {status.executor_stats.total_fills}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-400 uppercase">Fill Rate</div>
            <div className="text-xl font-bold text-white mt-1">
              {(status.executor_stats.fill_rate * 100).toFixed(1)}%
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-400 uppercase">Avg Slippage</div>
            <div className="text-xl font-bold text-yellow-400 mt-1">
              {status.executor_stats.avg_slippage.toFixed(4)}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-400 uppercase">Cancellations</div>
            <div className="text-xl font-bold text-red-400 mt-1">
              {status.executor_stats.total_cancellations}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-400 uppercase">Active Orders</div>
            <div className="text-xl font-bold text-white mt-1">
              {status.executor_stats.active_orders}
            </div>
          </div>
        </div>
      </div>

      {/* Errors */}
      {(error || status.errors.length > 0) && (
        <div className="bg-red-900/30 border border-red-500/50 rounded-lg p-4">
          <h4 className="text-red-400 font-semibold mb-2">⚠️ Errors</h4>
          {error && <p className="text-sm text-red-300 mb-1">• {error}</p>}
          {status.errors.map((err, i) => (
            <p key={i} className="text-sm text-red-300 mb-1">• {err}</p>
          ))}
        </div>
      )}
    </div>
  )
}
