#!/usr/bin/env python3
"""
Risk management system for live trading.

Handles:
- Position size limits
- Exposure limits
- Daily loss limits
- Drawdown protection
- Circuit breakers
"""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum


class RiskViolation(Enum):
    """Types of risk limit violations."""
    POSITION_SIZE = "position_size_exceeded"
    TOTAL_EXPOSURE = "total_exposure_exceeded"
    DAILY_LOSS = "daily_loss_limit_exceeded"
    MAX_DRAWDOWN = "max_drawdown_exceeded"
    CONSECUTIVE_LOSSES = "consecutive_losses_exceeded"
    ORDER_RATE = "order_rate_exceeded"
    SINGLE_MARKET_EXPOSURE = "single_market_exposure_exceeded"


@dataclass
class RiskLimits:
    """Risk limit configuration."""
    # Position limits
    max_position_size: float = 500.0  # Max $ per position
    max_total_exposure: float = 2000.0  # Max $ across all positions
    max_single_market_exposure: float = 1000.0  # Max $ in one market
    
    # Loss limits
    max_daily_loss: float = -1000.0  # Max $ loss per day
    max_drawdown_pct: float = 0.30  # Max 30% drawdown from peak
    max_consecutive_losses: int = 10  # Max consecutive losing trades
    
    # Rate limits
    max_orders_per_minute: int = 30  # Max order rate
    max_orders_per_hour: int = 500
    
    # Emergency stops
    emergency_stop_loss: float = -2000.0  # Emergency kill switch
    enable_circuit_breaker: bool = True  # Pause on rapid losses


