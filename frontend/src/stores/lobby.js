/**
 * Pinia store for lobby/room state management
 * 单人模式：管理房间状态和 AI 参与者
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useLobbyStore = defineStore('lobby', () => {
  // State
  const currentRoom = ref(null)
  const participants = ref([])

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
    return participants.value.filter(p => p.participant_type === 'ai' || p.is_ai)
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
  }

  function leaveRoom() {
    currentRoom.value = null
    participants.value = []
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
    
    // Getters
    participantCount,
    hasCapacity,
    sortedParticipants,
    aiAgents,
    roomCode,
    isWaiting,
    isInProgress,
    
    // Actions
    joinRoom,
    leaveRoom,
    addParticipant,
    removeParticipant,
    updateParticipant,
    updateRoomStatus,
    setRoomData,
    setParticipants
  }
})
