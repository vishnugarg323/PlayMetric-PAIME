import { io, Socket } from 'socket.io-client'

// Use runtime config if available, fallback to import.meta.env
const SOCKET_URL = (window as any).ENV?.VITE_SOCKET_URL || import.meta.env.VITE_SOCKET_URL || ''

class WebSocketService {
  private socket: Socket | null = null
  private listeners: Map<string, Set<(data: any) => void>> = new Map()

  connect() {
    if (this.socket?.connected) return

    // Only connect if SOCKET_URL is defined
    if (!SOCKET_URL) {
      console.warn('VITE_SOCKET_URL not configured, WebSocket disabled')
      return
    }

    this.socket = io(SOCKET_URL, {
      transports: ['websocket', 'polling'],
      reconnectionDelay: 1000,
      reconnection: true,
      reconnectionAttempts: 10,
      // Use the path that matches the server socketio_path
      path: '/socket.io',
    })

    this.socket.on('connect', () => {
      console.log('WebSocket connected')
    })

    this.socket.on('disconnect', () => {
      console.log('WebSocket disconnected')
    })

    this.socket.on('error', (error) => {
      console.error('WebSocket error:', error)
    })

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error.message)
    })

    // Forward all events to listeners
    this.socket.onAny((event, data) => {
      const eventListeners = this.listeners.get(event)
      if (eventListeners) {
        eventListeners.forEach(callback => callback(data))
      }
    })
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
  }

  subscribe(event: string, callback: (data: any) => void) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event)!.add(callback)

    // Return unsubscribe function
    return () => {
      const eventListeners = this.listeners.get(event)
      if (eventListeners) {
        eventListeners.delete(callback)
      }
    }
  }

  emit(event: string, data?: any) {
    if (this.socket?.connected) {
      this.socket.emit(event, data)
    }
  }

  // Convenience methods for common events
  subscribeToSession(sessionId: string, callback: (data: any) => void) {
    return this.subscribe(`session:${sessionId}`, callback)
  }

  subscribeToScreenshots(sessionId: string, callback: (data: any) => void) {
    return this.subscribe(`screenshot:${sessionId}`, callback)
  }

  subscribeToMetrics(sessionId: string, callback: (data: any) => void) {
    return this.subscribe(`metrics:${sessionId}`, callback)
  }

  subscribeToBugs(callback: (data: any) => void) {
    return this.subscribe('bug:detected', callback)
  }

  subscribeToCrashes(callback: (data: any) => void) {
    return this.subscribe('crash:detected', callback)
  }
}

export const wsService = new WebSocketService()
