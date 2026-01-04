import { NextResponse } from 'next/server'

// This endpoint proxies requests to the Python trading bot
// Falls back to mock data if bot is not running

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    // Try to connect to the bot on localhost:5000
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 2000) // 2 second timeout

    const response = await fetch('http://localhost:5000/api/status', {
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
    console.warn('Bot not reachable, using mock data:', error instanceof Error ? error.message : 'Unknown error')
    
    // Return mock data when bot is not available
    const { getMockStatus } = await import('@/lib/mock-data')
    return NextResponse.json(getMockStatus())
  }
}
