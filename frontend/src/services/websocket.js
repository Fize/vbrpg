import { io } from 'socket.io-client'

const WS_URL = import.meta.env.VITE_WS_URL || 'http://localhost:8000'
const GRACE_PERIOD_MS = 5 * 60 * 1000 // 5 minutes
const SESSION_ROOM_KEY = 'last_room_code'
const SESSION_DISCONNECT_KEY = 'disconnect_timestamp'

class WebSocketService {
  constructor() {
    this.socket = null
    this.connected = false
    this.eventHandlers = new Map()
    this.currentRoomCode = null
    this.currentPlayerId = null
    this.reconnectionAttempts = 0
    this.maxReconnectionAttempts = 60 // 5 minutes with 5s delay
    
    // Restore room code from session if available
    this.restoreSessionState()
  }
  
  /**
   * Restore room code and disconnect timestamp from sessionStorage
   */
  restoreSessionState() {
    try {
      const savedRoomCode = sessionStorage.getItem(SESSION_ROOM_KEY)
      const disconnectTimestamp = sessionStorage.getItem(SESSION_DISCONNECT_KEY)
      
      if (savedRoomCode && disconnectTimestamp) {
        const elapsed = Date.now() - parseInt(disconnectTimestamp)
        
        if (elapsed < GRACE_PERIOD_MS) {
          this.currentRoomCode = savedRoomCode
          console.log(`Restored room code ${savedRoomCode} from session (${Math.floor(elapsed / 1000)}s ago)`)
        } else {
          // Grace period expired, clear session
          console.log('Grace period expired, clearing session')
          this.clearSessionState()
        }
      }
    } catch (error) {
      console.error('Failed to restore session state:', error)
    }
  }
  
  /**
   * Save room code to sessionStorage
   */
  saveSessionState(roomCode) {
    try {
      if (roomCode) {
        sessionStorage.setItem(SESSION_ROOM_KEY, roomCode)
      }
    } catch (error) {
      console.error('Failed to save session state:', error)
    }
  }
  
  /**
   * Clear room code from sessionStorage
   */
  clearSessionState() {
    try {
      sessionStorage.removeItem(SESSION_ROOM_KEY)
      sessionStorage.removeItem(SESSION_DISCONNECT_KEY)
    } catch (error) {
      console.error('Failed to clear session state:', error)
    }
  }
  
  /**
   * Record disconnect timestamp for grace period tracking
   */
  recordDisconnect() {
    try {
      sessionStorage.setItem(SESSION_DISCONNECT_KEY, Date.now().toString())
    } catch (error) {
      console.error('Failed to record disconnect:', error)
    }
  }

