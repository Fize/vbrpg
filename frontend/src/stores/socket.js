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

  /**
   * 设置主持人相关的 WebSocket 事件监听
   * @param {Object} gameStore - 游戏 store 实例
   */
  function setupHostHandlers(gameStore) {
    // 主持人发言（完整）
    on('werewolf:host_announcement', (data) => {
      gameStore.addGameLog({
        type: 'host_announcement',
        player_id: 'host',
        player_name: '主持人',
        content: data.content,
        announcement_type: data.type
      })
    })
    
    // 主持人发言开始
    on('werewolf:host_announcement_start', (data) => {
      gameStore.addStreamingLog({
        type: 'host_announcement',
        player_id: 'host',
        player_name: '主持人',
        content: '',
        announcement_type: data.type
      })
    })
    
    // 主持人发言片段
    on('werewolf:host_announcement_chunk', (data) => {
      gameStore.updateStreamingLog('host', data.chunk)
    })
    
    // 主持人发言结束
    on('werewolf:host_announcement_end', (data) => {
      gameStore.finalizeStreamingLog('host', data.content)
    })
  }

  /**
   * 设置狼人杀游戏相关的 WebSocket 事件监听
   * @param {Object} gameStore - 游戏 store 实例
   */
  function setupWerewolfHandlers(gameStore) {
    // 游戏状态更新
    on('werewolf:game_state', (data) => {
      gameStore.updateGameState(data)
    })
    
    // 游戏阶段变化
    on('werewolf:phase_change', (data) => {
      gameStore.setPhase(data.to_phase)
      if (data.day_number !== undefined) {
        gameStore.updateGameState({ dayNumber: data.day_number })
      }
    })
    
    // 玩家发言开始
    on('werewolf:speech_start', (data) => {
      gameStore.setSpeakingPlayer(data.speaker_seat)
      gameStore.addStreamingLog({
        type: 'speech',
        player_id: `seat_${data.speaker_seat}`,
        player_name: data.speaker_name,
        content: ''
      })
    })
    
    // 玩家发言片段
    on('werewolf:speech_chunk', (data) => {
      gameStore.updateStreamingLog(`seat_${data.speaker_seat}`, data.chunk)
    })
    
    // 玩家发言结束
    on('werewolf:speech_end', (data) => {
      gameStore.finalizeStreamingLog(`seat_${data.speaker_seat}`, data.content)
      gameStore.setSpeakingPlayer(null)
    })
    
    // 轮到你行动
    on('werewolf:your_turn', (data) => {
      gameStore.setMyTurn(true, {
        role: data.role,
        action: data.action,
        targets: data.targets,
        message: data.message
      })
    })
    
    // 预言家查验结果
    on('werewolf:seer_result', (data) => {
      gameStore.addGameLog({
        type: 'seer_result',
        target_seat: data.target_seat,
        target_name: data.target_name,
        is_werewolf: data.is_werewolf,
        message: data.message
      })
    })
    
    // 投票更新
    on('werewolf:vote_update', (data) => {
      gameStore.addVote(data.voter_seat, data.target_seat, data.is_abstain)
    })
    
    // 投票结果
    on('werewolf:vote_result', (data) => {
      gameStore.updateVoteResults(data.vote_counts)
      if (data.eliminated_seat) {
        gameStore.addGameLog({
          type: 'vote_result',
          eliminated_seat: data.eliminated_seat,
          eliminated_name: data.eliminated_name,
          message: `投票结果：${data.eliminated_name} 被放逐`
        })
      } else if (data.is_tie) {
        gameStore.addGameLog({
          type: 'vote_result',
          is_tie: true,
          message: '投票结果：平票，无人出局'
        })
      }
    })
    
    // 游戏结束
    on('werewolf:game_over', (data) => {
      gameStore.setGameEnded(true, data.winner, data.winning_players)
      gameStore.setAllPlayersInfo(data.all_players)
      gameStore.addGameLog({
        type: 'game_end',
        winner: data.winner,
        message: `游戏结束！${data.winner_name}获胜`
      })
    })
    
    // 猎人开枪通知
    on('werewolf:hunter_shoot', (data) => {
      gameStore.setMyTurn(true, {
        role: 'hunter',
        action: 'shoot',
        targets: data.targets,
        message: data.message
      })
    })
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
    setupHostHandlers,
    setupWerewolfHandlers,
    reset
  }
})
