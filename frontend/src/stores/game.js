/**
 * Game store for managing werewolf game rooms and state
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

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
  
  const isHost = computed(() => {
    if (!currentRoom.value) return false
    return currentRoom.value.owner_id === myPlayerId.value
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
  
  const humanPlayers = computed(() =>
    players.value.filter((p) => !p.is_ai)
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
    if (!currentRoom.value || !isHost.value) return false
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
    if (currentPhase.value !== 'night') return false
    return !mySkillUsed.value
  })
  
  const canVote = computed(() => {
    if (isSpectator.value) return false
    if (!alivePlayers.value.find(p => p.id === myPlayerId.value)) return false
    if (currentPhase.value !== 'vote') return false
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
      participants.value = room.participants || []
      // 初始化玩家状态
      participants.value.forEach(p => {
        if (!playerStates.value[p.id]) {
          playerStates.value[p.id] = {
            is_alive: true,
            role_revealed: false,
            role_name: null,
            vote_count: 0
          }
        }
      })
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
    participants.value = participantsList
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
      if (state.phase) currentPhase.value = state.phase
      if (state.sub_phase) subPhase.value = state.sub_phase
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
    if (stateUpdate.current_phase || stateUpdate.phase) {
      currentPhase.value = stateUpdate.current_phase || stateUpdate.phase
    }
    if (stateUpdate.sub_phase !== undefined) {
      subPhase.value = stateUpdate.sub_phase
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
  
  function setMyRole(role) {
    myRole.value = role
  }
  
  function setIsSpectator(spectator) {
    isSpectator.value = spectator
  }
  
  function setCurrentTurn(playerId, turn) {
    currentTurn.value = playerId
    if (turn !== undefined) {
      turnNumber.value = turn
    }
  }
  
  function setPhase(phase, sub = null) {
    currentPhase.value = phase
    subPhase.value = sub
    
    // 重置回合状态
    if (phase === 'night') {
      mySkillUsed.value = false
    } else if (phase === 'vote') {
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
      phase_name: getPhaseDisplayName(currentPhase.value)
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
      phase_name: getPhaseDisplayName(currentPhase.value),
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
  
  function getPhaseDisplayName(phase) {
    switch (phase) {
      case 'night': return '夜晚'
      case 'day': return '白天'
      case 'discussion': return '讨论'
      case 'vote': return '投票'
      case 'result': return '结算'
      default: return phase
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
  }

  function reset() {
    leaveRoom()
    myPlayerId.value = localStorage.getItem('playerId') || null
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

  // 设置所有玩家信息（游戏结束后）
  function setAllPlayersInfo(players) {
    players.forEach(p => {
      const key = `seat_${p.seat_number}`
      if (playerStates.value[key]) {
        playerStates.value[key].role_name = p.role
        playerStates.value[key].team = p.team
        playerStates.value[key].role_revealed = true
      } else {
        playerStates.value[key] = {
          is_alive: p.is_alive,
          role_name: p.role,
          team: p.team,
          role_revealed: true,
          vote_count: 0
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
    voteResults,
    myVote,
    hasVoted,
    gameLogs,
    speakingPlayerId,
    speakOrder,
    mySkillTargets,
    mySkillUsed,

    // Computed
    isInRoom,
    roomCode,
    isHost,
    activeParticipants,
    players,
    spectators,
    humanPlayers,
    aiPlayers,
    alivePlayers,
    deadPlayers,
    alivePlayerIds,
    deadPlayerIds,
    canStartGame,
    isMyTurn,
    isGameInProgress,
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
    setCurrentTurn,
    setPhase,
    setAiThinking,
    setGameEnded,
    setPlayerDead,
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
    setMyTurn,
    addVote,
    setAllPlayersInfo
  }
})
