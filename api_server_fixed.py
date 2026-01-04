#!/usr/bin/env python3
if __name__ == '__main__':
    print("\n" + "="*60)
    print("Cross-Market State Fusion API Server")
    print("="*60)
    print(f"Starting Flask server on http://localhost:5000")
    print(f"Mode: {bot_state.mode}")
    print(f"Trade Size: ${bot_state.trade_size}")
    print(f"Enabled Markets: {', '.join(bot_state.enabled_markets)}")
    print("\nEndpoints:")
    print("  GET  /api/status  - Bot status and live data")
    print("  GET  /api/config  - Configuration")
    print("  POST /api/config  - Update config")
    print("  GET  /health      - Health check")
    print("\nPress Ctrl+C to stop")
    print("="*60 + "\n")
    
    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )
