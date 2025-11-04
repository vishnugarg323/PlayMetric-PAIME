import { clsx, type ClassValue } from 'clsx'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

export function formatBytes(bytes: number, decimals = 2) {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
}

export function formatDuration(seconds: number) {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  
  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`
  } else {
    return `${secs}s`
  }
}

export function formatRelativeTime(date: string) {
  const now = new Date()
  const then = new Date(date)
  const diffMs = now.getTime() - then.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)
  
  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return then.toLocaleDateString()
}

export function getStatusColor(status: string) {
  const colors: Record<string, string> = {
    running: 'bg-green-500',
    queued: 'bg-yellow-500',
    completed: 'bg-blue-500',
    failed: 'bg-red-500',
    stopped: 'bg-gray-500',
    active: 'bg-green-500',
    inactive: 'bg-gray-500',
    archived: 'bg-slate-500',
    open: 'bg-yellow-500',
    in_progress: 'bg-blue-500',
    resolved: 'bg-green-500',
    wont_fix: 'bg-gray-500',
    duplicate: 'bg-slate-500',
  }
  return colors[status] || 'bg-gray-500'
}

export function getSeverityColor(severity: string) {
  const colors: Record<string, string> = {
    critical: 'text-red-600 bg-red-100 border-red-200',
    high: 'text-orange-600 bg-orange-100 border-orange-200',
    medium: 'text-yellow-600 bg-yellow-100 border-yellow-200',
    low: 'text-blue-600 bg-blue-100 border-blue-200',
  }
  return colors[severity] || 'text-gray-600 bg-gray-100 border-gray-200'
}

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: number | null = null
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait) as unknown as number
  }
}
