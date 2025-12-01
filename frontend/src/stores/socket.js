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

  // ============ F8: 封装的游戏控制 emit 方法 ============

  /**
   * F8: 发送开始游戏事件
   * @param {string} roomCode - 房间代码
   * @param {string} playerId - 玩家ID（可选）
   * @throws {Error} 连接断开时抛出异常
   */
  function startGame(roomCode, playerId = null) {
    if (!socket.value?.connected) {
      throw new Error('WebSocket 未连接，无法开始游戏')
    }
    socket.value.emit('werewolf_start_game', {
      room_code: roomCode,
      player_id: playerId
    })
  }

  /**
   * F8: 发送暂停游戏事件
   * @param {string} roomCode - 房间代码
   * @param {string} playerId - 玩家ID（可选）
   * @throws {Error} 连接断开时抛出异常
   */
  function pauseGame(roomCode, playerId = null) {
    if (!socket.value?.connected) {
      throw new Error('WebSocket 未连接，无法暂停游戏')
    }
    socket.value.emit('werewolf_pause_game', {
      room_code: roomCode,
      player_id: playerId
    })
  }

  /**
   * F8: 发送继续游戏事件
   * @param {string} roomCode - 房间代码
   * @param {string} playerId - 玩家ID（可选）
   * @throws {Error} 连接断开时抛出异常
   */
  function resumeGame(roomCode, playerId = null) {
    if (!socket.value?.connected) {
      throw new Error('WebSocket 未连接，无法继续游戏')
    }
    socket.value.emit('werewolf_resume_game', {
      room_code: roomCode,
      player_id: playerId
    })
  }

  /**
   * 发送离开狼人杀房间事件，停止游戏并清理资源
   * @param {string} roomCode - 房间代码
   * @param {string} playerId - 玩家ID（可选）
   */
  function leaveWerewolfRoom(roomCode, playerId = null) {
    if (!socket.value?.connected) {
      console.warn('WebSocket 未连接，无法发送离开房间事件')
      return
    }
    socket.value.emit('werewolf_leave_room', {
      room_code: roomCode,
      player_id: playerId
    })
    console.log('Sent werewolf_leave_room event for room:', roomCode)
  }

  /**
   * F8: 发送玩家发言事件
   * @param {string} roomCode - 房间代码
   * @param {string} playerId - 玩家ID
   * @param {number} seatNumber - 座位号
   * @param {string} content - 发言内容
   * @throws {Error} 连接断开时或发言为空时抛出异常
   */
  function submitSpeech(roomCode, playerId, seatNumber, content) {
    if (!socket.value?.connected) {
      throw new Error('WebSocket 未连接，无法提交发言')
    }
    if (!content || !content.trim()) {
      throw new Error('发言内容不能为空')
    }
    socket.value.emit('werewolf_player_speech', {
      room_code: roomCode,
      player_id: playerId,
      seat_number: seatNumber,
      content: content.trim()
    })
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
      
      // 处理死亡公告
      if (data.type === 'death' && data.metadata && data.metadata.seat_number) {
        gameStore.setPlayerDeadBySeat(data.metadata.seat_number)
      }
    })
    
    // 主持人发言开始 (F6: 流式公告)
    on('werewolf:host_announcement_start', (data) => {
      gameStore.startHostAnnouncement(data.type, data.metadata || {})
      gameStore.addStreamingLog({
        type: 'host_announcement',
        player_id: 'host',
        player_name: '主持人',
        content: '',
        announcement_type: data.type
      })
    })
    
    // 主持人发言片段 (F6: 流式公告)
    on('werewolf:host_announcement_chunk', (data) => {
      gameStore.appendHostAnnouncementChunk(data.chunk)
      gameStore.updateStreamingLog('host', gameStore.hostAnnouncement.content)
    })
    
    // 主持人发言结束 (F6: 流式公告)
    on('werewolf:host_announcement_end', (data) => {
      gameStore.endHostAnnouncement(data.content, data.metadata || {})
      gameStore.finalizeStreamingLog('host', data.content)
      
      // 处理死亡玩家信息（从dawn公告的metadata中获取）
      if (data.metadata && data.metadata.dead_players) {
        data.metadata.dead_players.forEach(p => {
          gameStore.setPlayerDeadBySeat(p.seat_number)
        })
      }
    })
  }

  /**
   * F5: 设置游戏控制相关的 WebSocket 事件监听
   * @param {Object} gameStore - 游戏 store 实例
   */
  function setupGameControlHandlers(gameStore) {
    // 游戏开始
    on('werewolf:game_starting', (data) => {
      console.log('Game starting:', data)
    })
    
    on('werewolf:game_started', (data) => {
      gameStore.setGameStarted(true)
      gameStore.addGameLog({
        type: 'system',
        content: '游戏已开始',
        announcement_type: 'game_start'
      })
    })
    
    // 游戏暂停
    on('werewolf:game_paused', (data) => {
      gameStore.setGamePaused(true)
      gameStore.addGameLog({
        type: 'system',
        content: data.message || '游戏已暂停',
        announcement_type: 'game_paused'
      })
    })
    
    // 游戏继续
    on('werewolf:game_resumed', (data) => {
      gameStore.setGamePaused(false)
      gameStore.addGameLog({
        type: 'system',
        content: data.message || '游戏继续',
        announcement_type: 'game_resumed'
      })
    })
  }

  /**
   * F7: 设置发言相关的 WebSocket 事件监听
   * @param {Object} gameStore - 游戏 store 实例
   */
  function setupSpeechHandlers(gameStore) {
    // 点名发言 (F8: request_speech)
    on('werewolf:request_speech', (data) => {
      gameStore.setCurrentSpeaker(data.seat_number, data.player_name, data.is_human)
      
      // 如果是人类玩家被点名，设置等待输入状态
      if (data.is_human) {
        gameStore.setWaitingForInput(true)
      }
      
      // 开始发言气泡
      gameStore.startSpeechBubble(data.seat_number, data.player_name)
      
      gameStore.addGameLog({
        type: 'host_announcement',
        content: data.announcement,
        announcement_type: 'request_speech',
        metadata: { seat_number: data.seat_number }
      })
    })
    
    // 发言提醒 (F8: speech_reminder)
    on('werewolf:speech_reminder', (data) => {
      gameStore.addGameLog({
        type: 'system',
        content: data.message,
        announcement_type: 'speech_reminder',
        metadata: { 
          seat_number: data.seat_number,
          reminder_count: data.reminder_count 
        }
      })
    })
    
    // 发言已收到确认
    on('werewolf:speech_received', (data) => {
      gameStore.setWaitingForInput(false)
    })
    
    // 玩家发言 (广播)
    on('werewolf:player_speech', (data) => {
      // 更新发言气泡
      if (gameStore.activeSpeechBubbles[data.seat_number]) {
        gameStore.endSpeechBubble(data.seat_number, data.content)
      }
      
      gameStore.addGameLog({
        type: 'speech',
        player_id: `seat_${data.seat_number}`,
        player_name: data.player_name,
        content: data.content
      })
    })
    
    // 发言结束 (F8: speech_end)
    on('werewolf:speech_end', (data) => {
      gameStore.clearCurrentSpeaker()
      gameStore.clearSpeechBubble(data.seat_number)
      
      if (data.announcement) {
        gameStore.addGameLog({
          type: 'host_announcement',
          content: data.announcement,
          announcement_type: 'speech_end_transition'
        })
      }
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
      // 更新死亡玩家状态
      if (data.dead_players && data.dead_players.length > 0) {
        data.dead_players.forEach(p => {
          gameStore.setPlayerDeadBySeat(p.seat_number)
        })
      }
    })
    
    // 游戏阶段变化
    on('werewolf:phase_change', (data) => {
      gameStore.setPhase(data.to_phase)
      if (data.day_number !== undefined) {
        gameStore.updateGameState({ dayNumber: data.day_number })
      }
      // 阶段变化时清除所有发言气泡
      gameStore.clearAllSpeechBubbles()
    })
    
    // AI 玩家发言开始 (F7: 发言气泡)
    on('werewolf:speech_start', (data) => {
      gameStore.setSpeakingPlayer(data.speaker_seat)
      // 开始发言气泡流式显示
      gameStore.startSpeechBubble(data.speaker_seat, data.speaker_name)
      gameStore.addStreamingLog({
        type: 'speech',
        player_id: `seat_${data.speaker_seat}`,
        player_name: data.speaker_name,
        content: ''
      })
    })
    
    // AI 玩家发言片段 (F7: 发言气泡)
    on('werewolf:speech_chunk', (data) => {
      // 更新发言气泡内容
      gameStore.appendSpeechBubbleChunk(data.speaker_seat, data.chunk)
      gameStore.updateStreamingLog(`seat_${data.speaker_seat}`, 
        gameStore.activeSpeechBubbles[data.speaker_seat]?.content || data.chunk)
    })
    
    // AI 玩家发言结束 (F7: 发言气泡)
    on('werewolf:speech_end', (data) => {
      // 结束发言气泡（5秒后自动消失）
      gameStore.endSpeechBubble(data.speaker_seat, data.content)
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
        // 标记被放逐玩家为死亡状态
        gameStore.setPlayerDeadBySeat(data.eliminated_seat)
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
    setupGameControlHandlers,  // F5: 游戏控制事件
    setupSpeechHandlers,       // F7-F8: 发言相关事件
    setupWerewolfHandlers,
    reset,
    
    // F8: 封装的游戏控制方法
    startGame,
    pauseGame,
    resumeGame,
    leaveWerewolfRoom,
    submitSpeech
  }
})
