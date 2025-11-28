/**
 * Socket store for managing WebSocket connections
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { io } from 'socket.io-client'

const SOCKET_URL = import.meta.env.VITE_WS_URL || 'http://localhost:8000'

export const useSocketStore = defineStore('socket', () => {
  // State
  const socket = ref(null)
  const isConnected = ref(false)
  const isReconnecting = ref(false)
  const reconnectAttempts = ref(0)
  const error = ref(null)
  const roomCode = ref(null)
  
  // Event listeners map
  const eventListeners = ref(new Map())

  // Computed
  const connectionStatus = computed(() => {
    if (isConnected.value) return 'connected'
    if (isReconnecting.value) return 'reconnecting'
    return 'disconnected'
  })

  // Connect to socket server
  function connect(options = {}) {
    if (socket.value?.connected) {
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      try {
        socket.value = io(SOCKET_URL, {
          transports: ['websocket', 'polling'],
          reconnection: true,
          reconnectionAttempts: 10,
          reconnectionDelay: 1000,
          reconnectionDelayMax: 5000,
          timeout: 20000,
          ...options
        })

        // Connection events
        socket.value.on('connect', () => {
          console.log('Socket connected:', socket.value.id)
          isConnected.value = true
          isReconnecting.value = false
          reconnectAttempts.value = 0
          error.value = null
          resolve()
        })

        socket.value.on('disconnect', (reason) => {
          console.log('Socket disconnected:', reason)
          isConnected.value = false
          
          if (reason === 'io server disconnect') {
            // Server initiated disconnect, won't auto reconnect
            socket.value.connect()
          }
        })

        socket.value.on('connect_error', (err) => {
          console.error('Socket connection error:', err)
          error.value = err.message
          if (!isConnected.value) {
            reject(err)
          }
        })

        socket.value.on('reconnecting', (attemptNumber) => {
          console.log('Socket reconnecting, attempt:', attemptNumber)
          isReconnecting.value = true
          reconnectAttempts.value = attemptNumber
        })

        socket.value.on('reconnect', () => {
          console.log('Socket reconnected')
          isReconnecting.value = false
          reconnectAttempts.value = 0
          
          // Rejoin room if previously joined
          if (roomCode.value) {
            joinRoom(roomCode.value)
          }
        })

        socket.value.on('reconnect_failed', () => {
          console.error('Socket reconnection failed')
          isReconnecting.value = false
          error.value = 'Connection failed after multiple attempts'
        })

      } catch (err) {
        console.error('Socket initialization error:', err)
        error.value = err.message
        reject(err)
      }
    })
  }

  // Disconnect from socket server
  function disconnect() {
    if (socket.value) {
      socket.value.disconnect()
      socket.value = null
      isConnected.value = false
      roomCode.value = null
      eventListeners.value.clear()
    }
  }

  // Join a room
  function joinRoom(code) {
    if (!socket.value?.connected) {
      console.warn('Cannot join room: socket not connected')
      return
    }
    
    roomCode.value = code
    socket.value.emit('join_room', { room_code: code })
    console.log('Joining room:', code)
  }

  // Leave current room
  function leaveRoom() {
    if (!socket.value?.connected || !roomCode.value) {
      return
    }
    
    socket.value.emit('leave_room', { room_code: roomCode.value })
    roomCode.value = null
  }

  // Emit an event
  function emit(event, data) {
    if (!socket.value?.connected) {
      console.warn('Cannot emit event: socket not connected')
      return
    }
    
    socket.value.emit(event, data)
  }

  // Register event listener
  function on(event, callback) {
    if (!socket.value) {
      console.warn('Cannot register listener: socket not initialized')
      return
    }
    
    socket.value.on(event, callback)
    
    // Track listener for cleanup
    if (!eventListeners.value.has(event)) {
      eventListeners.value.set(event, [])
    }
    eventListeners.value.get(event).push(callback)
  }

  // Remove event listener
  function off(event, callback) {
    if (!socket.value) return
    
    if (callback) {
      socket.value.off(event, callback)
      
      // Remove from tracked listeners
      const listeners = eventListeners.value.get(event)
      if (listeners) {
        const index = listeners.indexOf(callback)
        if (index > -1) {
          listeners.splice(index, 1)
        }
      }
    } else {
      // Remove all listeners for this event
      socket.value.off(event)
      eventListeners.value.delete(event)
    }
  }

  // Clear all event listeners
  function clearListeners() {
    if (!socket.value) return
    
    eventListeners.value.forEach((callbacks, event) => {
      callbacks.forEach(callback => {
        socket.value.off(event, callback)
      })
    })
    eventListeners.value.clear()
  }

  // Reset store
  function reset() {
    disconnect()
    error.value = null
    reconnectAttempts.value = 0
  }

  return {
    // State
    socket,
    isConnected,
    isReconnecting,
    reconnectAttempts,
    error,
    roomCode,
    
    // Computed
    connectionStatus,
    
    // Actions
    connect,
    disconnect,
    joinRoom,
    leaveRoom,
    emit,
    on,
    off,
    clearListeners,
    reset
  }
})
