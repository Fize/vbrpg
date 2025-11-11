<template>
  <div class="lobby-view">
    <!-- Loading State -->
    <div v-if="isLoading" class="loading-indicator">
      <div class="spinner"></div>
      <p>加载房间信息...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="errorMessage" class="error-state">
      <p class="error-message">{{ errorMessage }}</p>
      <button @click="goHome" class="back-button">返回主页</button>
    </div>

    <!-- Main Lobby Content -->
    <div v-else-if="currentRoom" class="lobby-content">
      <!-- Room Info Card -->
      <div class="room-info-card">
        <div class="room-header">
          <h1>房间大厅</h1>
          <span class="room-status" :class="statusClass">{{ statusText }}</span>
        </div>

        <div class="room-details">
          <div class="detail-item">
            <label>房间代码</label>
            <span class="room-code">{{ currentRoom.code }}</span>
          </div>

          <div class="detail-item">
            <label>游戏类型</label>
            <span>{{ gameTypeName }}</span>
          </div>

          <div class="detail-item">
            <label>玩家人数</label>
            <span>{{ currentRoom.current_participant_count }}/{{ currentRoom.max_players }}</span>
          </div>
        </div>
      </div>

      <!-- Participants List -->
      <div class="participants-section">
        <h2>玩家列表</h2>

        <div v-if="sortedParticipants.length === 0" class="empty-state">
          <p>暂无玩家</p>
        </div>

        <div v-else class="participants-list">
          <div
            v-for="participant in sortedParticipants"
            :key="participant.id"
            class="participant-item"
          >
            <div class="participant-info">
              <span class="participant-name">{{ participant.name }}</span>
              
              <div class="participant-badges">
                <span v-if="participant.is_owner" class="owner-badge">房主</span>
                <span v-if="participant.participant_type === 'ai'" class="ai-badge">AI</span>
              </div>
            </div>

            <div class="participant-meta">
              <span v-if="participant.join_timestamp" class="join-time">
                {{ formatJoinTime(participant.join_timestamp) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="actions">
        <button
          v-if="canLeaveRoom"
          @click="handleLeaveRoom"
          :disabled="isLeavingRoom"
          class="leave-button"
        >
          {{ isLeavingRoom ? '离开中...' : '离开房间' }}
        </button>

        <button
          v-if="isOwner && isWaiting"
          @click="handleStartGame"
          :disabled="!canStartGame"
          class="start-button"
        >
          开始游戏
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useLobbyStore } from '@/stores/lobby'
import { roomsApi } from '@/services/api'
import websocket from '@/services/websocket'

const router = useRouter()
const route = useRoute()
const lobbyStore = useLobbyStore()

// Component state
const isLoading = ref(true)
const isLeavingRoom = ref(false)
const errorMessage = ref('')

// Computed properties from store
const currentRoom = computed(() => lobbyStore.currentRoom)
const sortedParticipants = computed(() => lobbyStore.sortedParticipants)
const isOwner = computed(() => lobbyStore.isOwner)
const isWaiting = computed(() => lobbyStore.isWaiting)
const participantCount = computed(() => lobbyStore.participantCount)

// UI computed properties
const statusClass = computed(() => {
  if (!currentRoom.value) return ''
  return currentRoom.value.status === 'Waiting' ? 'status-waiting' : 'status-in-progress'
})

const statusText = computed(() => {
  if (!currentRoom.value) return ''
  const statusMap = {
    'Waiting': '等待中',
    'In Progress': '进行中',
    'Completed': '已完成',
    'Dissolved': '已解散'
  }
  return statusMap[currentRoom.value.status] || currentRoom.value.status
})

const gameTypeName = computed(() => {
  if (!currentRoom.value) return ''
  const typeMap = {
    'crime-scene': '犯罪现场'
  }
  return typeMap[currentRoom.value.game_type] || currentRoom.value.game_type
})

const canLeaveRoom = computed(() => {
  return currentRoom.value && currentRoom.value.status === 'Waiting'
})

const canStartGame = computed(() => {
  if (!currentRoom.value) return false
  const count = currentRoom.value.current_participant_count
  const min = currentRoom.value.min_players || 2
  return count >= min
})

// Methods
const loadRoomData = async () => {
  const roomCode = route.params.code
  if (!roomCode) {
    errorMessage.value = '房间代码无效'
    isLoading.value = false
    return
  }

  try {
    isLoading.value = true
    const response = await roomsApi.getRoom(roomCode)
    
    // Update lobby store with room data
    lobbyStore.joinRoom({
      room: response.room || response,
      participants: response.participants || [],
      is_owner: response.is_owner || false
    })

    errorMessage.value = ''
  } catch (error) {
    if (error.response?.status === 404) {
      errorMessage.value = '房间不存在'
    } else {
      errorMessage.value = '加载房间信息失败'
    }
    console.error('Failed to load room:', error)
  } finally {
    isLoading.value = false
  }
}

const handleLeaveRoom = async () => {
  if (isLeavingRoom.value || !currentRoom.value) return

  try {
    isLeavingRoom.value = true
    await roomsApi.leaveRoom(currentRoom.value.code)
    
    // Clear lobby store
    lobbyStore.leaveRoom()
    
    // Navigate to home
    router.push({ name: 'home' })
  } catch (error) {
    console.error('Failed to leave room:', error)
    errorMessage.value = '离开房间失败，请重试'
  } finally {
    isLeavingRoom.value = false
  }
}

const handleStartGame = async () => {
  if (!currentRoom.value) return

  try {
    await roomsApi.startGame(currentRoom.value.code)
    // Game will start, status will be updated via WebSocket
  } catch (error) {
    console.error('Failed to start game:', error)
    errorMessage.value = '开始游戏失败'
  }
}

const goHome = () => {
  router.push({ name: 'home' })
}

const formatJoinTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diff = Math.floor((now - date) / 1000 / 60) // minutes
  
  if (diff < 1) return '刚刚加入'
  if (diff < 60) return `${diff}分钟前加入`
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

// WebSocket event handlers
const setupWebSocketListeners = () => {
  const roomCode = route.params.code
  if (!roomCode) return

  // Join lobby WebSocket room
  websocket.connect()
  websocket.joinLobby(roomCode)

  // Set up reconnection handler to sync state
  websocket.onReconnect(async ({ roomCode }) => {
    console.log('Reconnected, syncing lobby state for room:', roomCode)
    try {
      const response = await roomsApi.getRoom(roomCode)
      
      // Check if room still exists and is valid
      if (response.room.status === 'Dissolved') {
        console.log('Room was dissolved during disconnect')
        lobbyStore.leaveRoom()
        router.push({ name: 'home' })
        return
      }
      
      // Sync state from API
      lobbyStore.joinRoom({
        room: response.room,
        participants: response.participants || [],
        is_owner: response.is_owner || false
      })
      
      console.log('Lobby state synced successfully')
    } catch (error) {
      if (error.response?.status === 404) {
        console.log('Room no longer exists')
        lobbyStore.leaveRoom()
        router.push({ name: 'home' })
      } else {
        console.error('Failed to sync lobby state:', error)
        errorMessage.value = '重新连接失败，请刷新页面'
      }
    }
  })

  // Player joined event
  websocket.onPlayerJoined((data) => {
    console.log('Player joined:', data)
    if (data.player) {
      lobbyStore.addParticipant(data.player)
    }
  })

  // Player left event
  websocket.onPlayerLeft((data) => {
    console.log('Player left:', data)
    if (data.player_id) {
      lobbyStore.removeParticipant(data.player_id)
    }
  })

  // AI agent added event
  websocket.onAIAgentAdded((data) => {
    console.log('AI agent added:', data)
    if (data.ai_agent) {
      lobbyStore.addParticipant(data.ai_agent)
    }
  })

  // AI agent removed event
  websocket.onAIAgentRemoved((data) => {
    console.log('AI agent removed:', data)
    if (data.ai_agent_id) {
      lobbyStore.removeParticipant(data.ai_agent_id)
    }
  })

  // Ownership transferred event
  websocket.onOwnershipTransferred((data) => {
    console.log('Ownership transferred:', data)
    if (data.new_owner_id) {
      lobbyStore.transferOwnership(data.new_owner_id)
    }
  })

  // Room dissolved event
  websocket.onRoomDissolved(() => {
    console.log('Room dissolved, navigating to home')
    lobbyStore.leaveRoom()
    router.push({ name: 'home' })
  })

  // Lobby joined confirmation
  websocket.onLobbyJoined((data) => {
    console.log('Successfully joined lobby:', data)
  })
}

const cleanupWebSocketListeners = () => {
  const roomCode = route.params.code
  if (roomCode) {
    websocket.leaveLobby(roomCode)
  }
  websocket.offLobbyEvents()
}

// Lifecycle
onMounted(() => {
  loadRoomData().then(() => {
    // Set up WebSocket listeners after room data is loaded
    setupWebSocketListeners()
  })
})

onBeforeUnmount(() => {
  // Clean up WebSocket listeners
  cleanupWebSocketListeners()
})
</script>

<style scoped>
.lobby-view {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
}

.loading-indicator {
  text-align: center;
  padding: 4rem 2rem;
}

.spinner {
  width: 48px;
  height: 48px;
  margin: 0 auto 1rem;
  border: 4px solid rgba(0, 0, 0, 0.1);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-state {
  text-align: center;
  padding: 4rem 2rem;
}

.error-message {
  color: #c33;
  margin-bottom: 1.5rem;
  font-size: 1.1rem;
}

.back-button {
  padding: 0.75rem 2rem;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.lobby-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.room-info-card {
  background: var(--color-background-soft);
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.room-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.room-header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.room-status {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 600;
}

.status-waiting {
  background: #e8f5e9;
  color: #2e7d32;
}

.status-in-progress {
  background: #fff3e0;
  color: #f57c00;
}

.room-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-item label {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.room-code {
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  color: var(--color-primary);
}

.participants-section {
  background: var(--color-background-soft);
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.participants-section h2 {
  margin: 0 0 1rem;
  font-size: 1.25rem;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: var(--color-text-secondary);
}

.participants-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.participant-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--color-background);
  border-radius: 4px;
  border: 1px solid var(--color-border);
}

.participant-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.participant-name {
  font-weight: 500;
}

.participant-badges {
  display: flex;
  gap: 0.5rem;
}

.owner-badge,
.ai-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 3px;
  font-size: 0.75rem;
  font-weight: 600;
}

.owner-badge {
  background: #fff3e0;
  color: #f57c00;
}

.ai-badge {
  background: #e3f2fd;
  color: #1976d2;
}

.participant-meta {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.leave-button,
.start-button {
  padding: 0.75rem 2rem;
  font-size: 1rem;
  font-weight: 600;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
}

.leave-button {
  background: #f5f5f5;
  color: #666;
}

.leave-button:hover:not(:disabled) {
  background: #e0e0e0;
}

.start-button {
  background: var(--color-primary);
  color: white;
}

.start-button:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.leave-button:disabled,
.start-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
