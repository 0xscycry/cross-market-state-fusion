#!/usr/bin/env python3
"""
Polymarket CLOB order execution.

Handles order placement, cancellation, and fill tracking for live trading.
Uses limit orders by default for better price control.

Requires:
    - Private key (for order signing)
    - API key (for CLOB authentication)
    - USDC balance on Polygon network
"""

import os
import time
import hmac
import hashlib
import requests
from typing import Dict, Optional, List
from datetime import datetime, timezone
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3


class OrderStatus:
    """Order status constants."""
    PENDING = "pending"
    OPEN = "open"
    MATCHED = "matched"
    FILLED = "filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class PolymarketExecutor:
    """
    Execute trades on Polymarket CLOB.
    
    Supports limit orders with fill tracking and partial fill handling.
    """
    
    def __init__(self, private_key: str, api_key: str, chain_id: int = 137):
        """
        Initialize executor.
        
        Args:
            private_key: Ethereum private key (0x...)
            api_key: Polymarket CLOB API key
            chain_id: Polygon mainnet (137) or testnet
        """
        self.private_key = private_key
        self.api_key = api_key
        self.chain_id = chain_id
        
        # Initialize account
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        
        # CLOB endpoints
        self.clob_url = "https://clob.polymarket.com"
        self.headers = {
            "Content-Type": "application/json",
        }
        
        # Order tracking
        self.open_orders: Dict[str, Dict] = {}  # order_id -> order
        self.nonce = int(time.time() * 1000)  # Millisecond timestamp
        
        print(f"[Executor] Initialized for address: {self.address}")
    
    def place_limit_order(
        self,
        token_id: str,
        side: str,  # "BUY" or "SELL"
        price: float,
        size: float,
        time_in_force: str = "GTC",  # Good-til-cancelled
        expiration: Optional[int] = None
    ) -> Dict:
        """
        Place a limit order on Polymarket CLOB.
        
        Args:
            token_id: Token ID (e.g., "0x1234..." for UP token)
            side: "BUY" or "SELL"
            price: Limit price (0.0 to 1.0)
            size: Number of shares
            time_in_force: "GTC" (good-til-cancelled) or "IOC" (immediate-or-cancel)
            expiration: Unix timestamp when order expires (default: 1 hour)
        
        Returns:
            Order response with order_id, status, etc.
        """
        # Generate nonce
        self.nonce += 1
        
        # Default expiration: 1 hour
        if expiration is None:
            expiration = int(time.time()) + 3600
        
        # Create order
        order = {
            "tokenID": token_id,
            "price": str(price),
            "amount": str(size),
            "side": side.upper(),
            "feeRateBps": "0",  # 0% fees on CLOB
            "nonce": str(self.nonce),
            "expiration": str(expiration),
            "maker": self.address,
        }
        
        # Sign order
        order_hash = self._hash_order(order)
        signature = self._sign_order(order_hash)
        order["signature"] = signature
        
        # Submit to CLOB
        try:
            response = requests.post(
                f"{self.clob_url}/order",
                json=order,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            order_id = result.get("orderID")
            
            # Track order
            if order_id:
                self.open_orders[order_id] = {
                    "order": order,
                    "result": result,
                    "created_at": time.time()
                }
            
            print(f"[Executor] Order placed: {order_id} | {side} {size:.1f} @ {price:.3f}")
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"[Executor] Order placement failed: {e}")
            return {"error": str(e), "status": "failed"}
    
    def cancel_order(self, order_id: str) -> Dict:
        """
        Cancel an open order.
        
        Args:
            order_id: Order ID to cancel
        
        Returns:
            Cancellation response
        """
        try:
            # Sign cancellation
            cancel_msg = f"cancel:{order_id}"
            signature = self._sign_message(cancel_msg)
            
            response = requests.delete(
                f"{self.clob_url}/order/{order_id}",
                headers={
                    **self.headers,
                    "Authorization": f"Bearer {signature}"
                },
                timeout=10
            )
            response.raise_for_status()
            
            # Remove from tracking
            if order_id in self.open_orders:
                del self.open_orders[order_id]
            
            print(f"[Executor] Order cancelled: {order_id}")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"[Executor] Cancellation failed: {e}")
            return {"error": str(e), "status": "failed"}
    
    def get_order_status(self, order_id: str) -> Dict:
        """
        Get current status of an order.
        
        Args:
            order_id: Order ID
        
        Returns:
            Order status with filled_amount, avg_price, etc.
        """
        try:
            response = requests.get(
                f"{self.clob_url}/order/{order_id}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"[Executor] Status check failed: {e}")
            return {"error": str(e), "status": "unknown"}
    
    def wait_for_fill(
        self,
        order_id: str,
        timeout: float = 5.0,
        poll_interval: float = 0.1,
        min_fill_pct: float = 0.9
    ) -> Dict:
        """
        Wait for an order to fill (or partially fill).
        
        Args:
            order_id: Order ID
            timeout: Max seconds to wait
            poll_interval: Seconds between status checks
            min_fill_pct: Minimum fill percentage (0.9 = 90%)
        
        Returns:
            Fill result with status, filled_amount, avg_price
        """
        start_time = time.time()
        original_size = None
        
        while time.time() - start_time < timeout:
            status = self.get_order_status(order_id)
            
            if "error" in status:
                return status
            
            # Get fill info
            filled_amount = float(status.get("filledAmount", 0))
            total_amount = float(status.get("originalAmount", 0))
            
            if original_size is None:
                original_size = total_amount
            
            # Check if filled
            if status.get("status") == OrderStatus.FILLED:
                avg_price = float(status.get("avgFillPrice", 0))
                print(f"[Executor] Order filled: {order_id} | {filled_amount:.1f} @ {avg_price:.3f}")
                return {
                    "status": "filled",
                    "filled_amount": filled_amount,
                    "avg_price": avg_price,
                    "fill_pct": filled_amount / original_size if original_size > 0 else 0
                }
            
            # Check if partially filled enough
            if filled_amount > 0 and original_size > 0:
                fill_pct = filled_amount / original_size
                if fill_pct >= min_fill_pct:
                    avg_price = float(status.get("avgFillPrice", 0))
                    print(f"[Executor] Order partially filled: {order_id} | {fill_pct*100:.1f}%")
                    # Cancel remainder
                    self.cancel_order(order_id)
                    return {
                        "status": "partial_fill",
                        "filled_amount": filled_amount,
                        "avg_price": avg_price,
                        "fill_pct": fill_pct
                    }
            
            time.sleep(poll_interval)
        
        # Timeout - cancel order
        print(f"[Executor] Order timeout: {order_id} | Cancelling")
        self.cancel_order(order_id)
        
        return {
            "status": "timeout",
            "filled_amount": filled_amount,
            "fill_pct": filled_amount / original_size if original_size and original_size > 0 else 0
        }
    
    def get_balance(self) -> Dict:
        """
        Get USDC balance on Polygon.
        
        Returns:
            Balance info
        """
        try:
            response = requests.get(
                f"{self.clob_url}/balance/{self.address}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"[Executor] Balance check failed: {e}")
            return {"error": str(e)}
    
    def _hash_order(self, order: Dict) -> str:
        """
        Hash order for signing.
        
        Uses EIP-712 structured data hashing.
        """
        # Simplified - real implementation needs EIP-712 domain separator
        order_string = "|".join([
            order["tokenID"],
            order["price"],
            order["amount"],
            order["side"],
            order["nonce"],
            order["expiration"],
            order["maker"]
        ])
        return Web3.keccak(text=order_string).hex()
    
    def _sign_order(self, order_hash: str) -> str:
        """
        Sign order hash with private key.
        
        Returns:
            Signature in hex format
        """
        message = encode_defunct(hexstr=order_hash)
        signed_message = self.account.sign_message(message)
        return signed_message.signature.hex()
    
    def _sign_message(self, message: str) -> str:
        """
        Sign arbitrary message.
        
        Returns:
            Signature in hex format
        """
        message_encoded = encode_defunct(text=message)
        signed_message = self.account.sign_message(message_encoded)
        return signed_message.signature.hex()
    
    def cleanup(self):
        """Cancel all open orders."""
        print(f"[Executor] Cleaning up {len(self.open_orders)} open orders...")
        for order_id in list(self.open_orders.keys()):
            self.cancel_order(order_id)
