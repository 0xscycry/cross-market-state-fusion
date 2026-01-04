export interface BotStatus {
  mode: 'train' | 'inference'
  trade_size: number
  enabled_markets?: string[]
  markets: Market[]
  performance: Performance
  recent_trades: Trade[]
  pnl_history: Array<{ timestamp: string; pnl: number }>
  training_stats?: TrainingStats
}

export interface Market {
  condition_id: string
  asset: string
  question: string
  end_date: string
  prob_up: number
  prob_down: number
  position: Position | null
  unrealized_pnl: number | null
  last_action: Action | null
  last_state: State | null
}

export interface Position {
  side: 'UP' | 'DOWN'
  entry_prob: number
  size: number
  entry_time: string
}

export interface Action {
  action: 'HOLD' | 'BUY_UP' | 'BUY_DOWN'
  confidence: number | null
}

export interface State {
  // Momentum
  returns_1m?: number
  returns_5m?: number
  returns_10m?: number
  
  // Order Flow
  ob_imbalance_l1?: number
  ob_imbalance_l5?: number
  trade_flow?: number
  cvd_accel?: number
  
  // Microstructure
  spread_pct?: number
  trade_intensity?: number
  large_trade_flag?: number
  
  // Volatility
  vol_5m?: number
  vol_expansion?: number
  
  // Position
  has_position?: number
  position_side?: number
  position_pnl?: number
  time_remaining?: number
  
  // Regime
  vol_regime?: number
  trend_regime?: number
}

export interface Performance {
  total_pnl: number
  num_trades: number
  num_wins: number
  win_rate: number
  avg_pnl: number
  avg_win: number
  avg_loss: number
  max_exposure: number
}

export interface Trade {
  asset: string
  side: 'UP' | 'DOWN'
  entry_prob: number
  exit_prob: number
  size: number
  pnl: number
  entry_time: string
  exit_time: string
}

export interface TrainingStats {
  update: number
  policy_loss: number
  value_loss: number
  entropy: number
}
