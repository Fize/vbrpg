<template>
  <div class="room-lobby-view">
    <!-- 顶部导航 -->
    <div class="page-header">
      <el-button class="back-btn" text :icon="ArrowLeft" @click="goBack">返回大厅</el-button>
      <div class="room-code-info">
        <span class="label">房间号</span>
        <span class="code">{{ roomCode }}</span>
        <el-button class="copy-btn" text :icon="CopyDocument" @click="copyRoomCode" />
      </div>
    </div>
    
    <div class="room-container" v-loading="loading">
      <!-- 左侧：游戏信息 + 玩家列表 -->
      <div class="left-panel">
        <!-- 游戏信息卡片 -->
        <div class="game-card">
          <div class="game-cover-wrapper">
            <img 
              src="@/assets/images/werewolf/werewolf-across.jpeg" 
              alt="狼人杀"
              class="game-cover"
              @error="handleImageError"
            />
            <div class="game-overlay">
              <el-tag :type="statusTagType" size="large">{{ statusText }}</el-tag>
            </div>
          </div>
          <div class="game-details">
            <h2 class="game-name">狼人杀</h2>
            <p class="game-desc">经典10人局 · AI对战模式</p>
          </div>
        </div>
        
        <!-- 玩家列表 -->
        <div class="players-section">
          <ParticipantList
            title="玩家列表"
            :participants="players"
            :max-count="10"
            :current-player-id="currentPlayerId"
            :is-host="isHost"
            :show-actions="false"
            :show-empty-slots="false"
          />
        </div>
      </div>
      
      <!-- 右侧：控制面板 -->
      <div class="right-panel">
        <div class="control-panel">
          <h3 class="panel-title">
            <span class="title-icon">◆</span>
            游戏控制
          </h3>
          
          <!-- 状态显示 -->
          <div class="status-display">
            <div class="status-item">
              <span class="status-label">玩家数量</span>
              <span class="status-value" :class="{ 'ready': players.length === 10 }">
                {{ players.length }} / 10
              </span>
            </div>
            <div class="status-item">
              <span class="status-label">游戏状态</span>
              <span class="status-value status-waiting">准备就绪</span>
            </div>
          </div>
          
          <!-- 操作按钮 -->
          <div class="action-buttons">
            <el-button
              class="start-btn"
              type="primary"
              size="large"
              :disabled="!canStartGame"
              :loading="starting"
              @click="handleStartGame"
            >
              <span class="btn-icon">▶</span>
              开始游戏
            </el-button>
            
            <el-button 
              class="disband-btn" 
              size="large" 
              @click="handleDisbandRoom"
            >
              解散房间
            </el-button>
          </div>
          
          <!-- 提示信息 -->
          <div v-if="!canStartGame" class="tips-section">
            <div class="tip-content">
              <el-icon><InfoFilled /></el-icon>
              <span>{{ startGameTip }}</span>
            </div>
          </div>
        </div>
        
        <!-- 游戏说明 -->
        <div class="game-rules">
          <h3 class="panel-title">
            <span class="title-icon">◆</span>
            游戏说明
          </h3>
          <ul class="rules-list">
            <li>狼人在夜晚猎杀村民</li>
            <li>村民在白天投票处决可疑者</li>
            <li>特殊角色拥有特殊能力</li>
            <li>找出所有狼人即可获胜</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, CopyDocument, InfoFilled } from '@element-plus/icons-vue'
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

// 当前玩家信息（从 store 或 localStorage 获取）
const currentPlayerId = ref(localStorage.getItem('playerId') || null)

// 映射参与者数据，将嵌套的 player 信息扁平化
const mapParticipant = (p) => ({
  id: p.id,
  username: p.player?.username || p.username,
  name: p.player?.username || p.name,
  is_ai: p.is_ai_agent || p.is_ai,
  is_spectator: p.is_spectator,
  is_host: p.is_owner || p.is_host,
  is_online: true, // 单人模式下 AI 总是在线
  joined_at: p.joined_at
})

// 计算属性
const players = computed(() => {
  if (!room.value?.participants) return []
  return room.value.participants
    .filter(p => !p.is_spectator)
    .map(mapParticipant)
})

