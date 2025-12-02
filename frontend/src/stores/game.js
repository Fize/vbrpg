/**
 * Game store for managing werewolf game rooms and state
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getPhaseCategory, getPhaseDisplayName, resolveNightSubPhase } from '@/utils/phase'

export const useGameStore = defineStore('game', () => {
  // ============ 基础状态 ============
  const currentRoom = ref(null)
  const participants = ref([])
  const gameState = ref(null)
  const isLoading = ref(false)
  const error = ref(null)
  
  // ============ 游戏进度状态 ============
  const currentTurn = ref(null)
  const turnNumber = ref(0)
  const currentPhase = ref(null) // 'night' | 'day' | 'discussion' | 'vote' | 'result'
  const subPhase = ref(null) // 夜间子阶段: 'werewolf' | 'seer' | 'witch' | 'hunter'
  const dayNumber = ref(1)
  const countdown = ref(0)
  const phaseCategory = computed(() => getPhaseCategory(currentPhase.value))
  
  // ============ F1: 游戏控制状态 ============
  const isStarted = ref(false)  // 游戏是否已开始
  const isPaused = ref(false)   // 游戏是否暂停
  
  // ============ F2: 主持人公告状态 ============
  const hostAnnouncement = ref({
    type: null,       // 公告类型
    content: '',      // 当前公告内容
    isStreaming: false  // 是否正在流式输出
  })
  const announcementHistory = ref([])  // 历史公告列表
  
  // ============ F3: 发言气泡状态 ============
  const activeSpeechBubbles = ref({})  // 格式: { [seatNumber]: { content, isStreaming, timer } }
  
  // ============ F4: 日志级别状态 ============
  const logLevel = ref('basic')  // 值: 'basic' | 'detailed'
  
  // ============ F9: 当前发言者状态 ============
  const currentSpeaker = ref({
    seatNumber: null,
    playerName: '',
    isHuman: false
  })
  const waitingForInput = ref(false)  // 是否等待玩家输入
  
  // ============ AI 状态 ============
  const isAiThinking = ref(false)
  const aiThinkingPlayer = ref(null)
  
  // ============ 游戏结果 ============
  const gameEnded = ref(false)
  const winner = ref(null) // 'werewolf' | 'villager' | null
  const winnerTeam = ref([])
  
  // ============ 玩家角色状态 ============
  const myPlayerId = ref(localStorage.getItem('playerId') || null)
  const myRole = ref(null) // { name, type, team, description }
  const isSpectator = ref(false)
  const mySkillTargets = ref([]) // 可使用技能的目标
  const mySkillUsed = ref(false) // 本回合技能是否已使用
  
  // ============ 玩家存活状态 ============
  const playerStates = ref({}) // { [playerId]: { is_alive, role_revealed, role_name, vote_count } }
  const seatPlayerMap = ref({}) // { [seatNumber]: playerId }
  
  // ============ 投票状态 ============
  const voteResults = ref({}) // { [targetId]: count }
  const myVote = ref(null) // 我的投票目标
  const hasVoted = ref(false)
  
  // ============ 游戏日志 ============
  const gameLogs = ref([])
  
  // ============ 发言状态 ============
  const speakingPlayerId = ref(null)
  const speakOrder = ref([]) // 发言顺序

  // ============ 计算属性 ============
  const isInRoom = computed(() => currentRoom.value !== null)
  const roomCode = computed(() => currentRoom.value?.code || null)
  
  // 单人模式下，用户始终是"房主"（有权限控制游戏）
  const isHost = computed(() => {
    // 只要在房间中，就有控制权限
    return currentRoom.value !== null
  })
  
  const activeParticipants = computed(() =>
    participants.value.filter((p) => p.is_active !== false)
  )
  
  const players = computed(() =>
    activeParticipants.value.filter((p) => !p.is_spectator)
  )
  
  const spectators = computed(() =>
    activeParticipants.value.filter((p) => p.is_spectator)
  )
  
  const aiPlayers = computed(() =>
    players.value.filter((p) => p.is_ai)
  )
  
  const alivePlayers = computed(() =>
    players.value.filter((p) => {
      const state = playerStates.value[p.id]
      return state ? state.is_alive : true
    })
  )
  
  const deadPlayers = computed(() =>
    players.value.filter((p) => {
      const state = playerStates.value[p.id]
      return state ? !state.is_alive : false
    })
  )
  
  const alivePlayerIds = computed(() => alivePlayers.value.map(p => p.id))
  const deadPlayerIds = computed(() => deadPlayers.value.map(p => p.id))
  
  const canStartGame = computed(() => {
    if (!currentRoom.value) return false
    if (currentRoom.value.status !== 'Waiting') return false
    return players.value.length === 10
  })
  
  const isMyTurn = computed(() => {
    return currentTurn.value === myPlayerId.value
  })
  
  const isGameInProgress = computed(() => {
    return currentRoom.value?.status === 'In Progress' && !gameEnded.value
  })
  
  const canUseSkill = computed(() => {
    if (isSpectator.value || !myRole.value) return false
    if (!alivePlayers.value.find(p => p.id === myPlayerId.value)) return false
    if (phaseCategory.value !== 'night') return false
    return !mySkillUsed.value
  })
  
  const canVote = computed(() => {
    if (isSpectator.value) return false
    if (!alivePlayers.value.find(p => p.id === myPlayerId.value)) return false
    if (phaseCategory.value !== 'vote') return false
    return !hasVoted.value
  })

  // ============ Actions ============
  function setMyPlayerId(id) {
    myPlayerId.value = id
    localStorage.setItem('playerId', id)
  }
  
  function setCurrentRoom(room) {
    currentRoom.value = room
    if (room) {
      const normalizedParticipants = (room.participants || []).map((participant, index) => {
        const seatNumber = participant.seat_number ?? index + 1
        const participantId = participant.id || participant.player_id || `seat_${seatNumber}`
        const displayName = participant.name || participant.player?.username || `玩家${seatNumber}`
        seatPlayerMap.value[seatNumber] = participantId
        if (!playerStates.value[participantId]) {
          playerStates.value[participantId] = {
            is_alive: participant.is_alive ?? true,
            role_revealed: false,
            role_name: null,
            role_type: null,
            vote_count: 0,
            seat_number: seatNumber,
            display_name: displayName
          }
        } else if (!playerStates.value[participantId].seat_number) {
          playerStates.value[participantId].seat_number = seatNumber
        }
        return {
          ...participant,
          id: participantId,
          seat_number: seatNumber,
          name: displayName,
          is_alive: participant.is_alive ?? true
        }
      })
      participants.value = normalizedParticipants
    }
  }

  function updateRoom(roomData) {
    if (currentRoom.value && currentRoom.value.code === roomData.code) {
      Object.assign(currentRoom.value, roomData)
      if (roomData.participants) {
        participants.value = roomData.participants
      }
    }
  }

  function setParticipants(participantsList) {
    const normalizedParticipants = participantsList.map((participant, index) => {
      const seatNumber = participant.seat_number ?? index + 1
      const participantId = participant.id || participant.player_id || `seat_${seatNumber}`
      const displayName = participant.name || participant.player?.username || `玩家${seatNumber}`
      seatPlayerMap.value[seatNumber] = participantId
      if (!playerStates.value[participantId]) {
        playerStates.value[participantId] = {
          is_alive: true,
          role_revealed: false,
          role_name: null,
          role_type: null,
          vote_count: 0,
          seat_number: seatNumber,
          display_name: displayName
        }
      }
      return {
        ...participant,
        id: participantId,
        seat_number: seatNumber,
        name: displayName
      }
    })
    participants.value = normalizedParticipants
  }

  function addParticipant(participant) {
    const existing = participants.value.find((p) => p.id === participant.id)
    if (!existing) {
      participants.value.push(participant)
      playerStates.value[participant.id] = {
        is_alive: true,
        role_revealed: false,
        role_name: null,
        vote_count: 0
      }
    }
  }

  function removeParticipant(participantId) {
    const index = participants.value.findIndex((p) => p.id === participantId)
    if (index !== -1) {
      participants.value[index].is_active = false
    }
  }

  function setGameState(state) {
    gameState.value = state
    
    // 解析游戏状态
    if (state) {
      if (state.day_number !== undefined) dayNumber.value = state.day_number
      if (state.phase !== undefined || state.sub_phase !== undefined) {
        syncPhaseState(state.phase, state.sub_phase)
      }
      if (state.player_states) {
        Object.assign(playerStates.value, state.player_states)
      }
      if (state.vote_results) voteResults.value = state.vote_results
    }
  }

  function updateGameState(stateUpdate) {
    if (gameState.value) {
      Object.assign(gameState.value, stateUpdate)
    } else {
      gameState.value = stateUpdate
    }
    
    // 更新相关状态
    if (stateUpdate.current_turn_player_id) {
      currentTurn.value = stateUpdate.current_turn_player_id
    }
    if (stateUpdate.turn_number !== undefined) {
      turnNumber.value = stateUpdate.turn_number
    }
    if (
      stateUpdate.current_phase !== undefined
      || stateUpdate.phase !== undefined
      || stateUpdate.sub_phase !== undefined
    ) {
      const nextPhase =
        stateUpdate.current_phase !== undefined
          ? stateUpdate.current_phase
          : stateUpdate.phase
      syncPhaseState(nextPhase, stateUpdate.sub_phase)
    }
    if (stateUpdate.day_number !== undefined) {
      dayNumber.value = stateUpdate.day_number
    }
    if (stateUpdate.countdown !== undefined) {
      countdown.value = stateUpdate.countdown
    }
    if (stateUpdate.player_states) {
      Object.assign(playerStates.value, stateUpdate.player_states)
    }
    if (stateUpdate.vote_results) {
      voteResults.value = stateUpdate.vote_results
    }
    if (stateUpdate.speaking_player_id !== undefined) {
      speakingPlayerId.value = stateUpdate.speaking_player_id
    }
  }

  function syncPhaseState(phaseValue, providedSubPhase) {
    const hasPhaseValue = phaseValue !== undefined
    const hasSubPhaseValue = providedSubPhase !== undefined
    if (!hasPhaseValue && !hasSubPhaseValue) {
      return
    }
    if (hasPhaseValue) {
      currentPhase.value = phaseValue
      subPhase.value = resolveNightSubPhase(phaseValue, providedSubPhase)
    } else if (hasSubPhaseValue) {
      subPhase.value = providedSubPhase
    }
  }
  
  function setMyRole(role) {
    myRole.value = role
  }
  
  function setIsSpectator(spectator) {
    isSpectator.value = spectator
  }
  
  function setPlayerStates(states) {
    const nextSeatMap = {}
    const nextStates = {}
    Object.entries(states).forEach(([playerId, state]) => {
      const seatNumber = state.seat_number ?? state.seatNumber
      if (seatNumber !== undefined) {
        nextSeatMap[Number(seatNumber)] = playerId
      }
      nextStates[playerId] = {
        ...state,
        seat_number: seatNumber
      }
    })
    playerStates.value = nextStates
    if (Object.keys(nextSeatMap).length > 0) {
      seatPlayerMap.value = nextSeatMap
    }
    participants.value = participants.value.map((participant, index) => {
      const state = nextStates[participant.id]
      if (state && state.seat_number !== undefined) {
        return {
          ...participant,
          seat_number: state.seat_number
        }
      }
      if (participant.seat_number !== undefined) {
        return participant
      }
      return {
        ...participant,
        seat_number: index + 1
      }
    })
  }
  
  function setCurrentPhase(phase, sub = undefined) {
    syncPhaseState(phase, sub)
  }
  
  function setTurnNumber(turn) {
    turnNumber.value = turn
  }
  
  function setCurrentTurn(playerId, turn) {
    currentTurn.value = playerId
    if (turn !== undefined) {
      turnNumber.value = turn
    }
  }
  
  function setPhase(phase, sub = undefined) {
    syncPhaseState(phase, sub)
    const normalizedPhase = getPhaseCategory(phase)
    
    // 重置回合状态
    if (normalizedPhase === 'night') {
      mySkillUsed.value = false
    } else if (normalizedPhase === 'vote') {
      hasVoted.value = false
      myVote.value = null
      voteResults.value = {}
    }
  }
  
  function setAiThinking(thinking, playerId = null) {
    isAiThinking.value = thinking
    aiThinkingPlayer.value = playerId
  }
  
  function setGameEnded(endedStatus, winnerTeamName = null, winnerPlayers = []) {
    gameEnded.value = endedStatus
    winner.value = winnerTeamName
    winnerTeam.value = winnerPlayers
    if (endedStatus && currentRoom.value) {
      currentRoom.value.status = 'Completed'
    }
  }
  
  function setPlayerDead(playerId, roleName = null) {
    if (playerStates.value[playerId]) {
      playerStates.value[playerId].is_alive = false
      if (roleName) {
        playerStates.value[playerId].role_revealed = true
        playerStates.value[playerId].role_name = roleName
      }
    }
  }

  // 根据座位号标记玩家死亡
  function setPlayerDeadBySeat(seatNumber, roleName = null) {
    console.log('setPlayerDeadBySeat called with:', seatNumber, 'seatPlayerMap:', JSON.stringify(seatPlayerMap.value))
    if (seatNumber === undefined || seatNumber === null) {
      console.log('seatNumber is undefined or null, returning')
      return
    }
    const normalizedSeat = Number(seatNumber)
    const playerId = seatPlayerMap.value[normalizedSeat]
    console.log('Looking for playerId with seat', normalizedSeat, '-> found:', playerId)
    if (playerId) {
      setPlayerDead(playerId, roleName)
      console.log('Marked player dead:', playerId, 'playerStates:', JSON.stringify(playerStates.value[playerId]))
    }
    const idx = participants.value.findIndex(p => Number(p.seat_number) === normalizedSeat)
    if (idx !== -1) {
      participants.value[idx].is_alive = false
      console.log('Marked participant dead at index:', idx)
    }
  }
  
  function setVote(targetId) {
    myVote.value = targetId
    hasVoted.value = true
  }
  
  function updateVoteResults(results) {
    voteResults.value = results
    // 更新玩家票数
    Object.entries(results).forEach(([playerId, count]) => {
      if (playerStates.value[playerId]) {
        playerStates.value[playerId].vote_count = count
      }
    })
  }
  
  function addGameLog(log) {
    gameLogs.value.push({
      ...log,
      id: Date.now(),
      time: new Date().toISOString(),
      day: dayNumber.value,
      phase: currentPhase.value,
        phase_name: getPhaseDisplayName(currentPhase.value, subPhase.value)
    })
  }
  
  /**
   * 添加流式发言日志（发言开始时调用）
   * @param {Object} log - 日志对象
   * @param {string} log.type - 日志类型 ('speech' | 'host_announcement')
   * @param {string} log.player_id - 发言玩家 ID
   * @param {string} log.player_name - 发言玩家名称
   * @param {string} log.content - 初始内容（通常为空字符串）
   * @param {boolean} log.isStreaming - 是否正在流式输出
   */
  function addStreamingLog(log) {
    const streamingLog = {
      ...log,
      id: `streaming_${log.player_id}_${Date.now()}`,
      time: new Date().toISOString(),
      day: dayNumber.value,
      phase: currentPhase.value,
        phase_name: getPhaseDisplayName(currentPhase.value, subPhase.value),
      isStreaming: true
    }
    gameLogs.value.push(streamingLog)
    return streamingLog.id
  }
  
  /**
   * 更新流式发言内容（收到新的 chunk 时调用）
   * @param {string} playerId - 发言玩家 ID
   * @param {string} content - 累积的发言内容
   */
  function updateStreamingLog(playerId, content) {
    // 查找最后一条该玩家的流式日志
    for (let i = gameLogs.value.length - 1; i >= 0; i--) {
      const log = gameLogs.value[i]
      if (log.player_id === playerId && log.isStreaming) {
        log.content = content
        return
      }
    }
  }
  
  /**
   * 完成流式发言（发言结束时调用）
   * @param {string} playerId - 发言玩家 ID
   * @param {string} fullContent - 完整的发言内容
   */
  function finalizeStreamingLog(playerId, fullContent) {
    // 查找最后一条该玩家的流式日志
    for (let i = gameLogs.value.length - 1; i >= 0; i--) {
      const log = gameLogs.value[i]
      if (log.player_id === playerId && log.isStreaming) {
        log.content = fullContent
        log.isStreaming = false
        return
      }
    }
  }
  
  function setSpeakingPlayer(playerId) {
    speakingPlayerId.value = playerId
  }
  
  function setSkillTargets(targets) {
    mySkillTargets.value = targets
  }
  
  function useSkill() {
    mySkillUsed.value = true
  }
  
  function setCountdown(seconds) {
    countdown.value = seconds
  }

  // ============ F1-F4, F9: 新增游戏控制 Actions ============
  
  /**
   * F1: 设置游戏开始状态
   */
  function setGameStarted(started) {
    isStarted.value = started
    if (started) {
      isPaused.value = false
    }
  }
  
  /**
   * F1: 设置游戏暂停状态
   */
  function setGamePaused(paused) {
    isPaused.value = paused
  }
  
  /**
   * F2: 开始流式公告
   */
  function startHostAnnouncement(type, metadata = {}) {
    hostAnnouncement.value = {
      type,
      content: '',
      isStreaming: true,
      metadata
    }
  }
  
  /**
   * F2: 追加流式公告内容
   */
  function appendHostAnnouncementChunk(chunk) {
    if (hostAnnouncement.value.isStreaming) {
      hostAnnouncement.value.content += chunk
    }
  }
  
  /**
   * F2: 结束流式公告
   */
  function endHostAnnouncement(fullContent, metadata = {}) {
    const announcement = {
      type: hostAnnouncement.value.type,
      content: fullContent || hostAnnouncement.value.content,
      metadata: { ...hostAnnouncement.value.metadata, ...metadata },
      time: new Date().toISOString(),
      day: dayNumber.value
    }
    
    // 添加到历史
    announcementHistory.value.push(announcement)
    
    // 保留当前公告固定显示，不重置
    hostAnnouncement.value = {
      type: announcement.type,
      content: announcement.content,
      isStreaming: false,
      metadata: announcement.metadata
    }
    
    return announcement
  }
  
  /**
   * F3: 开始发言气泡流式显示
   */
  function startSpeechBubble(seatNumber, playerName) {
    // 清除之前的所有气泡，确保同一时间只有一个发言气泡
    clearAllSpeechBubbles()
    
    activeSpeechBubbles.value[seatNumber] = {
      content: '',
      playerName,
      isStreaming: true,
      startTime: Date.now()
    }
  }
  
  /**
   * F3: 追加发言气泡内容
   */
  function appendSpeechBubbleChunk(seatNumber, chunk) {
    if (activeSpeechBubbles.value[seatNumber]) {
      activeSpeechBubbles.value[seatNumber].content += chunk
    }
  }
  
  /**
   * F3: 结束发言气泡流式显示
   */
  function endSpeechBubble(seatNumber, fullContent) {
    if (activeSpeechBubbles.value[seatNumber]) {
      activeSpeechBubbles.value[seatNumber].content = fullContent
      activeSpeechBubbles.value[seatNumber].isStreaming = false
      
      // 设置定时器，10秒后自动消失
      setTimeout(() => {
        clearSpeechBubble(seatNumber)
      }, 10000)
    }
  }
  
  /**
   * F3: 清除发言气泡
   */
  function clearSpeechBubble(seatNumber) {
    delete activeSpeechBubbles.value[seatNumber]
  }
  
  /**
   * F3: 清除所有发言气泡
   */
  function clearAllSpeechBubbles() {
    activeSpeechBubbles.value = {}
  }
  
  /**
   * F4: 设置日志级别
   */
  function setLogLevel(level) {
    if (level === 'basic' || level === 'detailed') {
      logLevel.value = level
    }
  }
  
  /**
   * F9: 设置当前发言者
   */
  function setCurrentSpeaker(seatNumber, playerName, isHuman = false) {
    currentSpeaker.value = {
      seatNumber,
      playerName,
      isHuman
    }
    waitingForInput.value = isHuman
  }
  
  /**
   * F9: 清除当前发言者
   */
  function clearCurrentSpeaker() {
    currentSpeaker.value = {
      seatNumber: null,
      playerName: '',
      isHuman: false
    }
    waitingForInput.value = false
  }
  
  /**
   * F9: 设置等待玩家输入状态
   */
  function setWaitingForInput(waiting) {
    waitingForInput.value = waiting
  }
  
  // ============ F37-F40: 断线重连辅助方法 ============
  
  /**
   * F38: 清空游戏日志
   */
  function clearGameLogs() {
    gameLogs.value = []
  }
  
  /**
   * F39: 清空公告历史
   */
  function clearAnnouncementHistory() {
    announcementHistory.value = []
  }
  
  /**
   * F39: 添加到公告历史
   */
  function addToAnnouncementHistory(announcement) {
    announcementHistory.value.push(announcement)
  }
  
  /**
   * F39: 设置当前主持人公告
   */
  function setHostAnnouncement(announcement) {
    hostAnnouncement.value = {
      type: announcement.type || null,
      content: announcement.content || '',
      isStreaming: announcement.isStreaming || false,
      metadata: announcement.metadata || {}
    }
  }

  function setLoading(loading) {
    isLoading.value = loading
  }

  function setError(err) {
    error.value = err
  }

  function clearError() {
    error.value = null
  }

  function leaveRoom() {
    currentRoom.value = null
    participants.value = []
    gameState.value = null
    error.value = null
    currentTurn.value = null
    turnNumber.value = 0
    currentPhase.value = null
    subPhase.value = null
    dayNumber.value = 1
    countdown.value = 0
    isAiThinking.value = false
    aiThinkingPlayer.value = null
    gameEnded.value = false
    winner.value = null
    winnerTeam.value = []
    myRole.value = null
    isSpectator.value = false
    playerStates.value = {}
    voteResults.value = {}
    myVote.value = null
    hasVoted.value = false
    gameLogs.value = []
    speakingPlayerId.value = null
    mySkillTargets.value = []
    mySkillUsed.value = false
    seatPlayerMap.value = {}
    
    // F1-F4, F9: 重置新增状态
    isStarted.value = false
    isPaused.value = false
    hostAnnouncement.value = { type: null, content: '', isStreaming: false }
    announcementHistory.value = []
    activeSpeechBubbles.value = {}
    logLevel.value = 'basic'
    currentSpeaker.value = { seatNumber: null, playerName: '', isHuman: false }
    waitingForInput.value = false
  }

  function reset() {
    leaveRoom()
    myPlayerId.value = localStorage.getItem('playerId') || null
  }

  /**
   * 为新游戏重置状态（不清空房间信息）
   * 用于在同一房间重新开始游戏时清理上一局的数据
   */
  function resetForNewGame() {
    // 清理游戏进度状态
    gameState.value = null
    currentTurn.value = null
    turnNumber.value = 0
    currentPhase.value = null
    subPhase.value = null
    dayNumber.value = 1
    countdown.value = 0
    
    // 清理AI状态
    isAiThinking.value = false
    aiThinkingPlayer.value = null
    
    // 清理游戏结果
    gameEnded.value = false
    winner.value = null
    winnerTeam.value = []
    
    // 清理玩家状态（重要：确保新游戏时状态干净）
    playerStates.value = {}
    seatPlayerMap.value = {}
    
    // 清理投票状态
    voteResults.value = {}
    myVote.value = null
    hasVoted.value = false
    
    // 清理日志
    gameLogs.value = []
    
    // 清理发言状态
    speakingPlayerId.value = null
    mySkillTargets.value = []
    mySkillUsed.value = false
    
    // 清理控制状态
    isStarted.value = false
    isPaused.value = false
    
    // 清理公告状态
    hostAnnouncement.value = { type: null, content: '', isStreaming: false }
    announcementHistory.value = []
    activeSpeechBubbles.value = {}
    
    // 清理发言者状态
    currentSpeaker.value = { seatNumber: null, playerName: '', isHuman: false }
    waitingForInput.value = false
    
    console.log('Game state reset for new game')
  }

  // 设置我的回合状态
  function setMyTurn(isMyTurn, actionInfo = null) {
    if (isMyTurn && actionInfo) {
      mySkillTargets.value = actionInfo.targets || []
      // 可以根据 actionInfo.role 和 actionInfo.action 来显示相应的 UI
    }
  }

  // 添加投票
  function addVote(voterSeat, targetSeat, isAbstain) {
    if (targetSeat && !isAbstain) {
      const key = `seat_${targetSeat}`
      if (!voteResults.value[key]) {
        voteResults.value[key] = 0
      }
      voteResults.value[key]++
    }
  }

  // 更新玩家角色信息（游戏开始时从后端接收）
  function updatePlayerRoles(players) {
    const roleNameMap = {
      'werewolf': '狼人',
      'seer': '预言家',
      'witch': '女巫',
      'hunter': '猎人',
      'villager': '村民'
    }
    const roleTypeMap = {
      'werewolf': 'werewolf',
      'seer': 'god',
      'witch': 'god',
      'hunter': 'god',
      'villager': 'villager'
    }
    
    players.forEach(p => {
      const seatNumber = Number(p.seat_number)
      // 使用 seatPlayerMap 中已存在的 playerId，保持一致性
      // 如果没有则使用 seat_${seatNumber} 格式
      const existingPlayerId = seatPlayerMap.value[seatNumber]
      const key = existingPlayerId || `seat_${seatNumber}`
      const roleName = roleNameMap[p.role] || p.role
      const roleType = roleTypeMap[p.role] || 'villager'
      
      if (playerStates.value[key]) {
        playerStates.value[key].role_name = roleName
        playerStates.value[key].role_type = roleType
        playerStates.value[key].team = p.team
        playerStates.value[key].role_revealed = true
      } else {
        playerStates.value[key] = {
          seat_number: seatNumber,
          display_name: p.player_name,
          is_alive: true,
          role_name: roleName,
          role_type: roleType,
          team: p.team,
          role_revealed: true,
          vote_count: 0
        }
        // 只有在 seatPlayerMap 中没有该座位号时才设置
        if (!existingPlayerId) {
          seatPlayerMap.value[seatNumber] = key
        }
      }
    })
    
    console.log('Player roles updated:', playerStates.value)
  }

  // 设置所有玩家信息（游戏结束后）
  function setAllPlayersInfo(players) {
    // 角色名称映射
    const roleNameMap = {
      'werewolf': '狼人',
      'seer': '预言家',
      'witch': '女巫',
      'hunter': '猎人',
      'villager': '村民'
    }
    
    // 角色阵营映射
    const roleTypeMap = {
      'werewolf': 'werewolf',
      'seer': 'god',
      'witch': 'god',
      'hunter': 'god',
      'villager': 'villager'
    }
    
    players.forEach(p => {
      const seatNumber = Number(p.seat_number)
      // 使用 seatPlayerMap 中已存在的 playerId，保持一致性
      const existingPlayerId = seatPlayerMap.value[seatNumber]
      const key = existingPlayerId || `seat_${seatNumber}`
      // 使用后端传来的 role_name，如果没有则进行映射
      const roleName = p.role_name || roleNameMap[p.role] || p.role
      const roleType = roleTypeMap[p.role] || p.team || 'villager'
      
      if (playerStates.value[key]) {
        playerStates.value[key].role_name = roleName
        playerStates.value[key].role_type = roleType
        playerStates.value[key].team = p.team
        playerStates.value[key].role_revealed = true
        // 更新显示名称为角色名
        playerStates.value[key].display_name = roleName
      } else {
        playerStates.value[key] = {
          seat_number: seatNumber,
          display_name: roleName,
          is_alive: p.is_alive,
          role_name: roleName,
          role_type: roleType,
          team: p.team,
          role_revealed: true,
          vote_count: 0
        }
        // 只有在 seatPlayerMap 中没有该座位号时才设置
        if (!existingPlayerId) {
          seatPlayerMap.value[seatNumber] = key
        }
      }
    })
  }

  return {
    // State
    currentRoom,
    participants,
    gameState,
    isLoading,
    error,
    currentTurn,
    turnNumber,
    currentPhase,
    subPhase,
    dayNumber,
    countdown,
    isAiThinking,
    aiThinkingPlayer,
    gameEnded,
    winner,
    winnerTeam,
    myPlayerId,
    myRole,
    isSpectator,
    playerStates,
    seatPlayerMap,
    voteResults,
    myVote,
    hasVoted,
    gameLogs,
    speakingPlayerId,
    speakOrder,
    mySkillTargets,
    mySkillUsed,
    
    // F1-F4, F9: 新增状态
    isStarted,
    isPaused,
    hostAnnouncement,
    announcementHistory,
    activeSpeechBubbles,
    logLevel,
    currentSpeaker,
    waitingForInput,

    // Computed
    isInRoom,
    roomCode,
    isHost,
    activeParticipants,
    players,
    spectators,
    aiPlayers,
    alivePlayers,
    deadPlayers,
    alivePlayerIds,
    deadPlayerIds,
    canStartGame,
    isMyTurn,
    isGameInProgress,
    phaseCategory,
    canUseSkill,
    canVote,

    // Actions
    setMyPlayerId,
    setCurrentRoom,
    updateRoom,
    setParticipants,
    addParticipant,
    removeParticipant,
    setGameState,
    updateGameState,
    setMyRole,
    setIsSpectator,
    setPlayerStates,
    setCurrentPhase,
    setTurnNumber,
    setCurrentTurn,
    setPhase,
    setAiThinking,
    setGameEnded,
    setPlayerDead,
    setPlayerDeadBySeat,
    setVote,
    updateVoteResults,
    addGameLog,
    addStreamingLog,
    updateStreamingLog,
    finalizeStreamingLog,
    setSpeakingPlayer,
    setSkillTargets,
    useSkill,
    setCountdown,
    setLoading,
    setError,
    clearError,
    leaveRoom,
    reset,
    resetForNewGame,
    setMyTurn,
    addVote,
    setAllPlayersInfo,
    updatePlayerRoles,
    
    // F1-F4, F9: 新增 Actions
    setGameStarted,
    setGamePaused,
    startHostAnnouncement,
    appendHostAnnouncementChunk,
    endHostAnnouncement,
    startSpeechBubble,
    appendSpeechBubbleChunk,
    endSpeechBubble,
    clearSpeechBubble,
    clearAllSpeechBubbles,
    setLogLevel,
    setCurrentSpeaker,
    clearCurrentSpeaker,
    setWaitingForInput,
    
    // F37-F40: 断线重连辅助 Actions
    clearGameLogs,
    clearAnnouncementHistory,
    addToAnnouncementHistory,
    setHostAnnouncement
  }
})
