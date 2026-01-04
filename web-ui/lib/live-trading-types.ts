/**
 * Types for live trading feature
 */

export interface LiveTradingConfig {
  enabled: boolean
  mode: 'paper' | 'live' | 'mock'
  executor_type: 'real' | 'mock'
  wallet_address?: string
  api_key_configured: boolean
}

export interface RiskLimits {
  max_position_size: number
  max_total_exposure: number
  max_single_market_exposure: number
  max_daily_loss: number
  max_drawdown_pct: number
  max_consecutive_losses: number
  max_orders_per_minute: number
  max_orders_per_hour: number
  emergency_stop_loss: number
  enable_circuit_breaker: boolean
}

export interface RiskState {
  session_pnl: number
  daily_pnl: number
  current_equity: number
  peak_equity: number
  drawdown_pct: number
  open_positions: number
  total_exposure: number
  consecutive_losses: number
  total_trades: number
  violations: number
  circuit_breaker_active: boolean
}

export interface ExecutorStats {
  total_orders_placed: number
  total_fills: number
  total_cancellations: number
  fill_rate: number
  avg_slippage: number
  active_orders: number
}

export interface LiveTradingStatus {
  config: LiveTradingConfig
  risk_limits: RiskLimits
  risk_state: RiskState
  executor_stats: ExecutorStats
  can_trade: boolean
  errors: string[]
}

export interface OrderResult {
  success: boolean
  order_id?: string
  filled_size: number
  avg_price: number
  slippage: number
  latency_ms: number
  fees: number
  error?: string
}

export interface RiskViolation {
  timestamp: string
  type: string
  details: string
}
