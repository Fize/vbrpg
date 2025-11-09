<template>
  <el-alert
    v-if="visible"
    :title="title"
    :type="alertType"
    :description="description"
    :closable="closable"
    show-icon
    class="timeout-warning"
    @close="handleClose"
  >
    <template v-if="showCountdown" #default>
      <div class="countdown-container">
        <p class="countdown-text">{{ message }}</p>
        <div class="countdown-timer">
          <el-progress
            :percentage="percentage"
            :status="progressStatus"
            :stroke-width="8"
          />
          <span class="time-remaining">{{ formattedTimeRemaining }}</span>
        </div>
      </div>
    </template>
  </el-alert>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'

interface Props {
  modelValue?: boolean
  type?: 'turn' | 'game' | 'reconnection'
  remainingSeconds: number
  totalSeconds: number
  title?: string
  message?: string
  closable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: true,
  type: 'turn',
  closable: true
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'timeout': []
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const currentRemaining = ref(props.remainingSeconds)
let intervalId: number | null = null

// Update countdown
watch(() => props.remainingSeconds, (newVal) => {
  currentRemaining.value = newVal
}, { immediate: true })

// Start countdown timer
const startCountdown = () => {
  if (intervalId) {
    clearInterval(intervalId)
  }
  
  intervalId = window.setInterval(() => {
    if (currentRemaining.value > 0) {
      currentRemaining.value--
    } else {
      emit('timeout')
      stopCountdown()
    }
  }, 1000)
}

const stopCountdown = () => {
  if (intervalId) {
    clearInterval(intervalId)
    intervalId = null
  }
}

// Computed properties
const alertType = computed(() => {
  if (props.type === 'reconnection') return 'warning'
  if (currentRemaining.value < 10) return 'error'
  if (currentRemaining.value < 30) return 'warning'
  return 'info'
})

const title = computed(() => {
  if (props.title) return props.title
  
  switch (props.type) {
    case 'turn':
      return '回合时间提醒'
    case 'game':
      return '游戏时长提醒'
    case 'reconnection':
      return '重连时间提醒'
    default:
      return '时间提醒'
  }
})

const message = computed(() => {
  if (props.message) return props.message
  
  switch (props.type) {
    case 'turn':
      return '请尽快完成你的回合操作'
    case 'game':
      return '游戏已进行较长时间，请注意时间限制'
    case 'reconnection':
      return '请尽快重新连接，否则将被 AI 替代'
    default:
      return '请注意时间限制'
  }
})

const description = computed(() => {
  if (showCountdown.value) return undefined
  return `剩余时间: ${formattedTimeRemaining.value}`
})

const showCountdown = computed(() => {
  return props.type !== 'game'
})

const percentage = computed(() => {
  return (currentRemaining.value / props.totalSeconds) * 100
})

const progressStatus = computed(() => {
  if (currentRemaining.value < 10) return 'exception'
  if (currentRemaining.value < 30) return 'warning'
  return undefined
})

const formattedTimeRemaining = computed(() => {
  const minutes = Math.floor(currentRemaining.value / 60)
  const seconds = currentRemaining.value % 60
  
  if (minutes > 0) {
    return `${minutes}分${seconds}秒`
  }
  return `${seconds}秒`
})

const handleClose = () => {
  visible.value = false
  stopCountdown()
}

// Start countdown when component mounts
if (props.modelValue) {
  startCountdown()
}

// Watch visibility to start/stop countdown
watch(visible, (newVal) => {
  if (newVal) {
    startCountdown()
  } else {
    stopCountdown()
  }
})

// Cleanup on unmount
onUnmounted(() => {
  stopCountdown()
})
</script>

<style scoped>
.timeout-warning {
  margin-bottom: 16px;
}

.countdown-container {
  margin-top: 8px;
}

.countdown-text {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #606266;
}

.countdown-timer {
  display: flex;
  align-items: center;
  gap: 16px;
}

.countdown-timer .el-progress {
  flex: 1;
}

.time-remaining {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
}
</style>
