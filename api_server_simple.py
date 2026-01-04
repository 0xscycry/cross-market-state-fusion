#!/usr/bin/env python3
"""
Flask API server for Cross-Market State Fusion trading bot.
Simplified version without heavy dependencies - provides mock live trading status.

Usage:
    python api_server_simple.py

The server runs on port 5000 and provides:
    GET /api/status - Current bot status, markets, performance, trades
    GET /api/config - Bot configuration
    POST /api/config - Update bot configuration
    GET /api/live-trading/status - Live trading status
    POST /api/live-trading/config - Update live trading config
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

try:
    from flask import Flask, jsonify, request
    from flask_cors import CORS
except ImportError:
    print("
Error: Flask not installed. Install with: pip install Flask flask-cors")
    exit(1)

import random

app = Flask(__name__)
CORS(app)  # Enable CORS for Next.js dev server

# Global state - simulated bot and live trading data
class BotState:
    def __init__(self):
        self.mode = 'train'
        self.trade_size = 500
        self.enabled_markets = ['BTC', 'ETH', 'SOL', 'XRP']
        self.total_pnl = 0.0
        self.num_trades = 0
        self.num_wins = 0
        self.trades = []
        self.pnl_history = []
        self.markets = []
        self.training_stats = {
            'update': 1,
            'policy_loss': 0.05,
            'value_loss': 12.3,
            'entropy': 1.05
        }
        self.last_update = time.time()
        
    def update(self):
        """Simulate bot activity"""
        now = time.time()
        if now - self.last_update < 5:  # Update every 5 seconds
            return
            
        self.last_update = now
        
        # Simulate occasional trades (only from enabled markets)
        if random.random() < 0.2 and self.num_trades < 100 and len(self.enabled_markets) > 0:
            self._add_random_trade()
        
        # Update training stats
        if self.mode == 'train':
            self.training_stats['update'] += 1
            self.training_stats['policy_loss'] = max(0.001, self.training_stats['policy_loss'] * (0.95 + random.random() * 0.1))
            self.training_stats['value_loss'] = max(1.0, self.training_stats['value_loss'] * (0.95 + random.random() * 0.1))
            self.training_stats['entropy'] = min(1.09, max(0.95, self.training_stats['entropy'] + random.random() * 0.04 - 0.02))
        
        # Update markets
        self._update_markets()
    
    def _add_random_trade(self):
        """Add a simulated trade from an enabled market"""
        if len(self.enabled_markets) == 0:
            return
            
        asset = random.choice(self.enabled_markets)
        side = random.choice(['UP', 'DOWN'])
        entry_prob = random.uniform(0.2, 0.8)
        exit_prob = random.uniform(0.2, 0.8)
        size = self.trade_size
        
        # Calculate PnL using share-based formula (Phase 4+)
        shares = size / entry_prob
        pnl = (exit_prob - entry_prob) * shares
        
        self.total_pnl += pnl
        self.num_trades += 1
        if pnl > 0:
            self.num_wins += 1
        
        trade = {
            'asset': asset,
            'side': side,
            'entry_prob': entry_prob,
            'exit_prob': exit_prob,
            'size': size,
            'pnl': pnl,
            'entry_time': (datetime.now() - timedelta(minutes=random.randint(1, 14))).isoformat(),
            'exit_time': datetime.now().isoformat()
        }
        
        self.trades.insert(0, trade)
        if len(self.trades) > 50:
            self.trades.pop()
        
        self.pnl_history.append({
            'timestamp': datetime.now().isoformat(),
            'pnl': pnl
        })
        if len(self.pnl_history) > 200:
            self.pnl_history.pop(0)
    
    def _update_markets(self):
        """Update or create market data (only for enabled markets)"""
        if len(self.markets) == 0:
            # Initialize markets for enabled assets only
            for asset in self.enabled_markets:
                self.markets.append(self._create_market(asset))
        else:
            # Remove markets that are no longer enabled
            self.markets = [m for m in self.markets if m['asset'] in self.enabled_markets]
            
            # Add markets for newly enabled assets
            existing_assets = {m['asset'] for m in self.markets}
            for asset in self.enabled_markets:
                if asset not in existing_assets:
                    self.markets.append(self._create_market(asset))
            
            # Update existing markets
            for market in self.markets:
                # Update probabilities with small random walk
                market['prob_up'] = max(0.1, min(0.9, market['prob_up'] + random.uniform(-0.05, 0.05)))
                market['prob_down'] = 1.0 - market['prob_up']
                
                # Update time remaining
                end_time = datetime.fromisoformat(market['end_date'])
                if datetime.now() >= end_time:
                    # Market expired, create new one
                    idx = self.markets.index(market)
                    self.markets[idx] = self._create_market(market['asset'])
                
                # Randomly update positions
                if market['position'] and random.random() < 0.1:
                    # Close position
                    market['position'] = None
                    market['unrealized_pnl'] = None
                elif not market['position'] and random.random() < 0.05:
                    # Open position
                    market['position'] = {
                        'side': random.choice(['UP', 'DOWN']),
                        'entry_prob': market['prob_up'] if random.random() > 0.5 else market['prob_down'],
                        'size': self.trade_size,
                        'entry_time': datetime.now().isoformat()
                    }
                
                # Update unrealized PnL for open positions
                if market['position']:
                    entry_prob = market['position']['entry_prob']
                    current_prob = market['prob_up'] if market['position']['side'] == 'UP' else market['prob_down']
                    shares = self.trade_size / entry_prob
                    market['unrealized_pnl'] = (current_prob - entry_prob) * shares
                
                # Update state features with realistic values
                self._update_state(market)
    
    def _create_market(self, asset: str) -> Dict[str, Any]:
        """Create a new market"""
        prob_up = random.uniform(0.45, 0.55)
        market = {
            'condition_id': f"{asset.lower()}_{int(time.time())}_{random.randint(1000, 9999)}",
            'asset': asset,
            'question': f"Will {asset} price be higher in 15 minutes?",
            'end_date': (datetime.now() + timedelta(minutes=15)).isoformat(),
            'prob_up': prob_up,
            'prob_down': 1.0 - prob_up,
            'position': None,
            'unrealized_pnl': None,
            'last_action': {
                'action': 'HOLD',
                'confidence': None
            },
            'last_state': {}
        }
        self._update_state(market)
        return market
    
    def _update_state(self, market: Dict[str, Any]):
        """Update state features for a market"""
        # Simulate realistic 18-dimensional state
        trend = random.uniform(-1, 1)
        volatility = random.uniform(0, 0.5)
        
        market['last_state'] = {
            # Momentum (correlated with trend)
            'returns_1m': trend * 0.01 + random.uniform(-0.005, 0.005),
            'returns_5m': trend * 0.03 + random.uniform(-0.015, 0.015),
            'returns_10m': trend * 0.06 + random.uniform(-0.03, 0.03),
            
            # Order Flow (correlated with trend)
            'ob_imbalance_l1': trend * 0.3 + random.uniform(-0.2, 0.2),
            'ob_imbalance_l5': trend * 0.25 + random.uniform(-0.15, 0.15),
            'trade_flow': trend * 0.4 + random.uniform(-0.3, 0.3),
            'cvd_accel': trend * 0.004 + random.uniform(-0.002, 0.002),
            
            # Microstructure
            'spread_pct': volatility * 0.03 + random.uniform(0.01, 0.02),
            'trade_intensity': random.uniform(0.3, 0.9),
            'large_trade_flag': 1 if random.random() > 0.7 else 0,
            
            # Volatility
            'vol_5m': volatility * 0.04 + random.uniform(0.01, 0.03),
            'vol_expansion': random.uniform(-0.2, 0.2),
            
            # Position
            'has_position': 1 if market['position'] else 0,
            'position_side': 1 if market['position'] and market['position']['side'] == 'UP' else (-1 if market['position'] else 0),
            'position_pnl': (market['unrealized_pnl'] / self.trade_size) if market['unrealized_pnl'] else 0,
            'time_remaining': max(0, (datetime.fromisoformat(market['end_date']) - datetime.now()).total_seconds() / 900),
            
            # Regime
            'vol_regime': 1 if volatility > 0.3 else 0,
            'trend_regime': 1 if trend > 0.3 else (-1 if trend < -0.3 else 0)
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bot status for API response"""
        self.update()
        
        # Calculate performance metrics
        win_rate = self.num_wins / self.num_trades if self.num_trades > 0 else 0
        avg_pnl = self.total_pnl / self.num_trades if self.num_trades > 0 else 0
        
        wins = [t['pnl'] for t in self.trades if t['pnl'] > 0]
        losses = [t['pnl'] for t in self.trades if t['pnl'] <= 0]
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        return {
            'mode': self.mode,
            'trade_size': self.trade_size,
            'enabled_markets': self.enabled_markets,
            'markets': self.markets,
            'performance': {
                'total_pnl': self.total_pnl,
                'num_trades': self.num_trades,
                'num_wins': self.num_wins,
                'win_rate': win_rate,
                'avg_pnl': avg_pnl,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'max_exposure': self.trade_size * len(self.enabled_markets)
            },
            'recent_trades': self.trades[:20],
            'pnl_history': self.pnl_history,
            'training_stats': self.training_stats if self.mode == 'train' else None
        }

