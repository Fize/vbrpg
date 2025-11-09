<template>
  <div class="game-room-lobby">
    <!-- Loading State -->
    <LoadingIndicator 
      v-if="loading" 
      text="加载房间信息中..." 
      variant="primary"
      size="large"
    />

    <!-- Content -->
    <el-container v-else>
      <el-header class="lobby-header">
        <div class="header-content">
          <el-button
            icon="ArrowLeft"
            @click="handleLeave"
            class="back-button"
          >
            <span class="button-text">离开房间</span>
          </el-button>
          <div class="room-info">
            <h2>{{ currentRoom?.game_type?.name || '游戏房间' }}</h2>
            <div class="room-code-section">
              <span class="room-code-label">房间代码:</span>
              <el-tag class="room-code" size="large" type="success">
                {{ roomCode }}
              </el-tag>
              <el-button
                icon="DocumentCopy"
                @click="copyRoomCode"
                text
                circle
                class="copy-button"
              />
            </div>
          </div>
        </div>
      </el-header>

      <el-main class="lobby-main">
        <el-row :gutter="20" class="content-row">
          <!-- Left: Room Status -->
          <el-col :xs="24" :sm="24" :md="12" :lg="12" class="status-col">
            <el-card shadow="hover" class="status-card">
              <template #header>
                <div class="card-header">
                  <span>房间状态</span>
                  <el-tag
                    :type="statusTagType"
                    effect="dark"
                  >
                    {{ currentRoom?.status || 'Waiting' }}
                  </el-tag>
                </div>
              </template>

              <el-descriptions :column="1" border size="default">
                <el-descriptions-item label="游戏类型">
                  {{ currentRoom?.game_type?.name }}
                </el-descriptions-item>
                <el-descriptions-item label="玩家人数">
                  {{ activeParticipants.length }} / {{ currentRoom?.max_players }}
                </el-descriptions-item>
                <el-descriptions-item label="最少人数">
                  {{ currentRoom?.min_players }}
                </el-descriptions-item>
                <el-descriptions-item label="房主">
                  {{ isHost ? '你' : '其他玩家' }}
                </el-descriptions-item>
              </el-descriptions>

              <div v-if="isHost && canStartGame" class="start-section">
                <el-alert
                  type="success"
                  :closable="false"
                  show-icon
                  class="alert-section"
                >
                  <template #title>
                    准备就绪！点击开始游戏
                  </template>
                </el-alert>
                <el-button
                  type="primary"
                  size="large"
                  :loading="starting"
                  @click="handleStartGame"
                  class="start-button"
                >
                  开始游戏
                </el-button>
              </div>

              <el-alert
                v-else-if="isHost"
                type="info"
                :closable="false"
                show-icon
                class="waiting-alert"
              >
                <template #title>
                  需要至少 {{ currentRoom?.min_players }} 名玩家才能开始
                </template>
              </el-alert>

              <el-alert
                v-else
                type="info"
                :closable="false"
                show-icon
                class="waiting-alert"
              >
                <template #title>
                  等待房主开始游戏...
                </template>
              </el-alert>
            </el-card>
          </el-col>

          <!-- Right: Player List -->
          <el-col :xs="24" :sm="24" :md="12" :lg="12" class="players-col">
            <PlayerList :participants="activeParticipants" />
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useClipboard } from '@vueuse/core'
import { roomsApi } from '@/services/api'
import { useGameStore } from '@/stores/game'
import websocketService from '@/services/websocket'
import PlayerList from '@/components/PlayerList.vue'
import LoadingIndicator from '@/components/LoadingIndicator.vue'

const route = useRoute()
const router = useRouter()
const gameStore = useGameStore()
const { copy } = useClipboard()

// State
const starting = ref(false)
const loading = ref(false)
const roomCode = computed(() => route.params.code)

// Computed
const currentRoom = computed(() => gameStore.currentRoom)
const activeParticipants = computed(() => gameStore.activeParticipants)
const isHost = computed(() => gameStore.isHost)
const canStartGame = computed(() => gameStore.canStartGame)

const statusTagType = computed(() => {
  const status = currentRoom.value?.status
  if (status === 'Waiting') return 'info'
  if (status === 'In Progress') return 'success'
  if (status === 'Completed') return 'warning'
  return 'info'
})

// Methods
async function loadRoom() {
  try {
    loading.value = true
    const roomData = await roomsApi.getRoom(roomCode.value)
    gameStore.setCurrentRoom(roomData)
    
    // Join WebSocket room
    const playerId = localStorage.getItem('userId') || 'temp-user-id-123'
    websocketService.joinRoom(roomCode.value, playerId)
  } catch (error) {
    console.error('Failed to load room:', error)
    ElMessage.error('加载房间失败')
    router.push('/games')
  } finally {
    loading.value = false
  }
}

