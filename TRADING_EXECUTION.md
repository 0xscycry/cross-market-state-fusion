# Trading Execution: Paper vs Live

This document explains how the bot currently executes trades and what would change when moving to live trading.

---

## Current Status: **PAPER TRADING ONLY**

The bot does **NOT place real orders**. All trading is simulated.

### What "Paper Trading" Means

**From `run.py`**:
```python
def execute_action(self, cid: str, action: Action, state: MarketState):
    """Execute paper trade with flexible sizing."""
    if action == Action.HOLD:
        return

    price = state.prob  # Current mid-price from orderbook
    trade_amount = self.trade_size * action.size_multiplier

    # Open new position
    if pos.size == 0:
        if action.is_buy:
            pos.side = "UP"
            pos.size = trade_amount
            pos.entry_price = price  # Assume instant fill at mid-price
            pos.entry_time = datetime.now(timezone.utc)
            print(f"    OPEN {pos.asset} UP ${trade_amount:.0f} @ {price:.3f}")
```

**Key assumptions**:
- ✅ **Instant fills** - Order executes immediately
- ✅ **Mid-price execution** - Trade at exact orderbook mid-price
- ✅ **No slippage** - Price doesn't move against you
- ✅ **No latency** - Zero delay from decision to fill
- ✅ **No market impact** - Your order doesn't move the market
- ✅ **No fees** - Zero transaction costs (Polymarket CLOB charges 0%)
- ✅ **Unlimited liquidity** - Can trade any size

**Reality**: These assumptions are optimistic. Real trading faces friction.

---

## Order Types: Neither (Paper Trading)

**The bot currently uses:** Simulated instant execution at mid-price

**Answer**: The bot doesn't use limit orders or market orders because it doesn't place real orders at all. It's purely paper trading.

### What the Code Actually Does

```python
# 1. Get current mid-price from orderbook WebSocket
price = state.prob  # This is (best_bid + best_ask) / 2

# 2. Immediately "fill" the trade at that price
pos.entry_price = price
pos.entry_time = datetime.now(timezone.utc)

# 3. Track position in memory
self.positions[cid] = pos

# 4. Calculate unrealized PnL every tick
if pos.side == "UP":
    state.position_pnl = (state.prob - pos.entry_price) * shares

# 5. "Close" position when market expires or agent decides to exit
pnl = (exit_price - entry_price) * shares
self.total_pnl += pnl  # Track cumulative paper PnL
```

**No API calls. No order placement. Pure simulation.**

---

## Data Sources (What IS Real)

While trading is simulated, the **market data is 100% real**:

### 1. Binance Futures WebSocket
```python
self.price_streamer = BinanceStreamer(["BTC", "ETH", "SOL", "XRP"])
self.futures_streamer = FuturesStreamer(["BTC", "ETH", "SOL", "XRP"])
```

**Live data**:
- Spot prices (1-second updates)
- Returns (1m, 5m, 10m)
- Order flow (trade flow imbalance, CVD)
- Volatility (realized vol, vol expansion)
- Microstructure (trade intensity, large trades)

### 2. Polymarket CLOB WebSocket
```python
self.orderbook_streamer = OrderbookStreamer()
self.orderbook_streamer.subscribe(m.condition_id, m.token_up, m.token_down)
```

**Live data**:
- Best bid/ask prices
- Orderbook depth (L1, L5)
- Bid/ask imbalance
- Spread width
- Real-time probability updates

### 3. Polymarket REST API
```python
markets = get_15m_markets(assets=["BTC", "ETH", "SOL", "XRP"])
```

**Live data**:
- Active 15-minute binary markets
- Token IDs (UP/DOWN)
- Market expiration times
- Current prices

**Bottom line**: The bot observes real markets and makes real decisions. It just doesn't execute real orders.

---

## Why Paper Trading?

### 1. **Development & Testing**
Test strategies without risking capital:
- Does the RL agent learn?
- What's the PnL distribution?
- How does it perform across market regimes?

### 2. **No API Keys Required**
Polymarket CLOB requires wallet signing for order placement:
- Need private key
- Must approve USDC spending
- Gas costs on Polygon
- Regulatory considerations

### 3. **Safety**
Bugs in paper trading = lost opportunity  
Bugs in live trading = lost money

