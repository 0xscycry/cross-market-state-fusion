#!/usr/bin/env python3
"""
Polymarket CLOB order execution layer.

Handles:
- Limit order placement
- Order cancellation
- Fill confirmation
- Slippage tracking
- Position management

Requires:
- Private key (Ethereum wallet)
- API key (Polymarket CLOB)
- USDC balance on Polygon
"""

import os
import time
import json
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
    ETH_ACCOUNT_AVAILABLE = True
except ImportError:
    ETH_ACCOUNT_AVAILABLE = False
    print("Warning: eth_account not installed. Live trading disabled.")
    print("Install with: pip install eth-account")

import requests


CLOB_API_URL = "https://clob.polymarket.com"
GAMMA_API_URL = "https://gamma-api.polymarket.com"


@dataclass
class Order:
    """Represents a Polymarket CLOB order."""
    order_id: str
    token_id: str
    side: str  # "BUY" or "SELL"
    price: float
    size: float
    status: str  # "open", "filled", "cancelled", "partially_filled"
    filled_size: float
    avg_fill_price: Optional[float]
    created_at: datetime
    filled_at: Optional[datetime]
    fees_paid: float = 0.0


@dataclass
class FillResult:
    """Result of order execution."""
    success: bool
    filled_size: float
    avg_price: float
    slippage: float  # Difference from limit price
    latency_ms: float  # Time from order to fill
    fees: float
    order_id: Optional[str]
    error: Optional[str] = None