const spectators = computed(() => {
  if (!room.value?.participants) return []
  return room.value.participants
    .filter(p => p.is_spectator)
    .map(mapParticipant)
})

const canStartGame = computed(() => {
  return players.value.length === 10
})

// 单人模式下用户始终是"房主"（观战者但可控制游戏）
const isHost = computed(() => true)

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

async function handleStartGame() {
  starting.value = true
  try {
    const response = await roomsApi.startGame(roomCode.value)
    // 成功后直接跳转到游戏页面
    ElMessage.success('游戏开始！')
    router.push(`/game/${roomCode.value}`)
  } catch (err) {
    // 如果是 409 冲突（游戏已开始），也跳转到游戏页面
    if (err.response?.status === 409) {
      ElMessage.info('游戏已开始，正在进入...')
      router.push(`/game/${roomCode.value}`)
    } else {
      ElMessage.error(err.response?.data?.detail || '启动游戏失败')
    }
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
/* ===== 赛博朋克主题变量 ===== */
.room-lobby-view {
  --cyber-bg: #0a0a12;
  --cyber-bg-secondary: #12121f;
  --cyber-surface: rgba(18, 18, 31, 0.95);
  --cyber-cyan: #00f0ff;
  --cyber-purple: #a855f7;
  --cyber-pink: #ff00aa;
  --cyber-yellow: #ffd700;
  --cyber-red: #ff3366;
  --cyber-green: #00ff88;
  --cyber-text: #e0e0ff;
  --cyber-text-dim: rgba(224, 224, 255, 0.5);
  --cyber-border: rgba(0, 240, 255, 0.3);
  --cyber-glow: 0 0 20px rgba(0, 240, 255, 0.3);
}

/* ===== 页面背景 ===== */
.room-lobby-view {
  min-height: 100vh;
  background: var(--cyber-bg);
  padding: 20px;
  position: relative;
  overflow-x: hidden;
}

/* 科幻网格背景 */
.room-lobby-view::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image: 
    linear-gradient(rgba(0, 240, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 240, 255, 0.03) 1px, transparent 1px);
  background-size: 50px 50px;
  pointer-events: none;
}

/* ===== 页头 ===== */
.page-header {
  max-width: 1100px;
  margin: 0 auto 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  z-index: 1;
}

.back-btn {
  color: var(--cyber-cyan) !important;
  font-size: 14px;
}

.back-btn:hover {
  text-shadow: 0 0 10px var(--cyber-cyan);
}

.room-code-info {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--cyber-surface);
  padding: 10px 16px;
  border-radius: 4px;
  border: 1px solid var(--cyber-border);
}

.room-code-info .label {
  color: var(--cyber-text-dim);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.room-code-info .code {
  color: var(--cyber-cyan);
  font-size: 18px;
  font-weight: 700;
  font-family: 'Orbitron', 'Consolas', monospace;
  letter-spacing: 2px;
  text-shadow: 0 0 10px var(--cyber-cyan);
}

.copy-btn {
  color: var(--cyber-text-dim) !important;
  padding: 4px !important;
}

.copy-btn:hover {
  color: var(--cyber-cyan) !important;
}

/* ===== 房间容器 ===== */
.room-container {
  max-width: 1100px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 24px;
  position: relative;
  z-index: 1;
}

/* ===== 左侧面板 ===== */
.left-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 游戏卡片 */
.game-card {
  background: var(--cyber-surface);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--cyber-border);
  box-shadow: var(--cyber-glow);
}

.game-cover-wrapper {
  position: relative;
  height: 160px;
  overflow: hidden;
}

.game-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.game-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px 16px;
  background: linear-gradient(transparent, rgba(0,0,0,0.8));
  display: flex;
  justify-content: flex-end;
}

.game-overlay :deep(.el-tag) {
  background: rgba(0, 0, 0, 0.6);
  border: 1px solid var(--cyber-cyan);
  color: var(--cyber-cyan);
  font-family: 'Orbitron', monospace;
  backdrop-filter: blur(4px);
}

.game-overlay :deep(.el-tag--warning) {
  border-color: var(--cyber-yellow);
  color: var(--cyber-yellow);
}