### 4. **Training Data Collection**
```python
if self.logger:
    self.logger.log_trade(
        asset=pos.asset,
        side=pos.side,
        entry_price=pos.entry_price,
        exit_price=price,
        pnl=pnl,
        # ... more metrics
    )
```

Generates training logs (`logs/updates_*.csv`) for analysis without financial risk.

---

## Path to Live Trading

### What Would Change?

#### 1. **Order Execution Layer**

Add Polymarket CLOB API integration:

```python
import requests
from eth_account import Account

class PolymarketExecutor:
    def __init__(self, private_key: str, api_key: str):
        self.account = Account.from_key(private_key)
        self.api_key = api_key
        self.clob_url = "https://clob.polymarket.com"
    
    def place_limit_order(
        self,
        token_id: str,
        side: str,  # "BUY" or "SELL"
        price: float,
        size: float,
        time_in_force: str = "GTC"  # Good-til-cancelled
    ) -> dict:
        """Place a limit order on Polymarket CLOB."""
        # 1. Create order payload
        order = {
            "tokenID": token_id,
            "price": str(price),
            "size": str(size),
            "side": side,
            "feeRateBps": "0",  # 0 fees on CLOB
            "nonce": self._get_nonce(),
            "expiration": int(time.time()) + 3600,  # 1 hour
        }
        
        # 2. Sign order with private key
        order_hash = self._hash_order(order)
        signature = self.account.sign_message(order_hash)
        order["signature"] = signature.signature.hex()
        
        # 3. Submit to CLOB
        response = requests.post(
            f"{self.clob_url}/order",
            json=order,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        
        return response.json()
    
    def cancel_order(self, order_id: str) -> dict:
        """Cancel an open order."""
        response = requests.delete(
            f"{self.clob_url}/order/{order_id}",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return response.json()
```

#### 2. **Order Type: Limit Orders (Recommended)**

**Why limit orders?**
- ✅ **Control price** - Specify exact price you're willing to pay
- ✅ **Avoid slippage** - Won't pay more than limit price
- ✅ **Add liquidity** - Get filled by market takers (0% fee on CLOB)
- ✅ **Better for large sizes** - $500+ orders need careful execution

**Strategy**:
```python
def execute_action_live(self, cid: str, action: Action, state: MarketState):
    """Execute live trade with limit orders."""
    if action == Action.HOLD:
        return
    
    # Get current orderbook
    ob = self.orderbook_streamer.get_orderbook(cid, "UP")
    
    # Place limit order at favorable price
    if action.is_buy:
        # Bid between best bid and mid-price
        limit_price = ob.best_bid + (ob.spread * 0.3)  # 30% into spread
        order = self.executor.place_limit_order(
            token_id=market.token_up,
            side="BUY",
            price=limit_price,
            size=self.trade_size / limit_price,  # Convert $ to shares
            time_in_force="IOC"  # Immediate-or-cancel
        )
        
        # Handle partial fills
        filled_size = order.get("filled_size", 0)
        if filled_size < order["size"] * 0.9:  # Less than 90% filled
            # Chase with market order or cancel
            pass
```

**Alternative: Market Orders**
- ✅ **Guaranteed fill** - Executes immediately
- ❌ **Slippage risk** - Pays worst available price
- ❌ **Market impact** - Large orders walk the book

Use market orders only for:
- Small sizes (<$100)
- High urgency (near expiry)
- Thick orderbooks (tight spreads)

#### 3. **Fill Confirmation**

Current (paper):
```python
pos.entry_price = price  # Instant
pos.entry_time = datetime.now()
```

Live trading:
```python
# 1. Place order
order = executor.place_limit_order(...)
order_id = order["orderID"]

# 2. Poll for fill
while not filled:
    status = executor.get_order_status(order_id)
    if status["status"] == "filled":
        pos.entry_price = float(status["avg_fill_price"])
        pos.entry_time = datetime.fromisoformat(status["fill_time"])
        break
    elif time.time() - start_time > 5:  # 5 second timeout
        executor.cancel_order(order_id)
        break
    await asyncio.sleep(0.1)  # 100ms poll interval
```

#### 4. **Slippage Modeling**

Expected degradation from paper to live:

**Slippage formula**:
```python
expected_slippage = spread / 2 + market_impact

# Spread cost: ~0.5-2% for Polymarket 15-min markets
spread_cost = (best_ask - best_bid) / 2

# Market impact: Size-dependent
market_impact = (order_size / orderbook_depth) * volatility

# Total cost per trade
total_cost = spread_cost + market_impact + latency_cost
```

**From README**:
> Paper trading assumes instant fills at mid-price. Real trading faces latency, slippage, and market impact. **Expect 20-50% performance degradation.**

**Example**: Paper PnL = $50K → Live PnL ≈ $25-40K

#### 5. **Latency Compensation**

**Current (paper)**: Zero latency  
**Live trading**: 50-200ms round-trip

```python
# Latency breakdown
Decision → Order → CLOB → Fill → Confirmation
  ~0ms     50ms    50ms    50ms     50ms
            \______ 200ms total ______/
```

**Impact**: Orderbook may move between decision and fill

**Mitigation**:
```python
# Predict price movement during latency window
expected_price_move = state.returns_1m * (latency_ms / 60000)

# Adjust limit price
adjusted_limit = limit_price + expected_price_move

# Only trade if edge remains after adjustment
if expected_pnl > slippage + latency_cost:
    place_order(adjusted_limit)
```

#### 6. **Position Tracking**

Current:
```python
self.positions[cid] = Position(
    side="UP",
    size=500,
    entry_price=0.52,
    entry_time=datetime.now()
)
```

Live:
```python
self.positions[cid] = Position(
    side="UP",
    size=485,  # Actual filled size (partial fill)
    entry_price=0.523,  # Average fill price (worse than limit)
    entry_time=datetime.now(),
    order_id="0x1a2b3c...",  # Track for cancellation
    fees_paid=0.0,  # Polymarket CLOB = 0% fees
    slippage=0.003  # 0.523 vs 0.52 limit = 0.3% slippage
)
```

#### 7. **Risk Management**

**Current (paper)**: None needed  
**Live trading**: Critical

```python
class RiskManager:
    def __init__(self, max_daily_loss: float = -1000):
        self.max_daily_loss = max_daily_loss
        self.daily_pnl = 0
        self.max_position_size = 500
        self.max_total_exposure = 2000
    
    def can_trade(self, size: float) -> bool:
        """Check if trade is within risk limits."""
        # Daily loss limit
        if self.daily_pnl <= self.max_daily_loss:
            return False
        
        # Position size limit
        if size > self.max_position_size:
            return False
        
        # Total exposure limit
        current_exposure = sum(p.size for p in positions.values())
        if current_exposure + size > self.max_total_exposure:
            return False
        
        return True
```

---

## Implementation Checklist

### Phase 1: Infrastructure
- [ ] Set up Polymarket CLOB account
- [ ] Generate API keys
- [ ] Fund wallet with USDC on Polygon
- [ ] Test order placement on testnet/small size
- [ ] Implement order signing with private key
- [ ] Build order tracking system

### Phase 2: Execution Layer
- [ ] Replace `execute_action()` with live order placement
- [ ] Add fill confirmation logic
- [ ] Handle partial fills
- [ ] Implement order cancellation
- [ ] Add slippage tracking
- [ ] Log actual vs expected prices

### Phase 3: Risk Controls
- [ ] Add position size limits
- [ ] Add total exposure limits
- [ ] Add daily loss limits
- [ ] Implement emergency stop-loss
- [ ] Add latency monitoring
- [ ] Alert system for errors

### Phase 4: Validation
- [ ] Run paper trading for 2+ weeks
- [ ] Analyze slippage distribution
- [ ] Model expected live performance
- [ ] Start with $10-50 trades
- [ ] Gradually scale up size
- [ ] Compare live vs paper results

### Phase 5: Monitoring
- [ ] Real-time PnL dashboard
- [ ] Order status monitoring
- [ ] Fill rate tracking
- [ ] Slippage analysis
- [ ] Latency metrics
- [ ] Daily performance reports

---

## Code Changes Required

### Minimal Live Trading Implementation

**1. Add executor class** (`helpers/polymarket_executor.py`):
```python
from eth_account import Account
import requests

class PolymarketExecutor:
    # ... (implementation from above)
    pass
```