function copyRoomCode() {
  copy(roomCode.value)
  ElMessage.success('房间代码已复制到剪贴板')
}

async function handleLeave() {
  try {
    await ElMessageBox.confirm(
      '确定要离开房间吗？',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const playerId = localStorage.getItem('userId') || 'temp-user-id-123'
    websocketService.leaveRoom(roomCode.value, playerId)
    
    await roomsApi.leaveRoom(roomCode.value)
    gameStore.leaveRoom()
    
    router.push('/games')
  } catch (error) {
    if (error === 'cancel') return
    console.error('Failed to leave room:', error)
    ElMessage.error('离开房间失败')
  }
}

async function handleStartGame() {
  try {
    starting.value = true
    const updatedRoom = await roomsApi.startGame(roomCode.value)
    gameStore.updateRoom(updatedRoom)
    ElMessage.success('游戏已开始！')
  } catch (error) {
    console.error('Failed to start game:', error)
    ElMessage.error('开始游戏失败')
  } finally {
    starting.value = false
  }
}

// WebSocket event handlers
function setupWebSocketListeners() {
  websocketService.connect()
  
  websocketService.onPlayerJoined((data) => {
    console.log('Player joined:', data)
    gameStore.addParticipant(data.player)
    ElMessage.info(`${data.player.name} 加入了房间`)
  })

  websocketService.onPlayerLeft((data) => {
    console.log('Player left:', data)
    gameStore.removeParticipant(data.player_id)
    ElMessage.warning(`${data.player_name} 离开了房间`)
  })

  websocketService.onGameStarted((data) => {
    console.log('Game started:', data)
    gameStore.updateRoom({ status: 'In Progress', started_at: data.started_at })
    
    // Initialize game state if provided
    if (data.initial_state) {
      gameStore.setGameState(data.initial_state)
    }
    
    ElMessage.success('游戏开始了！')
    
    // Navigate to game board
    router.push(`/game/${roomCode.value}`)
  })

  websocketService.onError((error) => {
    console.error('WebSocket error:', error)
    ElMessage.error(error.message || '连接错误')
  })
}

function cleanupWebSocketListeners() {
  websocketService.offRoomEvents()
  const playerId = localStorage.getItem('userId') || 'temp-user-id-123'
  websocketService.leaveRoom(roomCode.value, playerId)
}

onMounted(() => {
  setupWebSocketListeners()
  loadRoom()
})

onBeforeUnmount(() => {
  cleanupWebSocketListeners()
})
</script>

<style scoped>
.game-room-lobby {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding-bottom: 20px;
}

.lobby-header {
  background: white;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  padding: 16px 20px;
  height: auto;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
  max-width: 1400px;
  margin: 0 auto;
}

.back-button {
  flex-shrink: 0;
}

.room-info {
  flex: 1;
  text-align: center;
  min-width: 0;
}

.room-info h2 {
  margin: 0 0 8px 0;
  color: #303133;
  font-size: 24px;
  font-weight: 600;
}

.room-code-section {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}

.room-code-label {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}

.room-code {
  font-size: 20px;
  font-weight: bold;
  font-family: monospace;
  padding: 8px 16px;
  letter-spacing: 2px;
}

.copy-button {
  flex-shrink: 0;
}

.lobby-main {
  padding: 24px 20px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.content-row {
  width: 100%;
}

.status-col,
.players-col {
  margin-bottom: 20px;
}

.status-card {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: 16px;
}

.start-section {
  margin-top: 20px;
}

.alert-section {
  margin-bottom: 16px;
}

.start-button {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
}

.waiting-alert {
  margin-top: 20px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .lobby-header {
    padding: 12px 16px;
  }
  
  .header-content {
    gap: 12px;
  }
  
  .back-button .button-text {
    display: none;
  }
  
  .room-info h2 {
    font-size: 20px;
  }
  
  .room-code {
    font-size: 18px;
    padding: 6px 12px;
  }
  
  .lobby-main {
    padding: 16px 12px;
  }
  
  .status-col,
  .players-col {
    margin-bottom: 16px;
  }
  
  .card-header {
    font-size: 14px;
  }
}

@media (max-width: 480px) {
  .lobby-header {
    padding: 10px 12px;
  }
  
  .room-info h2 {
    font-size: 18px;
    margin-bottom: 6px;
  }
  
  .room-code-section {
    flex-direction: column;
    gap: 6px;
  }
  
  .room-code {
    font-size: 16px;
    padding: 6px 10px;
  }
  
  .lobby-main {
    padding: 12px 8px;
  }
}

@media (min-width: 768px) and (max-width: 991px) {
  .content-row {
    display: flex;
    flex-direction: column;
  }
  
  .status-col,
  .players-col {
    max-width: 100%;
  }
}
</style>