# Global bot state instance
bot_state = BotState()

# Live Trading State (simplified mock version)
class LiveTradingState:
    def __init__(self):
        self.enabled = False
        self.mode = 'paper'  # 'paper' or 'live'
        self.api_key_configured = False
        self.private_key_configured = False
        self.wallet_address = None
        self.errors = []
        
        # Mock risk state
        self.session_pnl = 0.0
        self.daily_pnl = 0.0
        self.current_equity = 10000.0
        self.peak_equity = 10000.0
        self.open_positions = 0
        self.total_exposure = 0.0
        self.consecutive_losses = 0
        self.total_trades = 0
        self.violations = 0
        self.circuit_breaker_active = False
        
        # Mock executor stats
        self.total_orders_placed = 0
        self.total_fills = 0
        self.total_cancellations = 0
        
        # Risk limits
        self.max_position_size = 500.0
        self.max_total_exposure = 2000.0
        self.max_single_market_exposure = 1000.0
        self.max_daily_loss = -1000.0
        self.max_drawdown_pct = 0.30
        self.max_consecutive_losses = 10
        self.max_orders_per_minute = 30
        self.max_orders_per_hour = 500
        self.emergency_stop_loss = -2000.0
        self.enable_circuit_breaker = True
        
        # Check environment variables
        self._check_credentials()
    
    def _check_credentials(self):
        """Check if API credentials are configured."""
        api_key = os.getenv('POLYMARKET_API_KEY')
        private_key = os.getenv('POLYMARKET_PRIVATE_KEY')
        
        self.api_key_configured = api_key is not None and len(api_key) > 0
        self.private_key_configured = private_key is not None and len(private_key) > 0
        
        if self.private_key_configured:
            # Mock wallet address
            self.wallet_address = "0x" + "a" * 40
    
    def get_status(self) -> Dict[str, Any]:
        """Get current live trading status."""
        # Calculate drawdown
        drawdown_pct = 0.0
        if self.peak_equity > 0:
            drawdown_pct = ((self.current_equity - self.peak_equity) / self.peak_equity) * 100
        
        # Calculate fill rate
        fill_rate = 0.0
        if self.total_orders_placed > 0:
            fill_rate = self.total_fills / self.total_orders_placed
        
        return {
            'config': {
                'enabled': self.enabled,
                'mode': self.mode,
                'executor_type': 'mock',
                'wallet_address': self.wallet_address,
                'api_key_configured': self.api_key_configured,
            },
            'risk_limits': {
                'max_position_size': self.max_position_size,
                'max_total_exposure': self.max_total_exposure,
                'max_single_market_exposure': self.max_single_market_exposure,
                'max_daily_loss': self.max_daily_loss,
                'max_drawdown_pct': self.max_drawdown_pct,
                'max_consecutive_losses': self.max_consecutive_losses,
                'max_orders_per_minute': self.max_orders_per_minute,
                'max_orders_per_hour': self.max_orders_per_hour,
                'emergency_stop_loss': self.emergency_stop_loss,
                'enable_circuit_breaker': self.enable_circuit_breaker,
            },
            'risk_state': {
                'session_pnl': self.session_pnl,
                'daily_pnl': self.daily_pnl,
                'current_equity': self.current_equity,
                'peak_equity': self.peak_equity,
                'drawdown_pct': drawdown_pct,
                'open_positions': self.open_positions,
                'total_exposure': self.total_exposure,
                'consecutive_losses': self.consecutive_losses,
                'total_trades': self.total_trades,
                'violations': self.violations,
                'circuit_breaker_active': self.circuit_breaker_active,
            },
            'executor_stats': {
                'total_orders_placed': self.total_orders_placed,
                'total_fills': self.total_fills,
                'total_cancellations': self.total_cancellations,
                'fill_rate': fill_rate,
                'avg_slippage': 0.0,
                'active_orders': 0,
            },
            'can_trade': self.enabled and not self.circuit_breaker_active,
            'errors': self.errors,
        }