**2. Modify `run.py`**:
```python
class TradingEngine:
    def __init__(self, strategy: Strategy, trade_size: float, live: bool = False):
        self.strategy = strategy
        self.trade_size = trade_size
        self.live = live  # NEW: Enable live trading
        
        if self.live:
            self.executor = PolymarketExecutor(
                private_key=os.getenv("POLYMARKET_PRIVATE_KEY"),
                api_key=os.getenv("POLYMARKET_API_KEY")
            )
    
    def execute_action(self, cid: str, action: Action, state: MarketState):
        """Execute trade (paper or live)."""
        if action == Action.HOLD:
            return
        
        if self.live:
            self._execute_live(cid, action, state)
        else:
            self._execute_paper(cid, action, state)
    
    def _execute_paper(self, cid: str, action: Action, state: MarketState):
        """Current paper trading logic."""
        # ... (existing code)
        pass
    
    def _execute_live(self, cid: str, action: Action, state: MarketState):
        """NEW: Real order execution."""
        market = self.markets[cid]
        ob = self.orderbook_streamer.get_orderbook(cid, "UP")
        
        if action.is_buy:
            # Place limit order
            limit_price = ob.best_bid + (ob.spread * 0.3)
            order = self.executor.place_limit_order(
                token_id=market.token_up,
                side="BUY",
                price=limit_price,
                size=self.trade_size / limit_price
            )
            
            # Wait for fill
            # ... (fill confirmation logic)
```

**3. Add CLI flag**:
```python
parser.add_argument("--live", action="store_true", help="Enable live trading (default: paper)")
```

**4. Usage**:
```bash
# Paper trading (current)
python run.py --strategy rl --train --size 100

# Live trading (future)
python run.py --strategy rl --load rl_model --size 50 --live
```

---

## Performance Expectations

### Paper Trading Results
- Phase 5 (LACUNA): ~$50K PnL, 2,500% ROI
- Phase 4: $3,392 PnL, 170% ROI
- Phase 3: $23 PnL, 12% ROI

### Expected Live Trading Results

**Slippage impact**: 20-50% degradation

| Metric | Paper (Phase 5) | Live (Conservative) | Live (Optimistic) |
|--------|-----------------|---------------------|-------------------|
| PnL | $50,000 | $25,000 | $40,000 |
| ROI | 2,500% | 1,250% | 2,000% |
| Win Rate | 23% | 20-22% | 22-23% |
| Avg Trade | Variable | -10% to -20% | -5% to -10% |

**Why degradation?**
1. **Spread cost**: Pay bid-ask spread on every trade
2. **Partial fills**: May not get full size at limit price
3. **Latency**: Prices move between decision and execution
4. **Market impact**: Large orders move prices against you
5. **Missed opportunities**: Some signals expire before fill

---

## Regulatory & Compliance

### Legal Considerations

**Polymarket availability**:
- ❌ Blocked in the US (geofencing)
- ✅ Available in most other jurisdictions
- ⚠️ Check local regulations

**Automation**:
- ✅ Polymarket allows bots (unlike some exchanges)
- ✅ No rate limits on CLOB API
- ⚠️ Must comply with ToS

**Tax implications**:
- Each trade is a taxable event
- Track cost basis, gains/losses
- Consult tax professional

---

## Conclusion

**Current status**: Pure paper trading (simulated execution)  
**Order types**: Neither - assumes instant mid-price fills  
**Data**: 100% real (Binance + Polymarket live feeds)  
**Path to live**: Requires order execution layer + risk management

**Recommendation**: Continue paper trading until:
1. ✅ Strategy is profitable over 2+ weeks
2. ✅ Win rate stable >20%
3. ✅ Entropy remains healthy (>1.0)
4. ✅ Slippage model built and validated
5. ✅ Risk controls implemented and tested

Then start live with:
- Small size ($10-50/trade)
- Limited daily loss ($100-500)
- 1-2 markets only (BTC, ETH)
- Close monitoring

**Live trading adds significant complexity and risk. Paper trading is safer for development and learning.**

---

## See Also

- [README.md](README.md) - Project overview
- [TRAINING_JOURNAL.md](TRAINING_JOURNAL.md) - Training evolution
- [MODEL_PERSISTENCE.md](MODEL_PERSISTENCE.md) - How model saving works
- [run.py](run.py) - Main trading loop
- [helpers/polymarket_api.py](helpers/polymarket_api.py) - API integration

---

*Last updated: January 4, 2025*
