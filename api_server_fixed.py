#!/usr/bin/env python3
"""Flask API server with FIXED trade price generation.

Key fix: Trades now use ACTUAL market prices instead of random prices.
"""
import os
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

try:
    from flask import Flask, jsonify, request
    from flask_cors import CORS
except ImportError:
    print("Error: Flask not installed. Run: pip install Flask flask-cors")
    exit(1)

app = Flask(__name__)
CORS(app)


class BotState:
    def __init__(self):
        self.mode = 'train'
        self.trade_size = 100
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
        """Update bot state every 5 seconds."""
        now = time.time()
        if now - self.last_update < 5:
            return
        
        self.last_update = now
        
        # Simulate occasional trades (only if markets exist)
        if (random.random() < 0.2 and 
            self.num_trades < 100 and 
            len(self.enabled_markets) > 0 and 
            len(self.markets) > 0):
            self._add_random_trade()
        
        # Update training stats
        if self.mode == 'train':
            self.training_stats['update'] += 1
            self.training_stats['policy_loss'] = max(
                0.001, 
                self.training_stats['policy_loss'] * (0.95 + random.random() * 0.1)
            )
            self.training_stats['value_loss'] = max(
                1.0, 
                self.training_stats['value_loss'] * (0.95 + random.random() * 0.1)
            )
            self.training_stats['entropy'] = min(
                1.09, 
                max(0.95, self.training_stats['entropy'] + random.random() * 0.04 - 0.02)
            )
        
        # Update markets
        self._update_markets()
    
    def _add_random_trade(self):
        """Add a simulated trade using ACTUAL market prices.
        
        KEY FIX: Trade prices now correspond to actual market prices,
        not random values between 0.2-0.8.
        """
        # Get markets that are available for trading
        available_markets = [
            m for m in self.markets 
            if m['asset'] in self.enabled_markets
        ]
        
        if not available_markets:
            return
        
        # Select a random market
        market = random.choice(available_markets)
        asset = market['asset']
        side = random.choice(['UP', 'DOWN'])
        
        # Use ACTUAL market price as exit (current price)
        current_prob = market['prob_up'] if side == 'UP' else market['prob_down']
        
        # Entry was at a slightly different price (simulate historical price)
        # Add variation of ±15% to simulate market movement
        entry_prob = max(0.05, min(0.95, current_prob + random.uniform(-0.15, 0.15)))
        
        # Exit at current market price
        exit_prob = current_prob
        
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
            'entry_prob': round(entry_prob, 3),
            'exit_prob': round(exit_prob, 3),
            'size': size,
            'pnl': round(pnl, 2),
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
        """Update or create market data."""
        if len(self.markets) == 0:
            # Initialize markets
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
                
                # Check if market expired
                end_time = datetime.fromisoformat(market['end_date'])
                if datetime.now() >= end_time:
                    idx = self.markets.index(market)
                    self.markets[idx] = self._create_market(market['asset'])
                
                # Randomly update positions
                if market['position'] and random.random() < 0.1:
                    market['position'] = None
                    market['unrealized_pnl'] = None
                elif not market['position'] and random.random() < 0.05:
                    market['position'] = {
                        'side': random.choice(['UP', 'DOWN']),
                        'entry_prob': market['prob_up'] if random.random() > 0.5 else market['prob_down'],
                        'size': self.trade_size,
                        'entry_time': datetime.now().isoformat()
                    }
                
                # Update unrealized PnL
                if market['position']:
                    entry_prob = market['position']['entry_prob']
                    current_prob = market['prob_up'] if market['position']['side'] == 'UP' else market['prob_down']
                    shares = self.trade_size / entry_prob
                    market['unrealized_pnl'] = (current_prob - entry_prob) * shares
                
                self._update_state(market)
    
    def _create_market(self, asset: str) -> Dict[str, Any]:
        """Create a new market."""
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
        """Update state features for a market."""
        trend = random.uniform(-1, 1)
        volatility = random.uniform(0, 0.5)
        
        market['last_state'] = {
            'returns_1m': trend * 0.01 + random.uniform(-0.005, 0.005),
            'returns_5m': trend * 0.03 + random.uniform(-0.015, 0.015),
            'returns_10m': trend * 0.06 + random.uniform(-0.03, 0.03),
            'ob_imbalance_l1': trend * 0.3 + random.uniform(-0.2, 0.2),
            'ob_imbalance_l5': trend * 0.25 + random.uniform(-0.15, 0.15),
            'trade_flow': trend * 0.4 + random.uniform(-0.3, 0.3),
            'cvd_accel': trend * 0.004 + random.uniform(-0.002, 0.002),
            'spread_pct': volatility * 0.03 + random.uniform(0.01, 0.02),
            'trade_intensity': random.uniform(0.3, 0.9),
            'large_trade_flag': 1 if random.random() > 0.7 else 0,
            'vol_5m': volatility * 0.04 + random.uniform(0.01, 0.03),
            'vol_expansion': random.uniform(-0.2, 0.2),
            'has_position': 1 if market['position'] else 0,
            'position_side': 1 if market['position'] and market['position']['side'] == 'UP' else (-1 if market['position'] else 0),
            'position_pnl': (market['unrealized_pnl'] / self.trade_size) if market['unrealized_pnl'] else 0,
            'time_remaining': max(0, (datetime.fromisoformat(market['end_date']) - datetime.now()).total_seconds() / 900),
            'vol_regime': 1 if volatility > 0.3 else 0,
            'trend_regime': 1 if trend > 0.3 else (-1 if trend < -0.3 else 0)
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bot status for API response."""
        self.update()
        
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


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current bot status."""
    try:
        return jsonify(bot_state.get_status()), 200
    except Exception as e:
        return jsonify({
            'error': 'Failed to get bot status',
            'message': str(e)
        }), 500


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get bot configuration."""
    return jsonify({
        'mode': bot_state.mode,
        'trade_size': bot_state.trade_size,
        'max_exposure': bot_state.trade_size * len(bot_state.enabled_markets),
        'enabled_markets': bot_state.enabled_markets
    }), 200


@app.route('/api/config', methods=['POST'])
def update_config():
    """Update bot configuration."""
    data = request.get_json()
    
    if 'mode' in data and data['mode'] in ['train', 'inference']:
        bot_state.mode = data['mode']
    
    if 'trade_size' in data and isinstance(data['trade_size'], (int, float)) and data['trade_size'] > 0:
        bot_state.trade_size = float(data['trade_size'])
    
    if 'enabled_markets' in data and isinstance(data['enabled_markets'], list):
        valid = ['BTC', 'ETH', 'SOL', 'XRP']
        enabled = [m for m in data['enabled_markets'] if m in valid]
        if len(enabled) > 0:
            bot_state.enabled_markets = enabled
    
    return jsonify({
        'success': True,
        'mode': bot_state.mode,
        'trade_size': bot_state.trade_size,
        'max_exposure': bot_state.trade_size * len(bot_state.enabled_markets),
        'enabled_markets': bot_state.enabled_markets
    }), 200


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API info."""
    return jsonify({
        'name': 'Cross-Market State Fusion API',
        'version': '2.0.0',
        'note': 'Trade prices now use actual market prices!',
        'endpoints': {
            'GET /api/status': 'Get current bot status',
            'GET /api/config': 'Get bot configuration',
            'POST /api/config': 'Update bot configuration',
            'GET /health': 'Health check'
        }
    }), 200


if __name__ == '__main__':
    print('\n' + 
' + '='*60)
    print('Cross-Market State Fusion API Server')
    print('='*60)
    print('Starting Flask server on http://localhost:5000')
    print('Trade prices now use ACTUAL market prices!')
    print('='*60 + '
')
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )
