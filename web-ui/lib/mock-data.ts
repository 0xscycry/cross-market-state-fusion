import { BotStatus } from './types'
import { getMockConfig } from './mock-config'

// Mock data generator for development when the bot is not running

let mockPnL = 0
let mockTrades: any[] = []
let mockPnLHistory: Array<{ timestamp: string; pnl: number }> = []

function generateRandomTrade(asset: string, size: number) {
  const side = Math.random() > 0.5 ? 'UP' : 'DOWN'
  const entryProb = Math.random() * 0.6 + 0.2 // 0.2 to 0.8
  const exitProb = Math.random() * 0.6 + 0.2
  const shares = size / entryProb
  const pnl = (exitProb - entryProb) * shares
  
  mockPnL += pnl
  
  const trade = {
    asset,
    side,
    entry_prob: entryProb,
    exit_prob: exitProb,
    size,
    pnl,
    entry_time: new Date(Date.now() - Math.random() * 900000).toISOString(),
    exit_time: new Date().toISOString(),
  }
  
  mockTrades.unshift(trade)
  if (mockTrades.length > 20) mockTrades.pop()
  
  mockPnLHistory.push({
    timestamp: new Date().toISOString(),
    pnl,
  })
  if (mockPnLHistory.length > 100) mockPnLHistory.shift()
  
  return trade
}

