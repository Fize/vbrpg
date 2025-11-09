/**
 * Analytics tracking service
 * 
 * Tracks user events and game metrics for analysis
 */

interface AnalyticsEvent {
  event: string
  properties?: Record<string, any>
  timestamp: string
}

interface GameEvent {
  room_code: string
  game_id: string
  event_type: 'start' | 'complete' | 'abandon' | 'error'
  duration_seconds?: number
  player_count?: number
  error_type?: string
}

class AnalyticsService {
  private enabled: boolean
  private events: AnalyticsEvent[] = []
  private batchSize: number = 10
  private flushInterval: number = 30000 // 30 seconds
  private flushTimer: number | null = null

  constructor() {
    // @ts-ignore - Vite env variable
    this.enabled = import.meta.env?.VITE_ANALYTICS_ENABLED === 'true'
    
    if (this.enabled) {
      this.startFlushTimer()
    }
  }

  /**
   * Track a generic event
   */
  track(event: string, properties?: Record<string, any>): void {
    if (!this.enabled) return

    const analyticsEvent: AnalyticsEvent = {
      event,
      properties,
      timestamp: new Date().toISOString()
    }

    this.events.push(analyticsEvent)

    // Flush if batch size reached
    if (this.events.length >= this.batchSize) {
      this.flush()
    }
  }

  /**
   * Track game start
   */
  trackGameStart(roomCode: string, gameId: string, playerCount: number): void {
    this.track('game_started', {
      room_code: roomCode,
      game_id: gameId,
      player_count: playerCount
    })
  }

  /**
   * Track game completion
   */
  trackGameComplete(
    roomCode: string,
    gameId: string,
    durationSeconds: number,
    playerCount: number,
    winnerId?: string
  ): void {
    this.track('game_completed', {
      room_code: roomCode,
      game_id: gameId,
      duration_seconds: durationSeconds,
      player_count: playerCount,
      winner_id: winnerId
    })
  }

  /**
   * Track game abandonment
   */
  trackGameAbandon(roomCode: string, gameId: string, reason: string): void {
    this.track('game_abandoned', {
      room_code: roomCode,
      game_id: gameId,
      reason
    })
  }

  /**
   * Track error
   */
  trackError(
    errorType: string,
    message: string,
    context?: Record<string, any>
  ): void {
    this.track('error_occurred', {
      error_type: errorType,
      message,
      ...context
    })
  }

  /**
   * Track user action
   */
  trackAction(
    actionType: string,
    roomCode?: string,
    details?: Record<string, any>
  ): void {
    this.track('user_action', {
      action_type: actionType,
      room_code: roomCode,
      ...details
    })
  }

  /**
   * Track page view
   */
  trackPageView(path: string, title?: string): void {
    this.track('page_view', {
      path,
      title: title || document.title,
      referrer: document.referrer
    })
  }

  /**
   * Track room creation
   */
  trackRoomCreate(roomCode: string, settings: Record<string, any>): void {
    this.track('room_created', {
      room_code: roomCode,
      ...settings
    })
  }

  /**
   * Track room join
   */
  trackRoomJoin(roomCode: string): void {
    this.track('room_joined', {
      room_code: roomCode
    })
  }

  /**
   * Track player registration
   */
  trackPlayerRegister(isUpgrade: boolean): void {
    this.track('player_registered', {
      is_upgrade: isUpgrade
    })
  }

  /**
   * Track guest account creation
   */
  trackGuestCreate(): void {
    this.track('guest_created', {})
  }

  /**
   * Track WebSocket events
   */
  trackWebSocket(event: 'connect' | 'disconnect' | 'reconnect' | 'error'): void {
    this.track('websocket_event', {
      event
    })
  }

  /**
   * Track turn timeout
   */
  trackTurnTimeout(roomCode: string, playerId: string): void {
    this.track('turn_timeout', {
      room_code: roomCode,
      player_id: playerId
    })
  }

  /**
   * Track AI action
   */
  trackAIAction(roomCode: string, actionType: string, durationMs: number): void {
    this.track('ai_action', {
      room_code: roomCode,
      action_type: actionType,
      duration_ms: durationMs
    })
  }

  /**
   * Flush events to server
   */
  private async flush(): Promise<void> {
    if (this.events.length === 0) return

    const eventsToSend = [...this.events]
    this.events = []

    try {
      // Send to analytics endpoint
      await fetch('/api/analytics/events', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          events: eventsToSend,
          session_id: this.getSessionId()
        })
      })
    } catch (error) {
      console.error('Failed to send analytics events:', error)
      // Don't retry - events are lost
    }
  }

  /**
   * Start auto-flush timer
   */
  private startFlushTimer(): void {
    this.flushTimer = window.setInterval(() => {
      this.flush()
    }, this.flushInterval)
  }

  /**
   * Stop auto-flush timer
   */
  private stopFlushTimer(): void {
    if (this.flushTimer !== null) {
      clearInterval(this.flushTimer)
      this.flushTimer = null
    }
  }

  /**
   * Get or create session ID
   */
  private getSessionId(): string {
    let sessionId = sessionStorage.getItem('analytics_session_id')
    
    if (!sessionId) {
      sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      sessionStorage.setItem('analytics_session_id', sessionId)
    }
    
    return sessionId
  }

  /**
   * Enable analytics
   */
  enable(): void {
    this.enabled = true
    this.startFlushTimer()
  }

  /**
   * Disable analytics
   */
  disable(): void {
    this.enabled = false
    this.stopFlushTimer()
    this.events = []
  }

  /**
   * Cleanup on app shutdown
   */
  async cleanup(): Promise<void> {
    this.stopFlushTimer()
    await this.flush()
  }
}

// Create singleton instance
const analytics = new AnalyticsService()

// Flush on page unload
window.addEventListener('beforeunload', () => {
  analytics.cleanup()
})

export default analytics
