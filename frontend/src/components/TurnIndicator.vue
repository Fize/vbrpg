<template>
  <div class="turn-indicator">
    <div class="turn-info">
      <div class="turn-number">
        <el-icon><Timer /></el-icon>
        第 {{ turnNumber }} 回合
      </div>
      <div class="current-player">
        <div class="player-avatar" :class="{ 'ai-player': isAiPlayer }">
          {{ currentPlayerInitial }}
        </div>
        <div class="player-details">
          <div class="player-name">{{ currentPlayerName }}</div>
          <div class="player-status">
            <template v-if="isAiThinking">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>AI正在思考...</span>
            </template>
            <template v-else-if="isMyTurn">
              <el-icon color="#67c23a"><CircleCheckFilled /></el-icon>
              <span style="color: #67c23a; font-weight: 600;">轮到你了！</span>
            </template>
            <template v-else>
              <span>当前回合</span>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- Progress bar for turn timeout -->
    <div v-if="showProgress" class="turn-progress">
      <el-progress
        :percentage="progressPercentage"
        :color="progressColor"
        :show-text="false"
        :stroke-width="4"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import { Timer, Loading, CircleCheckFilled } from '@element-plus/icons-vue'

const props = defineProps({
  currentPlayerId: {
    type: String,
    default: null
  },
  turnNumber: {
    type: Number,
    default: 1
  },
  isAiThinking: {
    type: Boolean,
    default: false
  },
  participants: {
    type: Array,
    default: () => []
  }
})

// State
const progressPercentage = ref(0)
const progressInterval = ref(null)
const showProgress = ref(false)

// Computed
const currentPlayer = computed(() => {
  if (!props.currentPlayerId) return null
  return props.participants.find(
    p => p.player_id === props.currentPlayerId || `AI_${p.id}` === props.currentPlayerId
  )
})

const isAiPlayer = computed(() => {
  return currentPlayer.value?.is_ai_agent || false
})

const currentPlayerName = computed(() => {
  if (!currentPlayer.value) return '等待中...'
  
  if (currentPlayer.value.is_ai_agent) {
    return `AI-${currentPlayer.value.ai_personality}`
  }
  return currentPlayer.value.player?.username || '未知玩家'
})

const currentPlayerInitial = computed(() => {
  return currentPlayerName.value.charAt(0).toUpperCase()
})

const isMyTurn = computed(() => {
  const currentUserId = localStorage.getItem('userId')
  return props.currentPlayerId === currentUserId
})

const progressColor = computed(() => {
  if (progressPercentage.value < 50) return '#67c23a'
  if (progressPercentage.value < 80) return '#e6a23c'
  return '#f56c6c'
})

// Methods
const startProgressBar = () => {
  progressPercentage.value = 0
  showProgress.value = true
  
  // Progress over 60 seconds (typical turn duration)
  const duration = 60000 // 60 seconds
  const interval = 100 // Update every 100ms
  const increment = (100 / duration) * interval
  
  progressInterval.value = setInterval(() => {
    progressPercentage.value += increment
    if (progressPercentage.value >= 100) {
      stopProgressBar()
    }
  }, interval)
}

const stopProgressBar = () => {
  if (progressInterval.value) {
    clearInterval(progressInterval.value)
    progressInterval.value = null
  }
  showProgress.value = false
  progressPercentage.value = 0
}

const resetProgressBar = () => {
  stopProgressBar()
  startProgressBar()
}

// Watch for turn changes
watch(() => props.currentPlayerId, (newId, oldId) => {
  if (newId !== oldId && newId) {
    resetProgressBar()
  }
})

watch(() => props.isAiThinking, (thinking) => {
  if (thinking) {
    // AI thinking, show different progress
    stopProgressBar()
  }
})

// Lifecycle
onBeforeUnmount(() => {
  stopProgressBar()
})
</script>

<style scoped>
.turn-indicator {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 15px 20px;
  color: white;
  min-width: 300px;
}

.turn-info {
  display: flex;
  align-items: center;
  gap: 20px;
}

.turn-number {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  padding-right: 20px;
  border-right: 2px solid rgba(255, 255, 255, 0.3);
}

.current-player {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.player-avatar {
  width: 45px;
  height: 45px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  border: 2px solid white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: bold;
  flex-shrink: 0;
}

.player-avatar.ai-player {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.player-details {
  flex: 1;
}

.player-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}

.player-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  opacity: 0.9;
}

.turn-progress {
  margin-top: 12px;
}

/* Animations */
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

.player-status .is-loading {
  animation: pulse 1.5s ease-in-out infinite;
}

/* Responsive */
@media (max-width: 768px) {
  .turn-indicator {
    min-width: unset;
    width: 100%;
  }

  .turn-info {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .turn-number {
    padding-right: 0;
    border-right: none;
    padding-bottom: 12px;
    border-bottom: 2px solid rgba(255, 255, 255, 0.3);
    width: 100%;
  }
}
</style>
