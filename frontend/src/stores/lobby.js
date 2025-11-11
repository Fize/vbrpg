/**
 * Pinia store for lobby/room state management
 * Handles room join/leave, participant updates, and ownership transfer
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useLobbyStore = defineStore('lobby', () => {
  // State
  const currentRoom = ref(null)
  const participants = ref([])
  const isOwner = ref(false)

  // Getters
  const participantCount = computed(() => {
    return participants.value.length
  })

  const hasCapacity = computed(() => {
    if (!currentRoom.value) return false
    return currentRoom.value.current_participant_count < currentRoom.value.max_players
  })

  const sortedParticipants = computed(() => {
    return [...participants.value].sort((a, b) => {
      if (!a.join_timestamp || !b.join_timestamp) return 0
      return new Date(a.join_timestamp) - new Date(b.join_timestamp)
    })
  })

  const aiAgents = computed(() => {
    return participants.value.filter(p => p.participant_type === 'ai')
  })

  const humanPlayers = computed(() => {
    return participants.value.filter(p => p.participant_type === 'human')
  })

  const roomCode = computed(() => {
    return currentRoom.value?.code || null
  })

  const isWaiting = computed(() => {
    return currentRoom.value?.status === 'Waiting'
  })

  const isInProgress = computed(() => {
    return currentRoom.value?.status === 'In Progress'
  })

  // Actions
  function joinRoom(roomData) {
    currentRoom.value = roomData.room
    participants.value = roomData.participants || []
    isOwner.value = roomData.is_owner || false
  }

  function leaveRoom() {
    currentRoom.value = null
    participants.value = []
    isOwner.value = false
  }

  function addParticipant(participant) {
    // Check if participant already exists
    const exists = participants.value.some(p => p.id === participant.id)
    if (!exists) {
      participants.value.push(participant)
      
      // Update room participant count if room exists
      if (currentRoom.value) {
        currentRoom.value.current_participant_count = participants.value.length
      }
    }
  }

  function removeParticipant(participantId) {
    const index = participants.value.findIndex(p => p.id === participantId)
    if (index !== -1) {
      participants.value.splice(index, 1)
      
      // Update room participant count if room exists
      if (currentRoom.value) {
        currentRoom.value.current_participant_count = participants.value.length
      }
    }
  }

  function updateParticipant(participantId, updates) {
    const participant = participants.value.find(p => p.id === participantId)
    if (participant) {
      Object.assign(participant, updates)
    }
  }

  function transferOwnership(newOwnerId, currentPlayerId = null) {
    // Update all participants' is_owner flags
    participants.value.forEach(p => {
      p.is_owner = (p.id === newOwnerId)
    })

    // Update room owner_id if room exists
    if (currentRoom.value) {
      currentRoom.value.owner_id = newOwnerId
    }

    // Update isOwner flag if this affects current player
    if (currentPlayerId) {
      isOwner.value = (newOwnerId === currentPlayerId)
    }
  }

  function updateRoomStatus(status) {
    if (currentRoom.value) {
      currentRoom.value.status = status
    }
  }

  function setRoomData(room) {
    currentRoom.value = room
  }

  function setParticipants(participantsList) {
    participants.value = participantsList
  }

  return {
    // State
    currentRoom,
    participants,
    isOwner,
    
    // Getters
    participantCount,
    hasCapacity,
    sortedParticipants,
    aiAgents,
    humanPlayers,
    roomCode,
    isWaiting,
    isInProgress,
    
    // Actions
    joinRoom,
    leaveRoom,
    addParticipant,
    removeParticipant,
    updateParticipant,
    transferOwnership,
    updateRoomStatus,
    setRoomData,
    setParticipants
  }
})