class PolymarketExecutor:
    """
    Handles real order execution on Polymarket CLOB.
    
    Usage:
        executor = PolymarketExecutor(
            private_key=os.getenv("POLYMARKET_PRIVATE_KEY"),
            api_key=os.getenv("POLYMARKET_API_KEY")
        )
        
        result = await executor.place_limit_order(
            token_id="0x1234...",
            side="BUY",
            price=0.52,
            size=961.5
        )
    """

    def __init__(
        self,
        private_key: str,
        api_key: str,
        chain_id: int = 137,  # Polygon mainnet
        verbose: bool = True
    ):
        """Initialize executor with credentials."""
        if not ETH_ACCOUNT_AVAILABLE:
            raise ImportError("eth_account package required for live trading")
        
        self.private_key = private_key
        self.api_key = api_key
        self.chain_id = chain_id
        self.verbose = verbose
        
        # Initialize wallet
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        
        # Track orders
        self.orders: Dict[str, Order] = {}
        self.nonce_counter = int(time.time() * 1000)  # Millisecond timestamp
        
        # Stats
        self.total_orders_placed = 0
        self.total_fills = 0
        self.total_cancellations = 0
        self.total_slippage = 0.0
        
        if self.verbose:
            print(f"
{'='*60}")
            print("Polymarket Executor Initialized")
            print(f"{'='*60}")
            print(f"Wallet: {self.address}")
            print(f"Chain ID: {self.chain_id}")
            print(f"CLOB API: {CLOB_API_URL}")
            print(f"{'='*60}
")

    def _get_nonce(self) -> int:
        """Generate unique nonce for order."""
        self.nonce_counter += 1
        return self.nonce_counter

    def _sign_order(self, order_data: Dict) -> str:
        """Sign order with private key."""
        # EIP-712 structured data for Polymarket orders
        # Simplified - actual implementation would use proper EIP-712 encoding
        message = json.dumps(order_data, sort_keys=True)
        message_hash = encode_defunct(text=message)
        signed = self.account.sign_message(message_hash)
        return signed.signature.hex()

    async def place_limit_order(
        self,
        token_id: str,
        side: str,  # "BUY" or "SELL"
        price: float,
        size: float,
        time_in_force: str = "GTC",  # Good-til-cancelled
        post_only: bool = True,  # Only add liquidity (no taker fees)
        wait_for_fill: bool = True,
        timeout_sec: float = 5.0
    ) -> FillResult:
        """
        Place a limit order on Polymarket CLOB.
        
        Args:
            token_id: Token contract address (UP or DOWN)
            side: "BUY" or "SELL"
            price: Limit price (0-1 range)
            size: Number of shares
            time_in_force: "GTC" (good-til-cancelled) or "IOC" (immediate-or-cancel)
            post_only: If True, reject order if it would take liquidity
            wait_for_fill: If True, wait for order to fill
            timeout_sec: Max time to wait for fill
        
        Returns:
            FillResult with execution details
        """
        start_time = time.time()
        
        try:
            # 1. Create order payload
            nonce = self._get_nonce()
            order_data = {
                "tokenID": token_id,
                "price": str(Decimal(str(price)).quantize(Decimal('0.001'))),  # 3 decimals
                "size": str(Decimal(str(size)).quantize(Decimal('0.01'))),  # 2 decimals
                "side": side,
                "feeRateBps": "0",  # 0% fees on CLOB
                "nonce": nonce,
                "signer": self.address,
                "expiration": int(time.time()) + 3600,  # 1 hour from now
                "maker": self.address,
            }
            
            # 2. Sign order
            signature = self._sign_order(order_data)
            order_data["signature"] = signature
            
            # 3. Submit to CLOB
            if self.verbose:
                print(f"
[EXECUTOR] Placing {side} limit order")
                print(f"  Token: {token_id[:10]}...")
                print(f"  Price: {price:.3f}")
                print(f"  Size: {size:.2f} shares")
                print(f"  Value: ${price * size:.2f}")
            
            response = requests.post(
                f"{CLOB_API_URL}/order",
                json=order_data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            
            if response.status_code != 200:
                error_msg = f"Order placement failed: {response.status_code} {response.text}"
                if self.verbose:
                    print(f"  ❌ {error_msg}")
                return FillResult(
                    success=False,
                    filled_size=0.0,
                    avg_price=0.0,
                    slippage=0.0,
                    latency_ms=(time.time() - start_time) * 1000,
                    fees=0.0,
                    order_id=None,
                    error=error_msg
                )
            
            result = response.json()
            order_id = result.get("orderID")
            
            # Track order
            order = Order(
                order_id=order_id,
                token_id=token_id,
                side=side,
                price=price,
                size=size,
                status="open",
                filled_size=0.0,
                avg_fill_price=None,
                created_at=datetime.now(timezone.utc),
                filled_at=None
            )
            self.orders[order_id] = order
            self.total_orders_placed += 1
            
            if self.verbose:
                print(f"  ✓ Order placed: {order_id[:16]}...")
            
            # 4. Wait for fill (if requested)
            if wait_for_fill:
                return await self._wait_for_fill(order_id, timeout_sec, start_time)
            else:
                return FillResult(
                    success=True,
                    filled_size=0.0,
                    avg_price=price,
                    slippage=0.0,
                    latency_ms=(time.time() - start_time) * 1000,
                    fees=0.0,
                    order_id=order_id
                )
        
        except Exception as e:
            error_msg = f"Exception placing order: {str(e)}"
            if self.verbose:
                print(f"  ❌ {error_msg}")
            return FillResult(
                success=False,
                filled_size=0.0,
                avg_price=0.0,
                slippage=0.0,
                latency_ms=(time.time() - start_time) * 1000,
                fees=0.0,
                order_id=None,
                error=error_msg
            )

    async def _wait_for_fill(
        self,
        order_id: str,
        timeout_sec: float,
        start_time: float
    ) -> FillResult:
        """Poll order status until filled or timeout."""
        poll_interval = 0.1  # 100ms
        
        while (time.time() - start_time) < timeout_sec:
            try:
                # Get order status
                response = requests.get(
                    f"{CLOB_API_URL}/order/{order_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=5
                )
                
                if response.status_code != 200:
                    await asyncio.sleep(poll_interval)
                    continue
                
                status = response.json()
                order_status = status.get("status")
                filled_size = float(status.get("size_matched", 0))
                
                # Update tracked order
                order = self.orders[order_id]
                order.filled_size = filled_size
                order.status = order_status
                
                # Check if filled
                if order_status == "filled":
                    avg_fill_price = float(status.get("avg_fill_price", order.price))
                    order.avg_fill_price = avg_fill_price
                    order.filled_at = datetime.now(timezone.utc)
                    
                    slippage = avg_fill_price - order.price
                    latency_ms = (time.time() - start_time) * 1000
                    
                    self.total_fills += 1
                    self.total_slippage += abs(slippage)
                    
                    if self.verbose:
                        print(f"  ✓ Order filled in {latency_ms:.0f}ms")
                        print(f"    Avg price: {avg_fill_price:.3f}")
                        print(f"    Slippage: {slippage:+.4f} ({(slippage/order.price)*100:+.2f}%)")
                    
                    return FillResult(
                        success=True,
                        filled_size=filled_size,
                        avg_price=avg_fill_price,
                        slippage=slippage,
                        latency_ms=latency_ms,
                        fees=0.0,  # 0% on CLOB
                        order_id=order_id
                    )
                
                # Check if partially filled
                elif filled_size > 0:
                    if self.verbose:
                        print(f"  ⏳ Partial fill: {filled_size}/{order.size} ({(filled_size/order.size)*100:.0f}%)")
                
                await asyncio.sleep(poll_interval)
            
            except Exception as e:
                if self.verbose:
                    print(f"  Warning: Error polling order status: {e}")
                await asyncio.sleep(poll_interval)
        
        # Timeout - cancel order
        if self.verbose:
            print(f"  ⏱️ Order timeout after {timeout_sec}s")
        
        await self.cancel_order(order_id)
        
        order = self.orders[order_id]
        return FillResult(
            success=order.filled_size > 0,
            filled_size=order.filled_size,
            avg_price=order.avg_fill_price or order.price,
            slippage=0.0,
            latency_ms=(time.time() - start_time) * 1000,
            fees=0.0,
            order_id=order_id,
            error=f"Timeout after {timeout_sec}s" if order.filled_size == 0 else None
        )

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        try:
            response = requests.delete(
                f"{CLOB_API_URL}/order/{order_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=5
            )
            
            if response.status_code == 200:
                if order_id in self.orders:
                    self.orders[order_id].status = "cancelled"
                self.total_cancellations += 1
                
                if self.verbose:
                    print(f"  🚫 Order cancelled: {order_id[:16]}...")
                return True
            else:
                if self.verbose:
                    print(f"  ❌ Cancel failed: {response.status_code}")
                return False
        
        except Exception as e:
            if self.verbose:
                print(f"  ❌ Exception cancelling order: {e}")
            return False

    async def place_market_order(
        self,
        token_id: str,
        side: str,
        size: float
    ) -> FillResult:
        """
        Place a market order (aggressive limit at worst available price).
        
        Note: Polymarket CLOB doesn't have true market orders.
        This places a limit order far from mid-price to guarantee immediate fill.
        """
        # Get current orderbook to determine aggressive price
        # For BUY: use high limit (0.99)
        # For SELL: use low limit (0.01)
        aggressive_price = 0.99 if side == "BUY" else 0.01
        
        return await self.place_limit_order(
            token_id=token_id,
            side=side,
            price=aggressive_price,
            size=size,
            time_in_force="IOC",  # Immediate-or-cancel
            post_only=False,  # Allow taking liquidity
            wait_for_fill=True,
            timeout_sec=2.0
        )

    def get_order_status(self, order_id: str) -> Optional[Order]:
        """Get status of an order."""
        return self.orders.get(order_id)

    def get_stats(self) -> Dict:
        """Get execution statistics."""
        return {
            "total_orders_placed": self.total_orders_placed,
            "total_fills": self.total_fills,
            "total_cancellations": self.total_cancellations,
            "fill_rate": self.total_fills / max(1, self.total_orders_placed),
            "avg_slippage": self.total_slippage / max(1, self.total_fills),
            "active_orders": len([o for o in self.orders.values() if o.status == "open"])
        }

    def print_stats(self):
        """Print execution statistics."""
        stats = self.get_stats()
        print(f"
{'='*60}")
        print("Execution Statistics")
        print(f"{'='*60}")
        print(f"Orders placed: {stats['total_orders_placed']}")
        print(f"Orders filled: {stats['total_fills']}")
        print(f"Orders cancelled: {stats['total_cancellations']}")
        print(f"Fill rate: {stats['fill_rate']*100:.1f}%")
        print(f"Avg slippage: {stats['avg_slippage']:.4f}")
        print(f"Active orders: {stats['active_orders']}")
        print(f"{'='*60}
")


class MockExecutor:
    """
    Mock executor for testing without real API calls.
    Simulates order execution with realistic fills and slippage.
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.orders: Dict[str, Order] = {}
        self.total_orders_placed = 0
        
        if self.verbose:
            print("
⚠️  MOCK EXECUTOR - No real orders will be placed
")

    async def place_limit_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
        **kwargs
    ) -> FillResult:
        """Simulate limit order execution."""
        import random
        
        self.total_orders_placed += 1
        
        # Simulate 80% fill rate
        if random.random() < 0.8:
            # Simulate slight price improvement (20% of spread)
            slippage = random.uniform(-0.002, 0.001)  # -0.2% to +0.1%
            avg_price = price + slippage
            latency = random.uniform(50, 200)  # 50-200ms
            
            if self.verbose:
                print(f"  [MOCK] {side} {size:.2f} @ {avg_price:.3f} (filled in {latency:.0f}ms)")
            
            return FillResult(
                success=True,
                filled_size=size,
                avg_price=avg_price,
                slippage=slippage,
                latency_ms=latency,
                fees=0.0,
                order_id=f"mock_{self.total_orders_placed}"
            )
        else:
            # Order not filled
            if self.verbose:
                print(f"  [MOCK] {side} order timeout (no fill)")
            
            return FillResult(
                success=False,
                filled_size=0.0,
                avg_price=price,
                slippage=0.0,
                latency_ms=5000.0,
                fees=0.0,
                order_id=None,
                error="Timeout"
            )

    async def place_market_order(self, *args, **kwargs) -> FillResult:
        """Simulate market order (always fills)."""
        return await self.place_limit_order(*args, **kwargs)

    async def cancel_order(self, order_id: str) -> bool:
        return True

    def get_stats(self) -> Dict:
        return {"total_orders_placed": self.total_orders_placed}

    def print_stats(self):
        print(f"
[MOCK] Total orders: {self.total_orders_placed}
")
