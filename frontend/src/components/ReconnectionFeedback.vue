<template>
  <transition name="fade">
    <div v-if="visible" class="reconnection-overlay">
      <div class="reconnection-card">
        <div class="reconnection-icon">
          <el-icon v-if="status === 'reconnecting'" class="rotating" :size="48">
            <Loading />
          </el-icon>
          <el-icon v-else-if="status === 'success'" class="success" :size="48">
            <CircleCheck />
          </el-icon>
          <el-icon v-else-if="status === 'failed'" class="error" :size="48">
            <CircleClose />
          </el-icon>
        </div>

        <h3 class="reconnection-title">{{ title }}</h3>
        <p class="reconnection-message">{{ message }}</p>

        <div v-if="showProgress" class="reconnection-progress">
          <el-progress
            :percentage="progress"
            :status="progressStatus"
            :stroke-width="8"
          />
          <p class="attempt-text">第 {{ currentAttempt }}/{{ maxAttempts }} 次尝试</p>
        </div>

        <div v-if="showCountdown" class="countdown">
          <p>{{ countdownSeconds }} 秒后自动重试</p>
        </div>

        <div class="reconnection-actions">
          <el-button
            v-if="status === 'failed'"
            type="primary"
            @click="handleRetry"
            :loading="retrying"
          >
            立即重试
          </el-button>
          <el-button
            v-if="status === 'failed' && allowCancel"
            @click="handleCancel"
          >
            取消
          </el-button>
          <el-button
            v-if="status === 'success'"
            type="primary"
            @click="handleClose"
          >
            确定
          </el-button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { Loading, CircleCheck, CircleClose } from '@element-plus/icons-vue'

interface Props {
  modelValue?: boolean
  status: 'reconnecting' | 'success' | 'failed'
  currentAttempt?: number
  maxAttempts?: number
  allowCancel?: boolean
  autoRetryDelay?: number
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  currentAttempt: 1,
  maxAttempts: 5,
  allowCancel: true,
  autoRetryDelay: 5
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'retry': []
  'cancel': []
  'close': []
}>()

const retrying = ref(false)
const countdownSeconds = ref(props.autoRetryDelay)
let countdownInterval: number | null = null

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const title = computed(() => {
  switch (props.status) {
    case 'reconnecting':
      return '正在重新连接...'
    case 'success':
      return '重新连接成功'
    case 'failed':
      return '重新连接失败'
    default:
      return '重新连接'
  }
})

const message = computed(() => {
  switch (props.status) {
    case 'reconnecting':
      return '正在尝试恢复与服务器的连接，请稍候'
    case 'success':
      return '已成功恢复连接，游戏将继续'
    case 'failed':
      return '无法连接到服务器，请检查网络连接'
    default:
      return ''
  }
})

const showProgress = computed(() => {
  return props.status === 'reconnecting'
})

const progress = computed(() => {
  return (props.currentAttempt / props.maxAttempts) * 100
})

const progressStatus = computed(() => {
  if (props.currentAttempt >= props.maxAttempts - 1) {
    return 'exception'
  }
  return undefined
})

const showCountdown = computed(() => {
  return props.status === 'failed' && countdownSeconds.value > 0
})

// Start countdown when failed
watch(() => props.status, (newStatus) => {
  if (newStatus === 'failed') {
    startCountdown()
  } else {
    stopCountdown()
  }
})

const startCountdown = () => {
  countdownSeconds.value = props.autoRetryDelay
  
  if (countdownInterval) {
    clearInterval(countdownInterval)
  }
  
  countdownInterval = window.setInterval(() => {
    if (countdownSeconds.value > 0) {
      countdownSeconds.value--
    } else {
      stopCountdown()
      handleRetry()
    }
  }, 1000)
}

const stopCountdown = () => {
  if (countdownInterval) {
    clearInterval(countdownInterval)
    countdownInterval = null
  }
}

const handleRetry = async () => {
  stopCountdown()
  retrying.value = true
  try {
    emit('retry')
  } finally {
    setTimeout(() => {
      retrying.value = false
    }, 500)
  }
}

const handleCancel = () => {
  stopCountdown()
  visible.value = false
  emit('cancel')
}

const handleClose = () => {
  visible.value = false
  emit('close')
}

// Auto-close after success
watch(() => props.status, (newStatus) => {
  if (newStatus === 'success') {
    setTimeout(() => {
      handleClose()
    }, 2000)
  }
})

// Cleanup on unmount
onUnmounted(() => {
  stopCountdown()
})
</script>

<style scoped>
.reconnection-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000;
  backdrop-filter: blur(4px);
}

.reconnection-card {
  background-color: #fff;
  border-radius: 8px;
  padding: 32px;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  text-align: center;
}

.reconnection-icon {
  margin-bottom: 20px;
}

.reconnection-icon .el-icon {
  color: #409eff;
}

.reconnection-icon .el-icon.rotating {
  animation: rotate 1.5s linear infinite;
}

.reconnection-icon .el-icon.success {
  color: #67c23a;
}

.reconnection-icon .el-icon.error {
  color: #f56c6c;
}

.reconnection-title {
  margin: 0 0 12px 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.reconnection-message {
  margin: 0 0 24px 0;
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

.reconnection-progress {
  margin-bottom: 24px;
}

.attempt-text {
  margin: 12px 0 0 0;
  font-size: 14px;
  color: #909399;
}

.countdown {
  margin-bottom: 24px;
}

.countdown p {
  margin: 0;
  font-size: 14px;
  color: #606266;
}

.reconnection-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
