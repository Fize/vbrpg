<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    :title="dialogTitle"
    width="400px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
  >
    <div class="reconnection-content">
      <!-- Disconnected State -->
      <div v-if="status === 'disconnected'" class="status-section">
        <el-icon class="status-icon warning"><WarningFilled /></el-icon>
        <h3>连接已断开</h3>
        <p>您的网络连接已断开，正在尝试重新连接...</p>
        
        <div class="countdown">
          <el-progress 
            :percentage="reconnectionProgress" 
            :color="progressColor"
            :stroke-width="12"
          />
          <p class="countdown-text">
            剩余时间: <strong>{{ formatTime(remainingSeconds) }}</strong>
          </p>
          <p class="hint-text">
            如果在 {{ gracePeriodMinutes }} 分钟内未能重连，您将被AI替代
          </p>
        </div>
        
        <el-button type="primary" :loading="true" disabled>
          重连中...
        </el-button>
      </div>

      <!-- Reconnected State -->
      <div v-else-if="status === 'reconnected'" class="status-section">
        <el-icon class="status-icon success"><SuccessFilled /></el-icon>
        <h3>重连成功！</h3>
        <p>您已成功重新连接到游戏</p>
        <p class="info-text">断线时长: {{ disconnectDuration }}</p>
        
        <el-button type="success" @click="handleClose">
          继续游戏
        </el-button>
      </div>

      <!-- Failed State -->
      <div v-else-if="status === 'failed'" class="status-section">
        <el-icon class="status-icon error"><CircleCloseFilled /></el-icon>
        <h3>重连失败</h3>
        <p>{{ failureMessage }}</p>
        
        <div class="actions">
          <el-button type="primary" @click="handleReturnToLobby">
            返回大厅
          </el-button>
          <el-button @click="handleRetry">
            重试
          </el-button>
        </div>
      </div>

      <!-- Replaced by AI State -->
      <div v-else-if="status === 'replaced'" class="status-section">
        <el-icon class="status-icon info"><InfoFilled /></el-icon>
        <h3>已被AI替代</h3>
        <p>由于长时间未重连，您的位置已被AI接管</p>
        <p class="hint-text">游戏将继续进行，您可以观战</p>
        
        <div class="actions">
          <el-button type="primary" @click="handleReturnToLobby">
            返回大厅
          </el-button>
          <el-button @click="handleSpectate">
            观战
          </el-button>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { 
  WarningFilled, 
  SuccessFilled, 
  CircleCloseFilled,
  InfoFilled 
} from '@element-plus/icons-vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  status: {
    type: String,
    default: 'disconnected', // 'disconnected', 'reconnected', 'failed', 'replaced'
    validator: (value) => ['disconnected', 'reconnected', 'failed', 'replaced'].includes(value)
  },
  gracePeriodSeconds: {
    type: Number,
    default: 300 // 5 minutes
  },
  disconnectDuration: {
    type: String,
    default: ''
  },
  failureMessage: {
    type: String,
    default: '无法重新连接到服务器'
  }
})

const emit = defineEmits(['update:visible', 'close', 'retry', 'return-to-lobby', 'spectate'])

const remainingSeconds = ref(props.gracePeriodSeconds)
let countdownInterval = null

// Computed
const dialogTitle = computed(() => {
  const titles = {
    disconnected: '正在重新连接',
    reconnected: '重连成功',
    failed: '连接失败',
    replaced: 'AI接管'
  }
  return titles[props.status] || '连接状态'
})

const gracePeriodMinutes = computed(() => {
  return Math.floor(props.gracePeriodSeconds / 60)
})

const reconnectionProgress = computed(() => {
  const elapsed = props.gracePeriodSeconds - remainingSeconds.value
  return (elapsed / props.gracePeriodSeconds) * 100
})

const progressColor = computed(() => {
  const progress = reconnectionProgress.value
  if (progress < 50) return '#67c23a' // green
  if (progress < 80) return '#e6a23c' // yellow
  return '#f56c6c' // red
})

// Methods
const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const startCountdown = () => {
  stopCountdown()
  
  countdownInterval = setInterval(() => {
    if (remainingSeconds.value > 0) {
      remainingSeconds.value--
    } else {
      stopCountdown()
      // Emit timeout event
      emit('timeout')
    }
  }, 1000)
}

const stopCountdown = () => {
  if (countdownInterval) {
    clearInterval(countdownInterval)
    countdownInterval = null
  }
}

const handleClose = () => {
  emit('close')
}

const handleRetry = () => {
  emit('retry')
}

const handleReturnToLobby = () => {
  emit('return-to-lobby')
}

const handleSpectate = () => {
  emit('spectate')
}

// Watch status changes
watch(() => props.status, (newStatus) => {
  if (newStatus === 'disconnected') {
    remainingSeconds.value = props.gracePeriodSeconds
    startCountdown()
  } else {
    stopCountdown()
  }
}, { immediate: true })

watch(() => props.visible, (newVisible) => {
  if (newVisible && props.status === 'disconnected') {
    remainingSeconds.value = props.gracePeriodSeconds
    startCountdown()
  } else if (!newVisible) {
    stopCountdown()
  }
})

// Cleanup
onBeforeUnmount(() => {
  stopCountdown()
})
</script>

<style scoped>
.reconnection-content {
  padding: 20px 0;
}

.status-section {
  text-align: center;
}

.status-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.status-icon.warning {
  color: #e6a23c;
  animation: pulse 1.5s infinite;
}

.status-icon.success {
  color: #67c23a;
  animation: bounceIn 0.5s;
}

.status-icon.error {
  color: #f56c6c;
}

.status-icon.info {
  color: #909399;
}

h3 {
  font-size: 24px;
  color: #303133;
  margin: 16px 0 12px;
}

p {
  font-size: 16px;
  color: #606266;
  margin: 8px 0;
  line-height: 1.6;
}

.countdown {
  margin: 24px 0;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.countdown-text {
  font-size: 18px;
  color: #303133;
  margin: 16px 0 8px;
}

.countdown-text strong {
  font-size: 24px;
  color: #e6a23c;
  font-weight: 600;
}

.hint-text {
  font-size: 14px;
  color: #909399;
  margin-top: 8px;
}

.info-text {
  font-size: 14px;
  color: #409eff;
  font-weight: 500;
}

.actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 24px;
}

.el-button {
  min-width: 120px;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.05);
  }
}

@keyframes bounceIn {
  0% {
    opacity: 0;
    transform: scale(0.3);
  }
  50% {
    transform: scale(1.05);
  }
  70% {
    transform: scale(0.9);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

@media (max-width: 480px) {
  h3 {
    font-size: 20px;
  }

  p {
    font-size: 14px;
  }

  .countdown-text {
    font-size: 16px;
  }

  .countdown-text strong {
    font-size: 20px;
  }

  .actions {
    flex-direction: column;
  }

  .el-button {
    width: 100%;
  }
}
</style>
