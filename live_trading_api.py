#!/usr/bin/env python3
"""
Live Trading API endpoints for Cross-Market State Fusion.

Provides:
- GET /api/live-trading/status - Get live trading status
- POST /api/live-trading/config - Update live trading configuration
- POST /api/live-trading/toggle - Enable/disable live trading
- GET /api/live-trading/violations - Get risk violations

Integrates with:
- helpers/polymarket_executor.py - Order execution
- helpers/risk_manager.py - Risk management
"""

import os
import json
from typing import Dict, Any, Optional
from flask import Blueprint, jsonify, request
from datetime import datetime, timezone

try:
    from helpers.polymarket_executor import PolymarketExecutor, MockExecutor
    from helpers.risk_manager import RiskManager, RiskLimits
    LIVE_TRADING_AVAILABLE = True
except ImportError:
    LIVE_TRADING_AVAILABLE = False
    print("Warning: Live trading modules not available")

# Create Blueprint
live_trading_bp = Blueprint('live_trading', __name__, url_prefix='/api/live-trading')

# Global state
class LiveTradingState:
    def __init__(self):
        self.enabled = False
        self.mode = 'paper'  # 'paper' or 'live'
        self.executor: Optional[Any] = None
        self.risk_manager: Optional[RiskManager] = None
        self.api_key_configured = False
        self.private_key_configured = False
        self.wallet_address: Optional[str] = None
        self.errors = []
        
        # Check environment variables
        self._check_credentials()
        
        # Initialize risk manager (always available)
        if LIVE_TRADING_AVAILABLE:
            self.risk_manager = RiskManager(
                limits=RiskLimits(
                    max_position_size=500.0,
                    max_total_exposure=2000.0,
                    max_single_market_exposure=1000.0,
                    max_daily_loss=-1000.0,
                    max_drawdown_pct=0.30,
                    max_consecutive_losses=10,
                    max_orders_per_minute=30,
                    max_orders_per_hour=500,
                    emergency_stop_loss=-2000.0,
                    enable_circuit_breaker=True
                ),
                initial_equity=10000.0,
                verbose=False  # Set to True for detailed logs
            )
    
    def _check_credentials(self):
        """Check if API credentials are configured."""
        api_key = os.getenv('POLYMARKET_API_KEY')
        private_key = os.getenv('POLYMARKET_PRIVATE_KEY')
        
        self.api_key_configured = api_key is not None and len(api_key) > 0
        self.private_key_configured = private_key is not None and len(private_key) > 0
        
        if self.private_key_configured and LIVE_TRADING_AVAILABLE:
            try:
                from eth_account import Account
                account = Account.from_key(private_key)
                self.wallet_address = account.address
            except Exception as e:
                self.errors.append(f"Invalid private key: {str(e)}")
                self.private_key_configured = False
    
    def initialize_executor(self, use_mock: bool = False):
        """Initialize order executor."""
        if not LIVE_TRADING_AVAILABLE:
            self.errors.append("Live trading modules not installed")
            return False
        
        try:
            if use_mock or not (self.api_key_configured and self.private_key_configured):
                # Use mock executor for testing
                self.executor = MockExecutor(verbose=True)
                self.mode = 'paper'
                return True
            else:
                # Use real executor
                self.executor = PolymarketExecutor(
                    private_key=os.getenv('POLYMARKET_PRIVATE_KEY'),
                    api_key=os.getenv('POLYMARKET_API_KEY'),
                    chain_id=137,  # Polygon mainnet
                    verbose=True
                )
                self.mode = 'live'
                return True
        except Exception as e:
            self.errors.append(f"Failed to initialize executor: {str(e)}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current live trading status."""
        # Get risk state
        risk_state = {
            'session_pnl': 0.0,
            'daily_pnl': 0.0,
            'current_equity': 10000.0,
            'peak_equity': 10000.0,
            'drawdown_pct': 0.0,
            'open_positions': 0,
            'total_exposure': 0.0,
            'consecutive_losses': 0,
            'total_trades': 0,
            'violations': 0,
            'circuit_breaker_active': False,
        }
        
        if self.risk_manager:
            risk_state = self.risk_manager.get_status()
        
        # Get executor stats
        executor_stats = {
            'total_orders_placed': 0,
            'total_fills': 0,
            'total_cancellations': 0,
            'fill_rate': 0.0,
            'avg_slippage': 0.0,
            'active_orders': 0,
        }
        
        if self.executor:
            executor_stats = self.executor.get_stats()
        
        # Check if can trade
        can_trade = True
        if self.risk_manager:
            can_trade, _ = self.risk_manager.can_trade(cid='test', size=100.0)
        
        return {
            'config': {
                'enabled': self.enabled,
                'mode': self.mode,
                'executor_type': 'mock' if isinstance(self.executor, MockExecutor) else 'real',
                'wallet_address': self.wallet_address,
                'api_key_configured': self.api_key_configured,
            },
            'risk_limits': {
                'max_position_size': self.risk_manager.limits.max_position_size if self.risk_manager else 500.0,
                'max_total_exposure': self.risk_manager.limits.max_total_exposure if self.risk_manager else 2000.0,
                'max_single_market_exposure': self.risk_manager.limits.max_single_market_exposure if self.risk_manager else 1000.0,
                'max_daily_loss': self.risk_manager.limits.max_daily_loss if self.risk_manager else -1000.0,
                'max_drawdown_pct': self.risk_manager.limits.max_drawdown_pct if self.risk_manager else 0.30,
                'max_consecutive_losses': self.risk_manager.limits.max_consecutive_losses if self.risk_manager else 10,
                'max_orders_per_minute': self.risk_manager.limits.max_orders_per_minute if self.risk_manager else 30,
                'max_orders_per_hour': self.risk_manager.limits.max_orders_per_hour if self.risk_manager else 500,
                'emergency_stop_loss': self.risk_manager.limits.emergency_stop_loss if self.risk_manager else -2000.0,
                'enable_circuit_breaker': self.risk_manager.limits.enable_circuit_breaker if self.risk_manager else True,
            },
            'risk_state': risk_state,
            'executor_stats': executor_stats,
            'can_trade': can_trade and self.enabled,
            'errors': self.errors,
        }

# Global instance
live_trading_state = LiveTradingState()

@live_trading_bp.route('/status', methods=['GET'])
def get_status():
    """Get live trading status."""
    try:
        status = live_trading_state.get_status()
        return jsonify(status), 200
    except Exception as e:
        return jsonify({
            'error': 'Failed to get live trading status',
            'message': str(e)
        }), 500

@live_trading_bp.route('/config', methods=['POST'])
def update_config():
    """Update live trading configuration."""
    try:
        data = request.get_json()
        
        # Handle enable/disable toggle
        if 'enabled' in data:
            enabled = data['enabled']
            
            if enabled and not live_trading_state.enabled:
                # Enabling live trading
                if not LIVE_TRADING_AVAILABLE:
                    return jsonify({
                        'error': 'Live trading not available',
                        'message': 'Required packages not installed'
                    }), 400
                
                # Initialize executor
                use_mock = not (live_trading_state.api_key_configured and live_trading_state.private_key_configured)
                if not live_trading_state.initialize_executor(use_mock=use_mock):
                    return jsonify({
                        'error': 'Failed to initialize live trading',
                        'message': '; '.join(live_trading_state.errors)
                    }), 500
                
                live_trading_state.enabled = True
                print(f"
{'='*60}")
                print("🟢 LIVE TRADING ENABLED")
                print(f"Mode: {live_trading_state.mode}")
                print(f"Executor: {'Mock' if use_mock else 'Real'}")
                print(f"{'='*60}
")
            
            elif not enabled and live_trading_state.enabled:
                # Disabling live trading
                live_trading_state.enabled = False
                print(f"
{'='*60}")
                print("🔴 LIVE TRADING DISABLED")
                print(f"{'='*60}
")
        
        # Handle risk limits update
        if 'risk_limits' in data and live_trading_state.risk_manager:
            limits_data = data['risk_limits']
            limits = live_trading_state.risk_manager.limits
            
            # Update limits
            if 'max_position_size' in limits_data:
                limits.max_position_size = float(limits_data['max_position_size'])
            if 'max_total_exposure' in limits_data:
                limits.max_total_exposure = float(limits_data['max_total_exposure'])
            if 'max_single_market_exposure' in limits_data:
                limits.max_single_market_exposure = float(limits_data['max_single_market_exposure'])
            if 'max_daily_loss' in limits_data:
                limits.max_daily_loss = float(limits_data['max_daily_loss'])
            if 'max_drawdown_pct' in limits_data:
                limits.max_drawdown_pct = float(limits_data['max_drawdown_pct'])
            if 'max_consecutive_losses' in limits_data:
                limits.max_consecutive_losses = int(limits_data['max_consecutive_losses'])
            if 'emergency_stop_loss' in limits_data:
                limits.emergency_stop_loss = float(limits_data['emergency_stop_loss'])
            
            print("✓ Risk limits updated")
        
        # Return updated status
        status = live_trading_state.get_status()
        return jsonify(status), 200
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to update configuration',
            'message': str(e)
        }), 500

@live_trading_bp.route('/violations', methods=['GET'])
def get_violations():
    """Get risk violations history."""
    try:
        if not live_trading_state.risk_manager:
            return jsonify({'violations': []}), 200
        
        violations = live_trading_state.risk_manager.get_violations()
        
        # Format violations for response
        formatted = [
            {
                'timestamp': timestamp.isoformat(),
                'type': violation.value,
                'details': details
            }
            for timestamp, violation, details in violations[-50:]  # Last 50
        ]
        
        return jsonify({'violations': formatted}), 200
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to get violations',
            'message': str(e)
        }), 500

@live_trading_bp.route('/reset-circuit-breaker', methods=['POST'])
def reset_circuit_breaker():
    """Manually reset circuit breaker."""
    try:
        if not live_trading_state.risk_manager:
            return jsonify({'error': 'Risk manager not initialized'}), 400
        
        live_trading_state.risk_manager.reset_circuit_breaker()
        
        status = live_trading_state.get_status()
        return jsonify(status), 200
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to reset circuit breaker',
            'message': str(e)
        }), 500

# Function to get executor instance (for use in run.py)
def get_live_trading_executor():
    """Get the live trading executor instance."""
    return live_trading_state.executor if live_trading_state.enabled else None

# Function to get risk manager instance (for use in run.py)
def get_risk_manager():
    """Get the risk manager instance."""
    return live_trading_state.risk_manager

# Function to check if live trading is enabled
def is_live_trading_enabled():
    """Check if live trading is enabled."""
    return live_trading_state.enabled and live_trading_state.executor is not None
