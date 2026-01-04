// Shared mock configuration state
// This allows both the config API and status API to use the same config

export interface MockConfig {
  mode: 'train' | 'inference'
  trade_size: number
  max_exposure: number
}

// Singleton config store
let mockConfig: MockConfig = {
  mode: 'train',
  trade_size: 500,
  max_exposure: 2000
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
    mockConfig.max_exposure = updates.trade_size * 4
  }
  if (updates.max_exposure !== undefined) {
    mockConfig.max_exposure = updates.max_exposure
  }
  return { ...mockConfig }
}