.game-overlay :deep(.el-tag--success) {
  border-color: var(--cyber-green);
  color: var(--cyber-green);
}

.game-details {
  padding: 16px 20px;
}

.game-name {
  font-size: 22px;
  font-weight: 700;
  color: var(--cyber-text);
  margin: 0 0 6px;
  font-family: 'Orbitron', sans-serif;
}

.game-desc {
  font-size: 13px;
  color: var(--cyber-text-dim);
  margin: 0;
  letter-spacing: 1px;
}

/* 玩家列表区域 */
.players-section {
  flex: 1;
}

/* ===== 右侧面板 ===== */
.right-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 控制面板 */
.control-panel {
  background: var(--cyber-surface);
  border-radius: 12px;
  padding: 24px;
  border: 1px solid var(--cyber-border);
  box-shadow: var(--cyber-glow);
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--cyber-cyan);
  margin: 0 0 20px;
  text-transform: uppercase;
  letter-spacing: 2px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  color: var(--cyber-purple);
  font-size: 10px;
}

/* 状态显示 */
.status-display {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  border: 1px solid rgba(0, 240, 255, 0.1);
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-label {
  font-size: 13px;
  color: var(--cyber-text-dim);
}

.status-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--cyber-text);
  font-family: 'Orbitron', monospace;
}

.status-value.ready {
  color: var(--cyber-green);
  text-shadow: 0 0 10px var(--cyber-green);
}

.status-waiting {
  color: var(--cyber-yellow);
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.start-btn {
  height: 50px;
  background: linear-gradient(135deg, var(--cyber-cyan), var(--cyber-purple)) !important;
  border: none !important;
  color: var(--cyber-bg) !important;
  font-weight: 700;
  font-size: 16px;
  font-family: 'Orbitron', monospace;
  text-transform: uppercase;
  letter-spacing: 2px;
  box-shadow: var(--cyber-glow);
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.start-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 0 30px rgba(0, 240, 255, 0.5);
}

.start-btn:disabled {
  background: var(--cyber-text-dim) !important;
  opacity: 0.5;
  box-shadow: none;
}

.btn-icon {
  font-size: 12px;
}

.disband-btn {
  height: 44px;
  background: transparent !important;
  border: 1px solid var(--cyber-red) !important;
  color: var(--cyber-red) !important;
  font-family: 'Orbitron', monospace;
  text-transform: uppercase;
  letter-spacing: 1px;
  transition: all 0.3s;
}

.disband-btn:hover {
  background: rgba(255, 51, 102, 0.1) !important;
  box-shadow: 0 0 15px rgba(255, 51, 102, 0.3);
}

/* 提示信息 */
.tips-section {
  margin-top: 16px;
}

.tip-content {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid var(--cyber-border);
  border-radius: 6px;
  font-size: 13px;
  color: var(--cyber-text-dim);
}

.tip-content .el-icon {
  color: var(--cyber-cyan);
  font-size: 16px;
}

/* 游戏规则 */
.game-rules {
  background: var(--cyber-surface);
  border-radius: 12px;
  padding: 24px;
  border: 1px solid var(--cyber-border);
}

.rules-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.rules-list li {
  position: relative;
  padding: 10px 0 10px 20px;
  font-size: 13px;
  color: var(--cyber-text-dim);
  border-bottom: 1px solid rgba(0, 240, 255, 0.1);
}

.rules-list li:last-child {
  border-bottom: none;
}

.rules-list li::before {
  content: '›';
  position: absolute;
  left: 0;
  color: var(--cyber-purple);
  font-weight: bold;
}

/* ===== 加载状态 ===== */
.room-container :deep(.el-loading-mask) {
  background: rgba(10, 10, 18, 0.9);
}

.room-container :deep(.el-loading-spinner .circular) {
  stroke: var(--cyber-cyan);
}

/* ===== 响应式 ===== */
@media (max-width: 900px) {
  .room-lobby-view {
    padding: 12px;
  }
  
  .page-header {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }
  
  .room-code-info {
    justify-content: center;
  }
  
  .room-container {
    grid-template-columns: 1fr;
  }
  
  .game-cover-wrapper {
    height: 120px;
  }
}
</style>