# Global live trading state
live_trading_state = LiveTradingState()

# ========== Bot Status Endpoints ==========

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current bot status"""
    try:
        status = bot_state.get_status()
        return jsonify(status), 200
    except Exception as e:
        return jsonify({
            'error': 'Failed to get bot status',
            'message': str(e)
        }), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get bot configuration"""
    return jsonify({
        'mode': bot_state.mode,
        'trade_size': bot_state.trade_size,
        'max_exposure': bot_state.trade_size * len(bot_state.enabled_markets),
        'enabled_markets': bot_state.enabled_markets
    }), 200

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update bot configuration"""
    data = request.get_json()
    
    # Validate and update mode
    if 'mode' in data and data['mode'] in ['train', 'inference']:
        bot_state.mode = data['mode']
    
    # Validate and update trade size
    if 'trade_size' in data and isinstance(data['trade_size'], (int, float)) and data['trade_size'] > 0:
        bot_state.trade_size = float(data['trade_size'])
    
    # Validate and update enabled markets
    if 'enabled_markets' in data:
        if isinstance(data['enabled_markets'], list):
            valid_markets = ['BTC', 'ETH', 'SOL', 'XRP']
            enabled = [m for m in data['enabled_markets'] if m in valid_markets]
            if len(enabled) > 0:
                bot_state.enabled_markets = enabled
    
    return jsonify({
        'success': True,
        'mode': bot_state.mode,
        'trade_size': bot_state.trade_size,
        'max_exposure': bot_state.trade_size * len(bot_state.enabled_markets),
        'enabled_markets': bot_state.enabled_markets
    }), 200

# ========== Live Trading Endpoints ==========

@app.route('/api/live-trading/status', methods=['GET'])
def get_live_trading_status():
    """Get live trading status"""
    try:
        status = live_trading_state.get_status()
        return jsonify(status), 200
    except Exception as e:
        return jsonify({
            'error': 'Failed to get live trading status',
            'message': str(e)
        }), 500

@app.route('/api/live-trading/config', methods=['POST'])
def update_live_trading_config():
    """Update live trading configuration"""
    try:
        data = request.get_json()
        
        # Handle enable/disable toggle
        if 'enabled' in data:
            enabled = data['enabled']
            
            if enabled and not live_trading_state.enabled:
                # Enabling live trading
                live_trading_state.enabled = True
                live_trading_state.mode = 'paper' if not (live_trading_state.api_key_configured and live_trading_state.private_key_configured) else 'live'
                print(f"

{'='*60}")
                print("
🟢 LIVE TRADING ENABLED (Mock Mode)")
                print(f"
Mode: {live_trading_state.mode}")
                print(f"
{'='*60}
")
            
            elif not enabled and live_trading_state.enabled:
                # Disabling live trading
                live_trading_state.enabled = False
                print(f"

{'='*60}")
                print("
🔴 LIVE TRADING DISABLED")
                print(f"
{'='*60}
")
        
        # Handle credentials update
        if 'credentials' in data:
            creds = data['credentials']
            if 'api_key' in creds and creds['api_key']:
                os.environ['POLYMARKET_API_KEY'] = creds['api_key']
                live_trading_state.api_key_configured = True
                print("
✓ API key updated")
            
            if 'private_key' in creds and creds['private_key']:
                os.environ['POLYMARKET_PRIVATE_KEY'] = creds['private_key']
                live_trading_state.private_key_configured = True
                live_trading_state._check_credentials()
                print("
✓ Private key updated")
        
        # Handle risk limits update
        if 'risk_limits' in data:
            limits_data = data['risk_limits']
            
            # Update limits
            if 'max_position_size' in limits_data:
                live_trading_state.max_position_size = float(limits_data['max_position_size'])
            if 'max_total_exposure' in limits_data:
                live_trading_state.max_total_exposure = float(limits_data['max_total_exposure'])
            if 'max_single_market_exposure' in limits_data:
                live_trading_state.max_single_market_exposure = float(limits_data['max_single_market_exposure'])
            if 'max_daily_loss' in limits_data:
                live_trading_state.max_daily_loss = float(limits_data['max_daily_loss'])
            if 'max_drawdown_pct' in limits_data:
                live_trading_state.max_drawdown_pct = float(limits_data['max_drawdown_pct'])
            if 'max_consecutive_losses' in limits_data:
                live_trading_state.max_consecutive_losses = int(limits_data['max_consecutive_losses'])
            if 'emergency_stop_loss' in limits_data:
                live_trading_state.emergency_stop_loss = float(limits_data['emergency_stop_loss'])
            
            print("
✓ Risk limits updated")
        
        # Return updated status
        status = live_trading_state.get_status()
        return jsonify(status), 200
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to update configuration',
            'message': str(e)
        }), 500

@app.route('/api/live-trading/reset-circuit-breaker', methods=['POST'])
def reset_circuit_breaker():
    """Manually reset circuit breaker"""
    try:
        live_trading_state.circuit_breaker_active = False
        live_trading_state.consecutive_losses = 0
        
        print("

✓ Circuit breaker manually reset
")
        
        status = live_trading_state.get_status()
        return jsonify(status), 200
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to reset circuit breaker',
            'message': str(e)
        }), 500

@app.route('/api/live-trading/violations', methods=['GET'])
def get_violations():
    """Get risk violations history"""
    try:
        # Return empty list for mock version
        return jsonify({'violations': []}), 200
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to get violations',
            'message': str(e)
        }), 500

# ========== Health & Info Endpoints ==========

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'live_trading_available': True  # Mock version always available
    }), 200

@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API info"""
    return jsonify({
        'name': 'Cross-Market State Fusion API',
        'version': '1.0.0',
        'mode': 'simplified',
        'endpoints': {
            'GET /api/status': 'Get current bot status',
            'GET /api/config': 'Get bot configuration',
            'POST /api/config': 'Update bot configuration',
            'GET /api/live-trading/status': 'Get live trading status',
            'POST /api/live-trading/config': 'Update live trading config',
            'POST /api/live-trading/reset-circuit-breaker': 'Reset circuit breaker',
            'GET /api/live-trading/violations': 'Get risk violations',
            'GET /health': 'Health check'
        },
        'live_trading_available': True
    }), 200

if __name__ == '__main__':
    print("

" + "="*60)
    print("
Cross-Market State Fusion API Server (Simplified)")
    print("
="*60)
    print(f"
Starting Flask server on http://localhost:5000")
    print(f"
Mode: {bot_state.mode}")
    print(f"
Trade Size: ${bot_state.trade_size}")
    print(f"
Enabled Markets: {', '.join(bot_state.enabled_markets)}")
    print(f"
Live Trading: Mock Mode (No real orders)")
    print("

Endpoints:")
    print("
  GET  /api/status                          - Bot status and live data")
    print("
  GET  /api/config                          - Configuration")
    print("
  POST /api/config                          - Update config")
    print("
  GET  /api/live-trading/status             - Live trading status")
    print("
  POST /api/live-trading/config             - Update live trading")
    print("
  POST /api/live-trading/reset-circuit-breaker - Reset circuit breaker")
    print("
  GET  /health                              - Health check")
    print("

Press Ctrl+C to stop")
    print("
="*60 + "
")
    
    # Run Flask app
    app.run(
        host='0.0.0.0',  # Listen on all interfaces
        port=5000,
        debug=False,  # Set to True for development
        threaded=True
    )
