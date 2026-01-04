# Cross-Market State Fusion - Web UI

Modern, real-time web dashboard for monitoring the RL trading bot that trades Polymarket's 15-minute binary crypto markets.

## Features

### 📊 Real-Time Dashboard
- **Performance Metrics**: Live PnL, win rate, average trade, ROI
- **Equity Curve**: Interactive chart showing cumulative profit/loss over time
- **Active Markets**: Grid view of all 4 concurrent markets (BTC, ETH, SOL, XRP)
- **Trade History**: Scrollable table of recent trades with entry/exit prices
- **State Monitor**: 18-dimensional feature visualization organized by category
- **Training Stats**: Live PPO metrics (policy loss, value loss, entropy)

### ⚙️ Bot Controls
- **Mode Switching**: Toggle between Training and Inference modes
- **Custom Trade Sizing**: Quick-select buttons ($50, $100, $250, $500, $1000) or enter custom amount
- **Live Configuration**: Update bot settings without restarting
- **Max Exposure Display**: Shows total capital at risk across 4 concurrent positions

### 🎨 Design
- **Dark theme** with glassmorphism effects
- **Gradient accents** and smooth animations
- **Responsive layout** (mobile → tablet → desktop)
- **Live status indicator** with pulse animation
- **Color-coded PnL** (green = profit, red = loss)

## Architecture

```
web-ui/
├── app/
│   ├── layout.tsx           # Root layout
│   ├── page.tsx             # Main dashboard page
│   ├── globals.css          # Global styles + Tailwind
│   └── api/
│       ├── status/          # Bot status endpoint (proxies to Flask)
│       │   └── route.ts
│       └── config/          # Bot config endpoint (GET/POST)
│           └── route.ts
├── components/
│   ├── Dashboard.tsx        # Main dashboard container
│   ├── ControlPanel.tsx     # Bot controls (mode, sizing)
│   ├── MarketCard.tsx       # Individual market display
│   ├── TradeHistory.tsx     # Trade history table
│   ├── PerformanceChart.tsx # Equity curve (Recharts)
│   └── StateMonitor.tsx     # 18-dim state visualization
├── lib/
│   ├── types.ts             # TypeScript interfaces
│   ├── utils.ts             # Formatting helpers
│   └── mock-data.ts         # Mock data generator (demo mode)
└── package.json
```

## Quick Start

### 1. Install Dependencies

```bash
cd web-ui
pnpm install
```

### 2. Start Development Server

```bash
pnpm dev
```

The UI runs on **http://localhost:3000**

### 3. Connect to Bot (Optional)

The UI automatically connects to the Python bot API on **http://localhost:5000**.

If the bot isn't running, the UI falls back to **mock data** for demonstration.

## Usage

### Demo Mode (Mock Data)

Run the UI without starting the bot to see simulated trading activity:

```bash
pnpm dev
# Open http://localhost:3000
# Yellow banner indicates mock data mode
```

### Live Mode (Real Bot)

**Terminal 1** - Start the Flask API server:
```bash
cd ..
python3 api_server.py
```

**Terminal 2** - Start the trading bot:
```bash
python run.py --strategy rl --train --size 100
```

**Terminal 3** - Start the web UI:
```bash
cd web-ui
pnpm dev
```

Open **http://localhost:3000** - the UI will automatically connect to the bot.

### Using Bot Controls

1. Click **"Show Controls"** in the header
2. Select **Mode**:
   - **Training**: Agent learns from trades (updates PPO policy)
   - **Inference**: Agent uses trained model (no learning)
3. Select **Trade Size**:
   - Quick buttons: $50, $100, $250, $500, $1000
   - Custom: Enter any amount between $1-$10,000
4. Click **"Apply Changes"**
5. Bot updates within 2 seconds

## API Endpoints

The UI communicates with the bot via REST API:

### GET `/api/status`
Returns current bot state:
```json
{
  "mode": "train",
  "trade_size": 500,
  "markets": [...],
  "performance": {
    "total_pnl": 1234.56,
    "num_trades": 42,
    "win_rate": 0.23,
    "avg_pnl": 29.39,
    "max_exposure": 2000
  },
  "recent_trades": [...],
  "pnl_history": [...],
  "training_stats": {
    "update": 15,
    "policy_loss": 0.0234,
    "value_loss": 8.45,
    "entropy": 1.05
  }
}
```

