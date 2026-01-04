'use client'

import { useState, useEffect } from 'react'
import Dashboard from '@/components/Dashboard'
import ControlPanel from '@/components/ControlPanel'
import { BotStatus } from '@/lib/types'

export default function Home() {
  const [status, setStatus] = useState<BotStatus | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isMockMode, setIsMockMode] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showControls, setShowControls] = useState(false)

  useEffect(() => {
    // Poll status endpoint every 2 seconds
    const fetchStatus = async () => {
      try {
        const response = await fetch('/api/status')
        if (!response.ok) {
          throw new Error('Failed to fetch status')
        }
        const data = await response.json()
        setStatus(data)
        setIsConnected(true)
        setError(null)
        
        // Check if we're getting mock data by looking at condition_id
        if (data.markets && data.markets.length > 0) {
          setIsMockMode(data.markets[0].condition_id.includes('mock'))
        }
      } catch (err) {
        console.error('Status fetch error:', err)
        setIsConnected(false)
        setError(err instanceof Error ? err.message : 'Unknown error')
      }
    }

    fetchStatus()
    const interval = setInterval(fetchStatus, 2000)

    return () => clearInterval(interval)
  }, [])

  const handleConfigUpdate = (mode: 'train' | 'inference', size: number, markets?: string[]) => {
    // Update local state optimistically
    if (status) {
      setStatus({
        ...status,
        mode,
        trade_size: size,
        enabled_markets: markets || status.enabled_markets,
        performance: {
          ...status.performance,
          max_exposure: size * (markets?.length || status.enabled_markets?.length || 4),
        },
      })
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                Cross-Market State Fusion
              </h1>
              <p className="text-sm text-slate-400 mt-1">
                RL Agent Trading Polymarket Binary Markets
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowControls(!showControls)}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-sm font-semibold transition-all flex items-center gap-2"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
                  />
                </svg>
                {showControls ? 'Hide Controls' : 'Show Controls'}
              </button>
              <div className="flex items-center gap-2">
                <div
                  className={`w-3 h-3 rounded-full ${
                    isConnected ? 'bg-green-500 pulse-glow' : 'bg-red-500'
                  }`}
                />
                <span className="text-sm text-slate-300">
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              {isMockMode && (
                <div className="text-xs px-2 py-1 bg-yellow-900/30 border border-yellow-500/50 rounded text-yellow-400">
                  Mock Data
                </div>
              )}
              {status && (
                <div className="text-sm text-slate-400">
                  <span className="text-slate-500">Mode:</span>{' '}
                  <span className="font-semibold text-blue-400">
                    {status.mode === 'train' ? 'Training' : 'Inference'}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6">
        {isMockMode && (
          <div className="mb-6 p-4 bg-yellow-900/20 border border-yellow-500/50 rounded-lg">
            <p className="text-yellow-400">
              <span className="font-semibold">Demo Mode:</span> The trading bot is not running. Displaying simulated data for demonstration.
            </p>
            <p className="text-sm text-yellow-300 mt-1">
              To connect to the real bot, start it with: <code className="bg-slate-800 px-2 py-1 rounded">python run.py --strategy rl --train</code>
            </p>
          </div>
        )}

        {error && !status && (
          <div className="mb-6 p-4 bg-red-900/20 border border-red-500/50 rounded-lg">
            <p className="text-red-400">
              <span className="font-semibold">Connection Error:</span> {error}
            </p>
            <p className="text-sm text-red-300 mt-1">
              Make sure the bot is running on http://localhost:5000
            </p>
          </div>
        )}

        {!status && !error && (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4" />
              <p className="text-slate-400">Connecting to trading bot...</p>
            </div>
          </div>
        )}

        {status && (
          <div className="space-y-6">
            {/* Control Panel (collapsible) */}
            {showControls && (
              <div className="animate-in slide-in-from-top duration-300">
                <ControlPanel
                  currentMode={status.mode}
                  currentSize={status.trade_size}
                  enabledMarkets={status.enabled_markets}
                  onConfigUpdate={handleConfigUpdate}
                />
              </div>
            )}

            {/* Dashboard */}
            <Dashboard status={status} />
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-700 bg-slate-900/50 backdrop-blur-sm mt-12">
        <div className="container mx-auto px-4 py-4 text-center text-sm text-slate-400">
          <p>
            Paper Trading Only • Binance Futures + Polymarket CLOB •{' '}
            <a
              href="https://github.com/humanplane/cross-market-state-fusion"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:text-blue-300 transition-colors"
            >
              View on GitHub
            </a>
          </p>
        </div>
      </footer>
    </main>
  )
}