@dataclass
class RiskState:
    """Current risk state."""
    # PnL tracking
    session_pnl: float = 0.0
    daily_pnl: float = 0.0
    peak_equity: float = 0.0
    current_equity: float = 0.0
    
    # Position tracking
    open_positions: Dict[str, float] = field(default_factory=dict)  # cid -> size
    total_exposure: float = 0.0
    
    # Trade tracking
    consecutive_losses: int = 0
    last_trade_pnl: float = 0.0
    total_trades: int = 0
    
    # Order rate tracking
    orders_last_minute: List[float] = field(default_factory=list)  # timestamps
    orders_last_hour: List[float] = field(default_factory=list)
    
    # Circuit breaker
    circuit_breaker_active: bool = False
    circuit_breaker_until: Optional[datetime] = None
    
    # Daily reset
    last_daily_reset: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RiskManager:
    """
    Enforces risk limits for live trading.
    
    Usage:
        risk = RiskManager(limits=RiskLimits(max_position_size=500))
        
        # Before placing order
        if not risk.can_trade(cid="btc_market", size=500):
            print("Trade blocked by risk manager")
            return
        
        # After trade closes
        risk.record_trade(pnl=25.50)
    """

    def __init__(
        self,
        limits: Optional[RiskLimits] = None,
        initial_equity: float = 10000.0,
        verbose: bool = True
    ):
        """Initialize risk manager."""
        self.limits = limits or RiskLimits()
        self.state = RiskState(
            current_equity=initial_equity,
            peak_equity=initial_equity
        )
        self.verbose = verbose
        
        # Track violations
        self.violations: List[tuple] = []  # (timestamp, violation_type, details)
        
        if self.verbose:
            self._print_limits()

    def _print_limits(self):
        """Print configured limits."""
        print(f"
{'='*60}")
        print("Risk Manager Initialized")
        print(f"{'='*60}")
        print(f"Max position size: ${self.limits.max_position_size:.0f}")
        print(f"Max total exposure: ${self.limits.max_total_exposure:.0f}")
        print(f"Max daily loss: ${abs(self.limits.max_daily_loss):.0f}")
        print(f"Max drawdown: {self.limits.max_drawdown_pct*100:.0f}%")
        print(f"Max consecutive losses: {self.limits.max_consecutive_losses}")
        print(f"Emergency stop: ${abs(self.limits.emergency_stop_loss):.0f}")
        print(f"Circuit breaker: {'Enabled' if self.limits.enable_circuit_breaker else 'Disabled'}")
        print(f"{'='*60}
")

    def can_trade(
        self,
        cid: str,
        size: float,
        asset: Optional[str] = None
    ) -> tuple[bool, Optional[RiskViolation]]:
        """
        Check if a trade is allowed under current risk limits.
        
        Args:
            cid: Market condition ID
            size: Trade size in $
            asset: Asset symbol (for single-market limits)
        
        Returns:
            (allowed, violation_type or None)
        """
        # Check circuit breaker
        if self.state.circuit_breaker_active:
            if datetime.now(timezone.utc) < self.state.circuit_breaker_until:
                if self.verbose:
                    remaining = (self.state.circuit_breaker_until - datetime.now(timezone.utc)).seconds
                    print(f"
⚠️  CIRCUIT BREAKER ACTIVE (resets in {remaining}s)")
                return False, RiskViolation.CONSECUTIVE_LOSSES
            else:
                # Reset circuit breaker
                self.state.circuit_breaker_active = False
                self.state.circuit_breaker_until = None
                if self.verbose:
                    print("
✓ Circuit breaker reset
")

        # Check position size
        if size > self.limits.max_position_size:
            self._record_violation(RiskViolation.POSITION_SIZE, f"Size ${size:.0f} > limit ${self.limits.max_position_size:.0f}")
            return False, RiskViolation.POSITION_SIZE

        # Check total exposure
        new_exposure = self.state.total_exposure + size
        if new_exposure > self.limits.max_total_exposure:
            self._record_violation(RiskViolation.TOTAL_EXPOSURE, f"Exposure ${new_exposure:.0f} > limit ${self.limits.max_total_exposure:.0f}")
            return False, RiskViolation.TOTAL_EXPOSURE

        # Check single market exposure (if asset provided)
        if asset:
            asset_exposure = sum(
                pos_size for pos_cid, pos_size in self.state.open_positions.items()
                if asset.upper() in pos_cid.upper()
            )
            new_asset_exposure = asset_exposure + size
            if new_asset_exposure > self.limits.max_single_market_exposure:
                self._record_violation(
                    RiskViolation.SINGLE_MARKET_EXPOSURE,
                    f"{asset} exposure ${new_asset_exposure:.0f} > limit ${self.limits.max_single_market_exposure:.0f}"
                )
                return False, RiskViolation.SINGLE_MARKET_EXPOSURE

        # Check daily loss limit
        if self.state.daily_pnl <= self.limits.max_daily_loss:
            self._record_violation(RiskViolation.DAILY_LOSS, f"Daily PnL ${self.state.daily_pnl:.2f} hit limit ${self.limits.max_daily_loss:.2f}")
            return False, RiskViolation.DAILY_LOSS

        # Check emergency stop
        if self.state.session_pnl <= self.limits.emergency_stop_loss:
            self._record_violation(RiskViolation.DAILY_LOSS, f"EMERGENCY STOP: PnL ${self.state.session_pnl:.2f}")
            if self.verbose:
                print(f"
🚨 EMERGENCY STOP TRIGGERED 🚨")
                print(f"Session PnL: ${self.state.session_pnl:.2f}")
                print(f"Emergency limit: ${self.limits.emergency_stop_loss:.2f}")
                print(f"ALL TRADING HALTED
")
            return False, RiskViolation.DAILY_LOSS

        # Check drawdown
        if self.state.peak_equity > 0:
            drawdown = (self.state.current_equity - self.state.peak_equity) / self.state.peak_equity
            if drawdown < -self.limits.max_drawdown_pct:
                self._record_violation(RiskViolation.MAX_DRAWDOWN, f"Drawdown {drawdown*100:.1f}% > limit {self.limits.max_drawdown_pct*100:.0f}%")
                return False, RiskViolation.MAX_DRAWDOWN

        # Check order rate
        now = time.time()
        self._cleanup_order_timestamps(now)
        
        if len(self.state.orders_last_minute) >= self.limits.max_orders_per_minute:
            self._record_violation(RiskViolation.ORDER_RATE, f"Rate limit: {len(self.state.orders_last_minute)} orders/min")
            return False, RiskViolation.ORDER_RATE
        
        if len(self.state.orders_last_hour) >= self.limits.max_orders_per_hour:
            self._record_violation(RiskViolation.ORDER_RATE, f"Rate limit: {len(self.state.orders_last_hour)} orders/hour")
            return False, RiskViolation.ORDER_RATE

        # All checks passed
        return True, None

    def record_order(self):
        """Record an order for rate limiting."""
        now = time.time()
        self.state.orders_last_minute.append(now)
        self.state.orders_last_hour.append(now)

    def record_position_open(self, cid: str, size: float):
        """Record opening a position."""
        self.state.open_positions[cid] = size
        self.state.total_exposure = sum(self.state.open_positions.values())
        
        if self.verbose:
            print(f"  [RISK] Position opened: {cid[:16]}... ${size:.0f}")
            print(f"  [RISK] Total exposure: ${self.state.total_exposure:.0f}")

    def record_position_close(self, cid: str):
        """Record closing a position."""
        if cid in self.state.open_positions:
            size = self.state.open_positions.pop(cid)
            self.state.total_exposure = sum(self.state.open_positions.values())
            
            if self.verbose:
                print(f"  [RISK] Position closed: {cid[:16]}...")
                print(f"  [RISK] Total exposure: ${self.state.total_exposure:.0f}")

    def record_trade(self, pnl: float):
        """Record a completed trade."""
        self.state.session_pnl += pnl
        self.state.daily_pnl += pnl
        self.state.current_equity += pnl
        self.state.total_trades += 1
        
        # Update peak equity
        if self.state.current_equity > self.state.peak_equity:
            self.state.peak_equity = self.state.current_equity
        
        # Track consecutive losses
        if pnl < 0:
            self.state.consecutive_losses += 1
            
            # Check circuit breaker
            if (
                self.limits.enable_circuit_breaker and
                self.state.consecutive_losses >= self.limits.max_consecutive_losses
            ):
                self._trigger_circuit_breaker()
        else:
            self.state.consecutive_losses = 0
        
        self.state.last_trade_pnl = pnl
        
        # Check for daily reset
        self._check_daily_reset()
        
        if self.verbose and self.state.total_trades % 10 == 0:
            self._print_status()

    def _trigger_circuit_breaker(self):
        """Activate circuit breaker after too many losses."""
        self.state.circuit_breaker_active = True
        self.state.circuit_breaker_until = datetime.now(timezone.utc) + timedelta(minutes=30)
        
        if self.verbose:
            print(f"
{'='*60}")
            print("🔴 CIRCUIT BREAKER TRIGGERED 🔴")
            print(f"{'='*60}")
            print(f"Consecutive losses: {self.state.consecutive_losses}")
            print(f"Trading paused for 30 minutes")
            print(f"Resume at: {self.state.circuit_breaker_until.strftime('%H:%M:%S')}")
            print(f"{'='*60}
")

    def _check_daily_reset(self):
        """Reset daily counters at midnight UTC."""
        now = datetime.now(timezone.utc)
        if now.date() > self.state.last_daily_reset.date():
            if self.verbose:
                print(f"
{'='*60}")
                print("Daily Reset")
                print(f"{'='*60}")
                print(f"Previous day PnL: ${self.state.daily_pnl:+.2f}")
                print(f"Session PnL: ${self.state.session_pnl:+.2f}")
                print(f"{'='*60}
")
            
            self.state.daily_pnl = 0.0
            self.state.last_daily_reset = now

    def _cleanup_order_timestamps(self, now: float):
        """Remove old timestamps for rate limiting."""
        # Remove orders older than 1 minute
        self.state.orders_last_minute = [
            ts for ts in self.state.orders_last_minute
            if now - ts < 60
        ]
        
        # Remove orders older than 1 hour
        self.state.orders_last_hour = [
            ts for ts in self.state.orders_last_hour
            if now - ts < 3600
        ]

    def _record_violation(self, violation: RiskViolation, details: str):
        """Record a risk violation."""
        self.violations.append((datetime.now(timezone.utc), violation, details))
        
        if self.verbose:
            print(f"
⚠️  RISK VIOLATION: {violation.value}")
            print(f"    {details}
")

    def _print_status(self):
        """Print current risk status."""
        drawdown = 0.0
        if self.state.peak_equity > 0:
            drawdown = (self.state.current_equity - self.state.peak_equity) / self.state.peak_equity
        
        print(f"
{'='*60}")
        print("Risk Status")
        print(f"{'='*60}")
        print(f"Session PnL: ${self.state.session_pnl:+.2f}")
        print(f"Daily PnL: ${self.state.daily_pnl:+.2f}")
        print(f"Current equity: ${self.state.current_equity:.2f}")
        print(f"Peak equity: ${self.state.peak_equity:.2f}")
        print(f"Drawdown: {drawdown*100:+.1f}%")
        print(f"Open positions: {len(self.state.open_positions)}")
        print(f"Total exposure: ${self.state.total_exposure:.0f}")
        print(f"Consecutive losses: {self.state.consecutive_losses}")
        print(f"Total trades: {self.state.total_trades}")
        print(f"Violations: {len(self.violations)}")
        print(f"{'='*60}
")

    def get_status(self) -> Dict:
        """Get current risk status as dict."""
        drawdown = 0.0
        if self.state.peak_equity > 0:
            drawdown = (self.state.current_equity - self.state.peak_equity) / self.state.peak_equity
        
        return {
            "session_pnl": self.state.session_pnl,
            "daily_pnl": self.state.daily_pnl,
            "current_equity": self.state.current_equity,
            "peak_equity": self.state.peak_equity,
            "drawdown_pct": drawdown * 100,
            "open_positions": len(self.state.open_positions),
            "total_exposure": self.state.total_exposure,
            "consecutive_losses": self.state.consecutive_losses,
            "total_trades": self.state.total_trades,
            "violations": len(self.violations),
            "circuit_breaker_active": self.state.circuit_breaker_active,
        }

    def reset_circuit_breaker(self):
        """Manually reset circuit breaker."""
        self.state.circuit_breaker_active = False
        self.state.circuit_breaker_until = None
        self.state.consecutive_losses = 0
        
        if self.verbose:
            print("
✓ Circuit breaker manually reset
")

    def get_violations(self) -> List[tuple]:
        """Get list of risk violations."""
        return self.violations

    def print_violations(self):
        """Print all recorded violations."""
        if not self.violations:
            print("
✓ No risk violations recorded
")
            return
        
        print(f"
{'='*60}")
        print(f"Risk Violations ({len(self.violations)})")
        print(f"{'='*60}")
        for timestamp, violation, details in self.violations[-10:]:  # Last 10
            print(f"{timestamp.strftime('%H:%M:%S')} | {violation.value}")
            print(f"  {details}")
        print(f"{'='*60}
")