export function getMockStatus(): BotStatus {
  // Get current config
  const config = getMockConfig()
  
  // Simulate occasional new trades with current trade size from enabled markets only
  if (Math.random() < 0.1 && config.enabled_markets.length > 0) {
    const randomMarket = config.enabled_markets[Math.floor(Math.random() * config.enabled_markets.length)]
    generateRandomTrade(randomMarket, config.trade_size)
  }
  
  const numTrades = mockTrades.length
  const numWins = mockTrades.filter(t => t.pnl > 0).length
  const winRate = numTrades > 0 ? numWins / numTrades : 0
  const avgPnl = numTrades > 0 ? mockPnL / numTrades : 0
  const avgWin = numWins > 0 ? mockTrades.filter(t => t.pnl > 0).reduce((sum, t) => sum + t.pnl, 0) / numWins : 0
  const numLosses = numTrades - numWins
  const avgLoss = numLosses > 0 ? mockTrades.filter(t => t.pnl <= 0).reduce((sum, t) => sum + t.pnl, 0) / numLosses : 0
  
  const now = new Date()
  
  // Only create markets for enabled assets
  const allMarkets = [
    {
      symbol: 'BTC',
      condition_id: 'btc_mock_1',
      asset: 'BTC',
      question: 'Will BTC price be higher in 15 minutes?',
      end_date: new Date(now.getTime() + 780000).toISOString(),
      prob_up: 0.52 + Math.random() * 0.1 - 0.05,
      prob_down: 0.48 + Math.random() * 0.1 - 0.05,
      last_action: { action: 'BUY_UP' as const, confidence: 0.65 },
      state: {
        returns_1m: 0.012,
        returns_5m: 0.034,
        returns_10m: 0.067,
        ob_imbalance_l1: 0.23,
        ob_imbalance_l5: 0.18,
        trade_flow: 0.45,
        cvd_accel: 0.0034,
        spread_pct: 0.015,
        trade_intensity: 0.78,
        large_trade_flag: 1,
        vol_5m: 0.024,
        vol_expansion: 0.12,
        has_position: 1,
        position_side: 1,
        position_pnl: 0.34,
        time_remaining: 0.87,
        vol_regime: 0,
        trend_regime: 1,
      },
    },
    {
      symbol: 'ETH',
      condition_id: 'eth_mock_1',
      asset: 'ETH',
      question: 'Will ETH price be higher in 15 minutes?',
      end_date: new Date(now.getTime() + 660000).toISOString(),
      prob_up: 0.48 + Math.random() * 0.1 - 0.05,
      prob_down: 0.52 + Math.random() * 0.1 - 0.05,
      last_action: { action: 'HOLD' as const, confidence: null },
      state: {
        returns_1m: -0.008,
        returns_5m: -0.021,
        returns_10m: -0.045,
        ob_imbalance_l1: -0.15,
        ob_imbalance_l5: -0.12,
        trade_flow: -0.32,
        cvd_accel: -0.0021,
        spread_pct: 0.018,
        trade_intensity: 0.62,
        large_trade_flag: 0,
        vol_5m: 0.019,
        vol_expansion: -0.08,
        has_position: 0,
        position_side: 0,
        position_pnl: 0,
        time_remaining: 0.73,
        vol_regime: 0,
        trend_regime: -1,
      },
    },
    {
      symbol: 'SOL',
      condition_id: 'sol_mock_1',
      asset: 'SOL',
      question: 'Will SOL price be higher in 15 minutes?',
      end_date: new Date(now.getTime() + 540000).toISOString(),
      prob_up: 0.55 + Math.random() * 0.1 - 0.05,
      prob_down: 0.45 + Math.random() * 0.1 - 0.05,
      last_action: { action: 'HOLD' as const, confidence: null },
      state: {
        returns_1m: 0.003,
        returns_5m: 0.011,
        returns_10m: 0.028,
        ob_imbalance_l1: 0.09,
        ob_imbalance_l5: 0.06,
        trade_flow: 0.15,
        cvd_accel: 0.0008,
        spread_pct: 0.021,
        trade_intensity: 0.54,
        large_trade_flag: 0,
        vol_5m: 0.027,
        vol_expansion: 0.05,
        has_position: 0,
        position_side: 0,
        position_pnl: 0,
        time_remaining: 0.60,
        vol_regime: 1,
        trend_regime: 0,
      },
    },
    {
      symbol: 'XRP',
      condition_id: 'xrp_mock_1',
      asset: 'XRP',
      question: 'Will XRP price be higher in 15 minutes?',
      end_date: new Date(now.getTime() + 420000).toISOString(),
      prob_up: 0.50 + Math.random() * 0.1 - 0.05,
      prob_down: 0.50 + Math.random() * 0.1 - 0.05,
      last_action: { action: 'HOLD' as const, confidence: null },
      state: {
        returns_1m: -0.002,
        returns_5m: 0.004,
        returns_10m: 0.009,
        ob_imbalance_l1: 0.02,
        ob_imbalance_l5: 0.01,
        trade_flow: 0.08,
        cvd_accel: 0.0003,
        spread_pct: 0.023,
        trade_intensity: 0.48,
        large_trade_flag: 0,
        vol_5m: 0.016,
        vol_expansion: -0.03,
        has_position: 0,
        position_side: 0,
        position_pnl: 0,
        time_remaining: 0.47,
        vol_regime: 0,
        trend_regime: 0,
      },
    },
  ]

  // Filter markets based on enabled_markets config
  const markets = allMarkets
    .filter(m => config.enabled_markets.includes(m.symbol))
    .map(m => ({
      condition_id: m.condition_id,
      asset: m.asset,
      question: m.question,
      end_date: m.end_date,
      prob_up: m.prob_up,
      prob_down: m.prob_down,
      position: Math.random() > 0.5 ? {
        side: (Math.random() > 0.5 ? 'UP' : 'DOWN') as const,
        entry_prob: Math.random() * 0.4 + 0.3,
        size: config.trade_size,
        entry_time: new Date(now.getTime() - 420000).toISOString(),
      } : null,
      unrealized_pnl: Math.random() > 0.5 ? (Math.random() * 50 - 25) : null,
      last_action: m.last_action,
      last_state: m.state,
    }))
  
  return {
    mode: config.mode,
    trade_size: config.trade_size,
    enabled_markets: config.enabled_markets,
    markets,
    performance: {
      total_pnl: mockPnL,
      num_trades: numTrades,
      num_wins: numWins,
      win_rate: winRate,
      avg_pnl: avgPnl,
      avg_win: avgWin,
      avg_loss: avgLoss,
      max_exposure: config.max_exposure,
    },
    recent_trades: mockTrades.slice(0, 10),
    pnl_history: mockPnLHistory,
    training_stats: config.mode === 'train' ? {
      update: Math.floor(Math.random() * 100) + 1,
      policy_loss: Math.random() * 0.1,
      value_loss: Math.random() * 20 + 5,
      entropy: Math.random() * 0.3 + 0.9,
    } : undefined,
  }
}
