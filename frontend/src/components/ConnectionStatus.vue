<template>
  <div class="connection-status" :class="statusClass">
    <div class="status-indicator">
      <span class="status-dot" :class="statusClass"></span>
      <span class="status-text">{{ statusText }}</span>
    </div>
    
    <el-button
      v-if="status === 'disconnected' || status === 'error'"
      type="text"
      size="small"
      @click="handleReconnect"
      :loading="reconnecting"
    >
      重新连接
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

interface Props {
  status: 'connected' | 'connecting' | 'disconnected' | 'error'
  showReconnect?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showReconnect: true
})

const emit = defineEmits<{
  'reconnect': []
}>()

const reconnecting = ref(false)

const statusClass = computed(() => {
  return `status-${props.status}`
})

const statusText = computed(() => {
  switch (props.status) {
    case 'connected':
      return '已连接'
    case 'connecting':
      return '连接中...'
    case 'disconnected':
      return '未连接'
    case 'error':
      return '连接错误'
    default:
      return '未知状态'
  }
})

const handleReconnect = async () => {
  reconnecting.value = true
  try {
    emit('reconnect')
  } finally {
    // Reset after a delay to show loading state
    setTimeout(() => {
      reconnecting.value = false
    }, 1000)
  }
}
</script>

<style scoped>
.connection-status {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 14px;
  transition: all 0.3s;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  transition: all 0.3s;
}

.status-dot.status-connected {
  background-color: #67c23a;
  box-shadow: 0 0 0 2px rgba(103, 194, 58, 0.3);
}

.status-dot.status-connecting {
  background-color: #e6a23c;
  animation: pulse 1.5s ease-in-out infinite;
}

.status-dot.status-disconnected {
  background-color: #909399;
}

.status-dot.status-error {
  background-color: #f56c6c;
  animation: pulse 1s ease-in-out infinite;
}

.status-text {
  color: #606266;
  font-weight: 500;
}

.connection-status.status-connected {
  background-color: rgba(103, 194, 58, 0.1);
}

.connection-status.status-connecting {
  background-color: rgba(230, 162, 60, 0.1);
}

.connection-status.status-disconnected {
  background-color: rgba(144, 147, 153, 0.1);
}

.connection-status.status-error {
  background-color: rgba(245, 108, 108, 0.1);
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
}

.el-button {
  margin-left: 4px;
}
</style>
