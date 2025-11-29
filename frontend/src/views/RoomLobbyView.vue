<template>
  <div class="room-lobby-view">
    <div class="page-header">
      <el-button text :icon="ArrowLeft" @click="goBack">返回大厅</el-button>
      <div class="room-code-info">
        <span class="label">房间号</span>
        <span class="code">{{ roomCode }}</span>
        <el-button text :icon="CopyDocument" @click="copyRoomCode">复制</el-button>
      </div>
    </div>
    
    <div class="room-container" v-loading="loading">
      <!-- 房间信息 -->
      <div class="room-info-section">
        <div class="game-info">
          <img 
            src="@/assets/images/werewolf/werewolf-across.jpeg" 
            alt="狼人杀"
            class="game-cover"
            @error="handleImageError"
          />
          <div class="game-details">
            <h2 class="game-name">狼人杀</h2>
            <p class="game-desc">标准10人局</p>
            <el-tag :type="statusTagType" size="large">{{ statusText }}</el-tag>
          </div>
        </div>
      </div>
      
      <div class="main-content">
        <!-- 参与者列表 -->
        <div class="participants-section">
          <ParticipantList
            title="玩家列表"
            :participants="players"
            :max-count="10"
            :current-player-id="currentPlayerId"
            :is-host="isHost"
            :show-actions="true"
            @remove="handleRemoveParticipant"
          />
          
          <div v-if="spectators.length > 0" class="spectators-list">
            <ParticipantList
              title="观战列表"
              :participants="spectators"
              :max-count="99"
              :show-empty-slots="false"
            />
          </div>
        </div>
        
        <!-- 控制面板 -->
        <div class="control-section">
          <!-- AI 控制（房主） -->
          <div v-if="isHost" class="ai-control">
            <h3 class="section-title">AI 控制</h3>
            <div class="ai-actions">
              <el-button 
                :disabled="players.length >= 10"
                @click="handleAddAI"
                :loading="addingAI"
              >
                <el-icon><Plus /></el-icon>
                添加 AI
              </el-button>
              <span class="ai-count">
                AI 玩家: {{ aiCount }} / {{ 10 - humanCount }}
              </span>
            </div>
          </div>
          
          <!-- 操作按钮 -->
          <div class="action-buttons">
            <!-- 单人模式：移除“离开房间”按钮，用户可以直接返回大厅 -->
            
            <el-button
              v-if="isHost"
              type="primary"
              size="large"
              :disabled="!canStartGame"
              :loading="starting"
              @click="handleStartGame"
            >
              开始游戏
            </el-button>
            
            <el-button v-if="isHost" size="large" type="danger" @click="handleDisbandRoom">
              解散房间
            </el-button>
          </div>
          
          <!-- 提示信息 -->
          <div class="tips-section">
            <el-alert
              v-if="!canStartGame && isHost"
              :title="startGameTip"
              type="info"
              show-icon
              :closable="false"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, CopyDocument, Plus } from '@element-plus/icons-vue'
import { roomsApi } from '@/services/api'
import { useSocketStore } from '@/stores/socket'
import ParticipantList from '@/components/werewolf/ParticipantList.vue'

const route = useRoute()
const router = useRouter()
const socketStore = useSocketStore()

// 房间信息
const roomCode = computed(() => route.params.code)
const room = ref(null)
const loading = ref(true)
const starting = ref(false)
const addingAI = ref(false)

// 当前玩家信息（从 store 或 localStorage 获取）
const currentPlayerId = ref(localStorage.getItem('playerId') || null)

// 计算属性
const players = computed(() => {
  if (!room.value?.participants) return []
  return room.value.participants.filter(p => !p.is_spectator)
})

const spectators = computed(() => {
  if (!room.value?.participants) return []
  return room.value.participants.filter(p => p.is_spectator)
})

const aiCount = computed(() => players.value.filter(p => p.is_ai).length)
const humanCount = computed(() => players.value.filter(p => !p.is_ai).length)

const isHost = computed(() => {
  return room.value?.owner_id === currentPlayerId.value
})

const canStartGame = computed(() => {
  return players.value.length === 10
})

const statusText = computed(() => {
  if (!room.value) return '加载中'
  switch (room.value.status) {
    case 'Waiting': return `等待中 (${players.value.length}/10)`
    case 'In Progress': return '游戏中'
    case 'Completed': return '已结束'
    default: return room.value.status
  }
})

const statusTagType = computed(() => {
  if (!room.value) return 'info'
  switch (room.value.status) {
    case 'Waiting': return 'warning'
    case 'In Progress': return 'success'
    case 'Completed': return ''
    default: return 'info'
  }
})

const startGameTip = computed(() => {
  const needed = 10 - players.value.length
  if (needed > 0) {
    return `还需要 ${needed} 名玩家才能开始游戏，可以添加 AI 玩家`
  }
  return ''
})

