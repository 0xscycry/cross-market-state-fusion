import clsx, { ClassValue } from 'clsx'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

export function formatCurrency(value: number): string {
  const sign = value >= 0 ? '+' : ''
  return `${sign}$${Math.abs(value).toFixed(2)}`
}

export function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`
}

export function formatTimestamp(timestamp: string | number, format: 'full' | 'short' = 'full'): string {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : new Date(timestamp)
  
  if (format === 'short') {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }
  
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function formatTimeRemaining(endDate: string): string {
  const now = new Date()
  const end = new Date(endDate)
  const diffMs = end.getTime() - now.getTime()
  
  if (diffMs < 0) {
    return 'Expired'
  }
  
  const diffMins = Math.floor(diffMs / 60000)
  const diffSecs = Math.floor((diffMs % 60000) / 1000)
  
  if (diffMins > 0) {
    return `${diffMins}m ${diffSecs}s`
  }
  
  return `${diffSecs}s`
}
