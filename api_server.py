#!/usr/bin/env python3
"""
Flask API server for Cross-Market State Fusion trading bot.
Provides real-time status data to the web UI.

Usage:
    python api_server.py

The server runs on port 5000 and provides:
    GET /api/status - Current bot status, markets, performance, trades
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import random

app = Flask(__name__)
CORS(app)  # Enable CORS for Next.js dev server

# Global state - in production, this would come from your actual trading bot
# For now, we'll simulate live data
class BotState:
    def __init__(self):
        self.mode = 'train'
        self.trade_size = 500
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
        
        # Simulate occasional trades
        if random.random() < 0.2 and self.num_trades < 100:
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
        """Add a simulated trade"""
        assets = ['BTC', 'ETH', 'SOL', 'XRP']
        asset = random.choice(assets)
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
        """Update or create market data"""
        assets = ['BTC', 'ETH', 'SOL', 'XRP']
        
        if len(self.markets) == 0:
            # Initialize markets
            for asset in assets:
                self.markets.append(self._create_market(asset))
        else:
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
            'markets': self.markets,
            'performance': {
                'total_pnl': self.total_pnl,
                'num_trades': self.num_trades,
                'num_wins': self.num_wins,
                'win_rate': win_rate,
                'avg_pnl': avg_pnl,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'max_exposure': self.trade_size * 4  # 4 concurrent markets
            },
            'recent_trades': self.trades[:20],
            'pnl_history': self.pnl_history,
            'training_stats': self.training_stats if self.mode == 'train' else None
        }

# Global bot state instance
bot_state = BotState()

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
        'max_exposure': bot_state.trade_size * 4
    }), 200

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update bot configuration"""
    data = request.get_json()
    
    if 'mode' in data and data['mode'] in ['train', 'inference']:
        bot_state.mode = data['mode']
    
    if 'trade_size' in data and isinstance(data['trade_size'], (int, float)) and data['trade_size'] > 0:
        bot_state.trade_size = float(data['trade_size'])
    
    return jsonify({
        'success': True,
        'mode': bot_state.mode,
        'trade_size': bot_state.trade_size
    }), 200

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API info"""
    return jsonify({
        'name': 'Cross-Market State Fusion API',
        'version': '1.0.0',
        'endpoints': {
            'GET /api/status': 'Get current bot status',
            'GET /api/config': 'Get bot configuration',
            'POST /api/config': 'Update bot configuration',
            'GET /health': 'Health check'
        }
    }), 200

if __name__ == '__main__':
    print("
" + "="*60)
    print("Cross-Market State Fusion API Server")
    print("="*60)
    print(f"Starting Flask server on http://localhost:5000")
    print(f"Mode: {bot_state.mode}")
    print(f"Trade Size: ${bot_state.trade_size}")
    print("
Endpoints:")
    print("  GET  /api/status  - Bot status and live data")
    print("  GET  /api/config  - Configuration")
    print("  POST /api/config  - Update config")
    print("  GET  /health      - Health check")
    print("
Press Ctrl+C to stop")
    print("="*60 + "
")
    
    # Run Flask app
    app.run(
        host='0.0.0.0',  # Listen on all interfaces
        port=5000,
        debug=False,  # Set to True for development
        threaded=True
    )
