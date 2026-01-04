#!/usr/bin/env python3
"""Live Trading API endpoints.

Provides:
- GET /api/live-trading/status - Get live trading status
- POST /api/live-trading/config - Update configuration
- POST /api/live-trading/reset-circuit-breaker - Reset circuit breaker
- GET /api/live-trading/violations - Get risk violations
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


class LiveTradingState:
    """Manages live trading state and risk management."""
    
    def __init__(self):
        self.enabled = False
        self.mode = 'paper'  # 'paper' or 'live'
        self.api_key_configured = bool(os.getenv('POLYMARKET_API_KEY'))
        self.private_key_configured = bool(os.getenv('POLYMARKET_PRIVATE_KEY'))
        self.wallet_address = '0x' + 'a'*40 if self.private_key_configured else None
        self.errors = []
        
        # Risk state
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
        
        # Executor stats
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
                'api_key_configured': self.api_key_configured
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
                'enable_circuit_breaker': self.enable_circuit_breaker
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
                'circuit_breaker_active': self.circuit_breaker_active
            },
            'executor_stats': {
                'total_orders_placed': self.total_orders_placed,
                'total_fills': self.total_fills,
                'total_cancellations': self.total_cancellations,
                'fill_rate': fill_rate,
                'avg_slippage': 0.0,
                'active_orders': 0
            },
            'can_trade': self.enabled and not self.circuit_breaker_active,
            'errors': self.errors
        }


# Global live trading state
live_state = LiveTradingState()


@app.route('/api/live-trading/status', methods=['GET'])
def get_live_status():
    """Get live trading status."""
    try:
        return jsonify(live_state.get_status()), 200
    except Exception as e:
        return jsonify({
            'error': 'Failed to get live trading status',
            'message': str(e)
        }), 500


@app.route('/api/live-trading/config', methods=['POST'])
def update_live_config():
    """Update live trading configuration."""
    try:
        data = request.get_json()
        
        # Handle enable/disable toggle
        if 'enabled' in data:
            live_state.enabled = data['enabled']
            if data['enabled']:
                print('\n' + 
' + '='*60)
                print('🟢 LIVE TRADING ENABLED (Mock Mode)')
                print('='*60 + '
')
            else:
                print('\n' + 
' + '='*60)
                print('🔴 LIVE TRADING DISABLED')
                print('='*60 + '
')
        
        # Handle credentials update
        if 'credentials' in data:
            creds = data['credentials']
            if creds.get('api_key'):
                os.environ['POLYMARKET_API_KEY'] = creds['api_key']
                live_state.api_key_configured = True
                print('✓ API key updated')
            
            if creds.get('private_key'):
                os.environ['POLYMARKET_PRIVATE_KEY'] = creds['private_key']
                live_state.private_key_configured = True
                live_state.wallet_address = '0x' + 'a'*40
                print('✓ Private key updated')
        
        # Handle risk limits update
        if 'risk_limits' in data:
            for key, value in data['risk_limits'].items():
                if hasattr(live_state, key):
                    setattr(live_state, key, value)
            print('✓ Risk limits updated')
        
        return jsonify(live_state.get_status()), 200
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to update configuration',
            'message': str(e)
        }), 500


@app.route('/api/live-trading/reset-circuit-breaker', methods=['POST'])
def reset_cb():
    """Manually reset circuit breaker."""
    try:
        live_state.circuit_breaker_active = False
        live_state.consecutive_losses = 0
        print('\n' + 
✓ Circuit breaker manually reset
')
        return jsonify(live_state.get_status()), 200
    except Exception as e:
        return jsonify({
            'error': 'Failed to reset circuit breaker',
            'message': str(e)
        }), 500


@app.route('/api/live-trading/violations', methods=['GET'])
def get_violations():
    """Get risk violations history."""
    try:
        # Return empty list for mock version
        return jsonify({'violations': []}), 200
    except Exception as e:
        return jsonify({
            'error': 'Failed to get violations',
            'message': str(e)
        }), 500


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
        'name': 'Live Trading API',
        'version': '1.0.0',
        'endpoints': {
            'GET /api/live-trading/status': 'Get live trading status',
            'POST /api/live-trading/config': 'Update configuration',
            'POST /api/live-trading/reset-circuit-breaker': 'Reset circuit breaker',
            'GET /api/live-trading/violations': 'Get risk violations',
            'GET /health': 'Health check'
        }
    }), 200


if __name__ == '__main__':
    print('\n' + 
' + '='*60)
    print('Live Trading API Server')
    print('='*60)
    print('Starting Flask server on http://localhost:5001')
    print('Mock mode - No real orders will be placed')
    print('='*60 + '
')
    
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=False,
        threaded=True
    )