  connect(playerId = null) {
    if (this.socket && this.connected) {
      return this.socket
    }

    // Store player ID for reconnection
    if (playerId) {
      this.currentPlayerId = playerId
    }

    const auth = this.currentPlayerId ? { player_id: this.currentPlayerId } : undefined

    this.socket = io(WS_URL, {
      withCredentials: true,
      reconnection: true,
      reconnectionAttempts: this.maxReconnectionAttempts,
      reconnectionDelay: 5000,
      auth: auth
    })

    this.socket.on('connect', async () => {
      console.log('WebSocket connected')
      this.connected = true
      this.reconnectionAttempts = 0
      
      // If we were in a room before disconnect, try to rejoin and sync state
      if (this.currentRoomCode) {
        console.log('Attempting to rejoin room:', this.currentRoomCode)
        
        // Clear disconnect timestamp on successful reconnection
        sessionStorage.removeItem(SESSION_DISCONNECT_KEY)
        
        // Emit reconnection event to trigger state sync
        if (this.eventHandlers.has('_internal_reconnect')) {
          const handler = this.eventHandlers.get('_internal_reconnect')
          await handler({ roomCode: this.currentRoomCode })
        }
        
        // Rejoin lobby
        this.joinLobby(this.currentRoomCode)
      }
    })

    this.socket.on('disconnect', reason => {
      console.log('WebSocket disconnected:', reason)
      this.connected = false
      
      // Record disconnect timestamp for grace period
      this.recordDisconnect()
      
      // Trigger reconnection handling
      if (this.eventHandlers.has('_internal_disconnect')) {
        const handler = this.eventHandlers.get('_internal_disconnect')
        handler({ reason, roomCode: this.currentRoomCode })
      }
    })

    this.socket.on('connect_error', error => {
      console.error('WebSocket connection error:', error)
      this.reconnectionAttempts++
      
      if (this.reconnectionAttempts >= this.maxReconnectionAttempts) {
        console.error('Max reconnection attempts reached')
        
        // Clear session state on max attempts
        this.clearSessionState()
        
        if (this.eventHandlers.has('_internal_reconnection_failed')) {
          const handler = this.eventHandlers.get('_internal_reconnection_failed')
          handler({ roomCode: this.currentRoomCode })
        }
      }
    })

    // Reconnection events
    this.socket.on('reconnected', (data) => {
      console.log('Successfully reconnected:', data)
      if (this.eventHandlers.has('reconnected')) {
        const handler = this.eventHandlers.get('reconnected')
        handler(data)
      }
    })

    this.socket.on('reconnection_failed', (data) => {
      console.error('Reconnection failed:', data)
      if (this.eventHandlers.has('reconnection_failed')) {
        const handler = this.eventHandlers.get('reconnection_failed')
        handler(data)
      }
    })

    this.socket.on('player_disconnected', (data) => {
      console.log('Player disconnected:', data)
      if (this.eventHandlers.has('player_disconnected')) {
        const handler = this.eventHandlers.get('player_disconnected')
        handler(data)
      }
    })

    this.socket.on('player_reconnected', (data) => {
      console.log('Player reconnected:', data)
      if (this.eventHandlers.has('player_reconnected')) {
        const handler = this.eventHandlers.get('player_reconnected')
        handler(data)
      }
    })

    this.socket.on('player_replaced_by_ai', (data) => {
      console.log('Player replaced by AI:', data)
      if (this.eventHandlers.has('player_replaced_by_ai')) {
        const handler = this.eventHandlers.get('player_replaced_by_ai')
        handler(data)
      }
    })

    return this.socket
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
      this.connected = false
    }
  }

  on(event, handler) {
    if (!this.socket) {
      this.connect()
    }
    this.socket.on(event, handler)
    this.eventHandlers.set(event, handler)
  }

  off(event) {
    if (this.socket && this.eventHandlers.has(event)) {
      this.socket.off(event, this.eventHandlers.get(event))
      this.eventHandlers.delete(event)
    }
  }

  emit(event, data, callback) {
    if (!this.socket || !this.connected) {
      console.error('WebSocket not connected')
      return
    }
    this.socket.emit(event, data, callback)
  }

  isConnected() {
    return this.connected
  }

  // Room-related events
  joinRoom(roomCode, playerId) {
    this.currentRoomCode = roomCode
    this.currentPlayerId = playerId
    this.emit('join_room', { room_code: roomCode, player_id: playerId })
  }

  leaveRoom(roomCode, playerId) {
    this.emit('leave_room', { room_code: roomCode, player_id: playerId })
    this.currentRoomCode = null
    this.currentPlayerId = null
  }

  // Lobby-specific events (for Phase 3)
  joinLobby(roomCode) {
    this.currentRoomCode = roomCode
    this.saveSessionState(roomCode) // Persist to sessionStorage
    this.emit('join_lobby', { room_code: roomCode })
  }

  leaveLobby(roomCode) {
    this.emit('leave_lobby', { room_code: roomCode })
    this.clearSessionState() // Clear on clean leave
    this.currentRoomCode = null
  }

  onLobbyJoined(handler) {
    this.on('lobby_joined', handler)
  }

  onLobbyLeft(handler) {
    this.on('lobby_left', handler)
  }

  onAIAgentAdded(handler) {
    this.on('ai_agent_added', handler)
  }

  onAIAgentRemoved(handler) {
    this.on('ai_agent_removed', handler)
  }

  onOwnershipTransferred(handler) {
    this.on('ownership_transferred', handler)
  }

  onRoomDissolved(handler) {
    this.on('room_dissolved', handler)
  }

  // Reconnection event handlers
  onDisconnected(handler) {
    this.eventHandlers.set('_internal_disconnect', handler)
  }

  onReconnectionFailed(handler) {
    this.eventHandlers.set('_internal_reconnection_failed', handler)
  }
  
  /**
   * Register handler for reconnection event
   * This is called when WebSocket reconnects after disconnect
   * Handler should sync room state from API
   */
  onReconnect(handler) {
    this.eventHandlers.set('_internal_reconnect', handler)
  }

  onReconnected(handler) {
    this.on('reconnected', handler)
  }

  onPlayerDisconnected(handler) {
    this.on('player_disconnected', handler)
  }

  onPlayerReconnected(handler) {
    this.on('player_reconnected', handler)
  }

  onPlayerReplacedByAI(handler) {
    this.on('player_replaced_by_ai', handler)
  }

  onPlayerJoined(handler) {
    this.on('player_joined', handler)
  }

  onPlayerLeft(handler) {
    this.on('player_left', handler)
  }

  onGameStarted(handler) {
    this.on('game_started', handler)
  }

  onRoomJoined(handler) {
    this.on('room_joined', handler)
  }

  onRoomLeft(handler) {
    this.on('room_left', handler)
  }

  // Game action submission
  sendGameAction(roomCode, playerId, action) {
    this.emit('game_action', {
      room_code: roomCode,
      player_id: playerId,
      action: action
    })
  }

  // Game state events (for Phase 4)
  onGameStateUpdate(handler) {
    this.on('game_state_update', handler)
  }

  onTurnChanged(handler) {
    this.on('turn_changed', handler)
  }

  onAiThinking(handler) {
    this.on('ai_thinking', handler)
  }

  onAiAction(handler) {
    this.on('ai_action', handler)
  }

  onGameEnded(handler) {
    this.on('game_ended', handler)
  }

  onError(handler) {
    this.on('error', handler)
  }

  // Clean up room event listeners
  offRoomEvents() {
    this.off('player_joined')
    this.off('player_left')
    this.off('game_started')
    this.off('room_joined')
    this.off('room_left')
    this.off('error')
  }

  // Clean up lobby event listeners
  offLobbyEvents() {
    this.off('player_joined')
    this.off('player_left')
    this.off('ai_agent_added')
    this.off('ai_agent_removed')
    this.off('ownership_transferred')
    this.off('room_dissolved')
    this.off('lobby_joined')
    this.off('lobby_left')
  }

  // Clean up game event listeners
  offGameEvents() {
    this.off('game_state_update')
    this.off('turn_changed')
    this.off('ai_thinking')
    this.off('ai_action')
    this.off('game_ended')
  }
}

export default new WebSocketService()

