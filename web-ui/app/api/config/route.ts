import { NextResponse } from 'next/server'
import { getMockConfig, setMockConfig } from '@/lib/mock-config'

// API route for getting and updating bot configuration
// In demo mode (when bot isn't running), this handles config updates locally

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    // Try to connect to the bot on localhost:5000
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 2000) // 2 second timeout

    const response = await fetch('http://localhost:5000/api/config', {
      cache: 'no-store',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      throw new Error(`Bot API returned ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.warn('Bot not reachable for config, using mock:', error instanceof Error ? error.message : 'Unknown error')
    
    // Return mock config when bot is not available
    return NextResponse.json(getMockConfig())
  }
}

export async function POST(request: Request) {
  // Parse body once at the start
  const body = await request.json()
  
  try {
    // Validate input
    if (body.mode && !['train', 'inference'].includes(body.mode)) {
      return NextResponse.json(
        { error: 'Invalid mode. Must be "train" or "inference"' },
        { status: 400 }
      )
    }
    
    if (body.trade_size !== undefined) {
      const size = parseFloat(body.trade_size)
      if (isNaN(size) || size <= 0 || size > 10000) {
        return NextResponse.json(
          { error: 'Invalid trade_size. Must be between 1 and 10000' },
          { status: 400 }
        )
      }
    }

    // Try to connect to the bot on localhost:5000
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 2000) // 2 second timeout

    const response = await fetch('http://localhost:5000/api/config', {
      method: 'POST',
      cache: 'no-store',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      throw new Error(`Bot API returned ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.warn('Bot not reachable for config update, updating mock:', error instanceof Error ? error.message : 'Unknown error')
    
    // Update mock config when bot is not available (demo mode)
    const updatedConfig = setMockConfig({
      mode: body.mode,
      trade_size: body.trade_size
    })
    
    // Return success response for demo mode
    return NextResponse.json({
      success: true,
      mode: updatedConfig.mode,
      trade_size: updatedConfig.trade_size,
      max_exposure: updatedConfig.max_exposure
    })
  }
}