// 加载房间信息
async function loadRoom() {
  loading.value = true
  try {
    const data = await roomsApi.getRoom(roomCode.value)
    room.value = data
    
    // 检查游戏是否已开始
    if (data.status === 'In Progress') {
      router.replace(`/game/${roomCode.value}`)
    }
  } catch (err) {
    console.error('加载房间失败:', err)
    ElMessage.error('房间不存在或已失效')
    router.push('/lobby')
  } finally {
    loading.value = false
  }
}

// WebSocket 事件处理
function setupSocketListeners() {
  socketStore.on('room_update', handleRoomUpdate)
  socketStore.on('game_started', handleGameStarted)
  socketStore.on('player_joined', handlePlayerJoined)
  socketStore.on('player_left', handlePlayerLeft)
}

function handleRoomUpdate(data) {
  if (data.room_code === roomCode.value) {
    room.value = { ...room.value, ...data }
  }
}

function handleGameStarted(data) {
  if (data.room_code === roomCode.value) {
    ElMessage.success('游戏开始！')
    router.push(`/game/${roomCode.value}`)
  }
}

function handlePlayerJoined(data) {
  if (data.room_code === roomCode.value) {
    loadRoom() // 重新加载房间信息
  }
}

function handlePlayerLeft(data) {
  if (data.room_code === roomCode.value) {
    loadRoom()
  }
}

// 操作方法
function goBack() {
  router.push('/lobby')
}

async function copyRoomCode() {
  try {
    await navigator.clipboard.writeText(roomCode.value)
    ElMessage.success('房间号已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

function handleImageError(e) {
  e.target.style.display = 'none'
}

async function handleAddAI() {
  addingAI.value = true
  try {
    await roomsApi.addAIAgent(roomCode.value)
    await loadRoom()
    ElMessage.success('AI 玩家已添加')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '添加 AI 失败')
  } finally {
    addingAI.value = false
  }
}

async function handleRemoveParticipant(participant) {
  if (!participant.is_ai) return
  
  try {
    await roomsApi.removeAIAgent(roomCode.value, participant.id)
    await loadRoom()
    ElMessage.success('AI 玩家已移除')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '移除失败')
  }
}

async function handleStartGame() {
  starting.value = true
  try {
    await roomsApi.startGame(roomCode.value)
    // 游戏开始事件会通过 WebSocket 触发跳转
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '启动游戏失败')
  } finally {
    starting.value = false
  }
}

// 单人模式：移除 handleLeaveRoom，用户可直接使用“返回大厅”按钮

async function handleDisbandRoom() {
  try {
    await ElMessageBox.confirm('确定要解散房间吗？所有玩家将被移出。', '警告', {
      type: 'warning',
      confirmButtonText: '确定解散',
      cancelButtonText: '取消'
    })
    // TODO: 添加解散房间 API
    ElMessage.success('房间已解散')
    router.push('/lobby')
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('解散房间失败')
    }
  }
}

onMounted(() => {
  loadRoom()
  setupSocketListeners()
  
  // 连接 WebSocket（如果还没连接）
  if (!socketStore.isConnected) {
    socketStore.connect()
  }
})

onUnmounted(() => {
  socketStore.off('room_update', handleRoomUpdate)
  socketStore.off('game_started', handleGameStarted)
  socketStore.off('player_joined', handlePlayerJoined)
  socketStore.off('player_left', handlePlayerLeft)
})
</script>

<style scoped>
.room-lobby-view {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.page-header {
  max-width: 1000px;
  margin: 0 auto 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header .el-button {
  color: white;
}

.room-code-info {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.2);
  padding: 8px 16px;
  border-radius: 8px;
}

.room-code-info .label {
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
}

.room-code-info .code {
  color: white;
  font-size: 18px;
  font-weight: 600;
  font-family: monospace;
  letter-spacing: 2px;
}

.room-container {
  max-width: 1000px;
  margin: 0 auto;
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.room-info-section {
  margin-bottom: 24px;
}

.game-info {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 12px;
}

.game-cover {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 8px;
}

.game-details {
  flex: 1;
}

.game-name {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 4px;
}

.game-desc {
  font-size: 14px;
  color: #909399;
  margin: 0 0 8px;
}

.main-content {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 24px;
}

.participants-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.control-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 12px;
}

.ai-control {
  background: #f5f7fa;
  border-radius: 12px;
  padding: 16px;
}

.ai-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ai-count {
  font-size: 14px;
  color: #909399;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tips-section .el-alert {
  border-radius: 8px;
}

/* 响应式 */
@media (max-width: 768px) {
  .room-lobby-view {
    padding: 12px;
  }
  
  .page-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .room-container {
    padding: 16px;
  }
  
  .main-content {
    grid-template-columns: 1fr;
  }
  
  .game-info {
    flex-direction: column;
    text-align: center;
  }
}
</style>
