/**
 * Game store for managing game rooms and state
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useGameStore = defineStore('game', () => {
  // State
  const currentRoom = ref(null)
  const participants = ref([])
  const gameState = ref(null)
  const isLoading = ref(false)
  const error = ref(null)
  
  // Game state tracking
  const currentTurn = ref(null)
  const turnNumber = ref(0)
  const currentPhase = ref(null)
  const isAiThinking = ref(false)
  const aiThinkingPlayer = ref(null)
  const gameEnded = ref(false)
  const winner = ref(null)

  // Computed
  const isInRoom = computed(() => currentRoom.value !== null)
  const roomCode = computed(() => currentRoom.value?.code || null)
  const isHost = computed(() => {
    if (!currentRoom.value) return false
    const currentUserId = localStorage.getItem('userId') // TODO: Get from auth store
    return currentRoom.value.created_by === currentUserId
  })
  const activeParticipants = computed(() =>
    participants.value.filter((p) => p.is_active)
  )
  const humanPlayers = computed(() =>
    activeParticipants.value.filter((p) => !p.is_ai)
  )
  const aiPlayers = computed(() =>
    activeParticipants.value.filter((p) => p.is_ai)
  )
  const canStartGame = computed(() => {
    if (!currentRoom.value || !isHost.value) return false
    if (currentRoom.value.status !== 'Waiting') return false
    const playerCount = activeParticipants.value.length
    return playerCount >= currentRoom.value.min_players
  })
  const isMyTurn = computed(() => {
    const currentUserId = localStorage.getItem('userId')
    return currentTurn.value === currentUserId
  })
  const isGameInProgress = computed(() => {
    return currentRoom.value?.status === 'In Progress' && !gameEnded.value
  })

  // Actions
  function setCurrentRoom(room) {
    currentRoom.value = room
    if (room) {
      participants.value = room.participants || []
    }
  }

  function updateRoom(roomData) {
    if (currentRoom.value && currentRoom.value.code === roomData.code) {
      Object.assign(currentRoom.value, roomData)
    }
  }

  function setParticipants(participantsList) {
    participants.value = participantsList
  }

  function addParticipant(participant) {
    const existing = participants.value.find((p) => p.id === participant.id)
    if (!existing) {
      participants.value.push(participant)
    }
  }

  function removeParticipant(participantId) {
    const index = participants.value.findIndex((p) => p.id === participantId)
    if (index !== -1) {
      participants.value[index].is_active = false
      participants.value[index].left_at = new Date().toISOString()
    }
  }

  function setGameState(state) {
    gameState.value = state
  }

  function updateGameState(stateUpdate) {
    if (gameState.value) {
      Object.assign(gameState.value, stateUpdate)
    } else {
      gameState.value = stateUpdate
    }
    
    // Extract turn info if present
    if (stateUpdate.current_turn_player_id) {
      currentTurn.value = stateUpdate.current_turn_player_id
    }
    if (stateUpdate.turn_number !== undefined) {
      turnNumber.value = stateUpdate.turn_number
    }
    if (stateUpdate.current_phase) {
      currentPhase.value = stateUpdate.current_phase
    }
  }
  
  function setCurrentTurn(playerId, turn) {
    currentTurn.value = playerId
    if (turn !== undefined) {
      turnNumber.value = turn
    }
  }
  
  function setAiThinking(thinking, playerId = null) {
    isAiThinking.value = thinking
    aiThinkingPlayer.value = playerId
  }
  
  function setGameEnded(endedStatus, winnerId = null) {
    gameEnded.value = endedStatus
    winner.value = winnerId
    if (endedStatus && currentRoom.value) {
      currentRoom.value.status = 'Completed'
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
    isAiThinking.value = false
    aiThinkingPlayer.value = null
    gameEnded.value = false
    winner.value = null
  }

  function reset() {
    currentRoom.value = null
    participants.value = []
    gameState.value = null
    isLoading.value = false
    error.value = null
    currentTurn.value = null
    turnNumber.value = 0
    currentPhase.value = null
    isAiThinking.value = false
    aiThinkingPlayer.value = null
    gameEnded.value = false
    winner.value = null
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
    isAiThinking,
    aiThinkingPlayer,
    gameEnded,
    winner,

    // Computed
    isInRoom,
    roomCode,
    isHost,
    activeParticipants,
    humanPlayers,
    aiPlayers,
    canStartGame,
    isMyTurn,
    isGameInProgress,

    // Actions
    setCurrentRoom,
    updateRoom,
    setParticipants,
    addParticipant,
    removeParticipant,
    setGameState,
    updateGameState,
    setCurrentTurn,
    setAiThinking,
    setGameEnded,
    setLoading,
    setError,
    clearError,
    leaveRoom,
    reset
  }
})