### GET `/api/config`
Returns bot configuration:
```json
{
  "mode": "train",
  "trade_size": 500,
  "max_exposure": 2000
}
```

### POST `/api/config`
Update bot configuration:
```json
{
  "mode": "inference",
  "trade_size": 250
}
```

## Technology Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **Data Fetching**: Polling (2s interval)
- **State Management**: React hooks

## Data Flow

```
┌─────────────────┐
│  Python Bot     │  (run.py)
│  Paper Trading  │
└────────┬────────┘
         │
         │ WebSocket + REST
         │
┌────────▼────────┐
│  Flask API      │  (api_server.py)
│  Port 5000      │  Serves bot status via REST
└────────┬────────┘
         │
         │ HTTP polling (2s)
         │
┌────────▼────────┐
│  Next.js API    │  (app/api/*/route.ts)
│  Routes          │  Proxy + fallback to mock data
└────────┬────────┘
         │
         │ Props
         │
┌────────▼────────┐
│  React UI       │  (components/*.tsx)
│  Port 3000      │  Real-time dashboard
└─────────────────┘
```

## State Features (18-dimensional)

| Category | Features (count) |
|----------|------------------|
| **Momentum** | returns_1m, returns_5m, returns_10m (3) |
| **Order Flow** | ob_imbalance_l1, ob_imbalance_l5, trade_flow, cvd_accel (4) |
| **Microstructure** | spread_pct, trade_intensity, large_trade_flag (3) |
| **Volatility** | vol_5m, vol_expansion (2) |
| **Position** | has_position, position_side, position_pnl, time_remaining (4) |
| **Regime** | vol_regime, trend_regime (2) |

## Mock Data Mode

When the bot isn't running, the UI automatically falls back to mock data:

- **Simulated trades**: Random trades every ~10 seconds
- **Live market updates**: Probabilities walk randomly
- **Realistic state**: 18-dim features with correlated values
- **Training progression**: Incrementing updates with decaying losses

Perfect for:
- **Demos**: Show the UI without running the bot
- **Development**: Test UI changes without backend
- **Screenshots**: Generate realistic-looking dashboards

## Customization

### Change Update Interval

Edit `app/page.tsx`:
```typescript
const interval = setInterval(fetchStatus, 2000) // Change 2000ms to desired interval
```

### Add New Trade Sizes

Edit `components/ControlPanel.tsx`:
```typescript
const TRADE_SIZES = [50, 100, 250, 500, 1000, 2500] // Add your sizes
```

### Change Color Scheme

Edit `tailwind.config.js`:
```javascript
theme: {
  extend: {
    colors: {
      primary: { ... }, // Customize colors
    }
  }
}
```

## Deployment

### Production Build

```bash
pnpm build
pnpm start
```

### Vercel (Recommended)

```bash
vercel
```

Note: You'll need to configure the API proxy to point to your production bot URL.

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## Troubleshooting

### UI shows "Connection Error"

- ✅ Check if Flask API is running on port 5000
- ✅ Check if `api_server.py` started successfully
- ✅ Look for errors in browser console

### UI shows "Mock Data" banner

- This is expected when the bot isn't running
- Start `api_server.py` to connect to real data

### Config updates don't work

- ✅ Ensure Flask API `/api/config` endpoint is implemented
- ✅ Check browser console for errors
- ✅ Verify bot accepts config changes

### Charts not rendering

- ✅ Ensure `pnl_history` has data
- ✅ Check browser console for Recharts errors
- ✅ Verify timestamps are valid ISO strings

## Contributing

To add new features:

1. **Add type definitions** in `lib/types.ts`
2. **Create component** in `components/`
3. **Import in Dashboard** (`components/Dashboard.tsx`)
4. **Update API route** if needed (`app/api/*/route.ts`)
5. **Test with mock data** (edit `lib/mock-data.ts`)

## License

MIT License - see [../LICENSE](../LICENSE) for details.

## Links

- **Main Project**: [README.md](../README.md)
- **Training Journal**: [TRAINING_JOURNAL.md](../TRAINING_JOURNAL.md)
- **LACUNA Writeup**: [humanplane.com/lacuna](https://humanplane.com/lacuna)
- **GitHub**: [github.com/humanplane/cross-market-state-fusion](https://github.com/humanplane/cross-market-state-fusion)
