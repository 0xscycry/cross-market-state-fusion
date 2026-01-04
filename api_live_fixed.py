#!/usr/bin/env python3
import os, time, random
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

class LiveTradingState:
    def __init__(self):
        self.enabled = False
        self.mode = 'paper'
        self.api_key_configured = bool(os.getenv('POLYMARKET_API_KEY'))
        self.private_key_configured = bool(os.getenv('POLYMARKET_PRIVATE_KEY'))
        self.wallet_address = '0x' + 'a'*40 if self.private_key_configured else None
        self.errors = []
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
        self.total_orders_placed = 0
        self.total_fills = 0
        self.total_cancellations = 0
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
    
    def get_status(self):
        drawdown_pct = ((self.current_equity - self.peak_equity) / self.peak_equity) * 100 if self.peak_equity > 0 else 0.0
        fill_rate = self.total_fills / self.total_orders_placed if self.total_orders_placed > 0 else 0.0
        return {
            'config': {'enabled': self.enabled, 'mode': self.mode, 'executor_type': 'mock', 'wallet_address': self.wallet_address, 'api_key_configured': self.api_key_configured},
            'risk_limits': {'max_position_size': self.max_position_size, 'max_total_exposure': self.max_total_exposure, 'max_single_market_exposure': self.max_single_market_exposure, 'max_daily_loss': self.max_daily_loss, 'max_drawdown_pct': self.max_drawdown_pct, 'max_consecutive_losses': self.max_consecutive_losses, 'max_orders_per_minute': self.max_orders_per_minute, 'max_orders_per_hour': self.max_orders_per_hour, 'emergency_stop_loss': self.emergency_stop_loss, 'enable_circuit_breaker': self.enable_circuit_breaker},
            'risk_state': {'session_pnl': self.session_pnl, 'daily_pnl': self.daily_pnl, 'current_equity': self.current_equity, 'peak_equity': self.peak_equity, 'drawdown_pct': drawdown_pct, 'open_positions': self.open_positions, 'total_exposure': self.total_exposure, 'consecutive_losses': self.consecutive_losses, 'total_trades': self.total_trades, 'violations': self.violations, 'circuit_breaker_active': self.circuit_breaker_active},
            'executor_stats': {'total_orders_placed': self.total_orders_placed, 'total_fills': self.total_fills, 'total_cancellations': self.total_cancellations, 'fill_rate': fill_rate, 'avg_slippage': 0.0, 'active_orders': 0},
            'can_trade': self.enabled and not self.circuit_breaker_active,
            'errors': self.errors
        }

live = LiveTradingState()

@app.route('/api/live-trading/status', methods=['GET'])
def get_live_status():
    return jsonify(live.get_status()), 200

@app.route('/api/live-trading/config', methods=['POST'])
def update_live_config():
    data = request.get_json()
    if 'enabled' in data:
        live.enabled = data['enabled']
        print('Live trading enabled' if data['enabled'] else 'Live trading disabled')
    if 'credentials' in data:
        creds = data['credentials']
        if creds.get('api_key'):
            os.environ['POLYMARKET_API_KEY'] = creds['api_key']
            live.api_key_configured = True
        if creds.get('private_key'):
            os.environ['POLYMARKET_PRIVATE_KEY'] = creds['private_key']
            live.private_key_configured = True
            live.wallet_address = '0x' + 'a'*40
    if 'risk_limits' in data:
        for k, v in data['risk_limits'].items():
            if hasattr(live, k):
                setattr(live, k, v)
    return jsonify(live.get_status()), 200

@app.route('/api/live-trading/reset-circuit-breaker', methods=['POST'])
def reset_cb():
    live.circuit_breaker_active = False
    live.consecutive_losses = 0
    return jsonify(live.get_status()), 200

@app.route('/api/live-trading/violations', methods=['GET'])
def get_violations():
    return jsonify({'violations': []}), 200

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200

if __name__ == '__main__':
    print('Live Trading API running on port 5001')
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
