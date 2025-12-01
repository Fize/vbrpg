<template>
  <!-- F9-F11: 游戏控制栏组件 -->
  <div class="game-control-bar">
    <!-- 游戏状态显示 -->
    <div class="status-indicator">
      <span :class="['status-dot', statusClass]"></span>
      <span class="status-text">{{ statusText }}</span>
    </div>

    <!-- 控制按钮组 -->
    <div class="control-buttons">
      <!-- 开始游戏按钮 -->
      <el-button
        v-if="!isStarted"
        type="primary"
        :disabled="disabled || isSpectator"
        @click="handleStart"
        :loading="loading"
      >
        <el-icon class="mr-1"><VideoPlay /></el-icon>
        开始游戏
      </el-button>

      <!-- 暂停按钮（游戏进行中且未暂停时显示） -->
      <el-button
        v-if="isStarted && !isPaused"
        type="warning"
        :disabled="disabled"
        @click="handlePause"
        :loading="loading"
      >
        <el-icon class="mr-1"><VideoPause /></el-icon>
        暂停
      </el-button>

      <!-- 继续按钮（游戏暂停时显示） -->
      <el-button
        v-if="isStarted && isPaused"
        type="success"
        :disabled="disabled"
        @click="handleResume"
        :loading="loading"
      >
        <el-icon class="mr-1"><VideoPlay /></el-icon>
        继续
      </el-button>
    </div>

    <!-- 旁观者提示 -->
    <div v-if="isSpectator" class="spectator-badge">
      <el-tag type="info" size="small">旁观模式</el-tag>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { VideoPlay, VideoPause } from '@element-plus/icons-vue'

// Props 定义
const props = defineProps({
  /**
   * 游戏是否已开始
   */
  isStarted: {
    type: Boolean,
    default: false
  },
  /**
   * 游戏是否暂停
   */
  isPaused: {
    type: Boolean,
    default: false
  },
  /**
   * 是否为旁观者模式
   */
  isSpectator: {
    type: Boolean,
    default: false
  },
  /**
   * 是否禁用所有按钮
   */
  disabled: {
    type: Boolean,
    default: false
  }
})

// Events 定义
const emit = defineEmits(['start', 'pause', 'resume'])

// 加载状态
const loading = ref(false)

// 计算属性：状态样式类
const statusClass = computed(() => {
  if (!props.isStarted) return 'waiting'
  if (props.isPaused) return 'paused'
  return 'running'
})

// 计算属性：状态文本
const statusText = computed(() => {
  if (!props.isStarted) return '等待开始'
  if (props.isPaused) return '游戏暂停'
  return '游戏进行中'
})

// 事件处理
async function handleStart() {
  loading.value = true
  try {
    emit('start')
  } finally {
    loading.value = false
  }
}

async function handlePause() {
  loading.value = true
  try {
    emit('pause')
  } finally {
    loading.value = false
  }
}

async function handleResume() {
  loading.value = true
  try {
    emit('resume')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.game-control-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: linear-gradient(135deg, rgba(30, 30, 40, 0.95), rgba(20, 20, 30, 0.98));
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

/* 状态指示器 */
.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-dot.waiting {
  background: #909399;
}

.status-dot.running {
  background: #67c23a;
}

.status-dot.paused {
  background: #e6a23c;
}

.status-text {
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  font-weight: 500;
}

/* 控制按钮组 */
.control-buttons {
  display: flex;
  gap: 12px;
}

.control-buttons .el-button {
  min-width: 100px;
}

/* 旁观者标签 */
.spectator-badge {
  margin-left: 12px;
}

/* 图标间距 */
.mr-1 {
  margin-right: 4px;
}

/* 脉动动画 */
@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.1);
  }
}

/* 响应式适配 */
@media (max-width: 768px) {
  .game-control-bar {
    flex-wrap: wrap;
    gap: 12px;
  }
  
  .status-indicator {
    flex: 1;
    min-width: 120px;
  }
  
  .control-buttons {
    flex: 1;
    justify-content: flex-end;
  }
  
  .spectator-badge {
    width: 100%;
    text-align: center;
    margin-left: 0;
  }
}
</style>
