// Shared mock configuration state
// This allows both the config API and status API to use the same config

export interface MockConfig {
  mode: 'train' | 'inference'
  trade_size: number
  max_exposure: number
  enabled_markets: string[]
}

// Singleton config store
let mockConfig: MockConfig = {
  mode: 'train',
  trade_size: 500,
  max_exposure: 2000,
  enabled_markets: ['BTC', 'ETH', 'SOL', 'XRP']
}

export function getMockConfig(): MockConfig {
  return { ...mockConfig }
}

export function setMockConfig(updates: Partial<MockConfig>): MockConfig {
  if (updates.mode) {
    mockConfig.mode = updates.mode
  }
  if (updates.trade_size !== undefined) {
    mockConfig.trade_size = updates.trade_size
    // Update max exposure based on enabled markets
    mockConfig.max_exposure = updates.trade_size * mockConfig.enabled_markets.length
  }
  if (updates.enabled_markets !== undefined) {
    // Ensure at least one market is enabled
    if (updates.enabled_markets.length > 0) {
      mockConfig.enabled_markets = updates.enabled_markets
      // Update max exposure based on trade size and enabled markets
      mockConfig.max_exposure = mockConfig.trade_size * updates.enabled_markets.length
    }
  }
  if (updates.max_exposure !== undefined) {
    mockConfig.max_exposure = updates.max_exposure
  }
  return { ...mockConfig }
}
