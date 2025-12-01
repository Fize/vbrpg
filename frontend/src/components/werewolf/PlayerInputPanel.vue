<template>
  <!-- F22-F25: 玩家发言输入面板组件 -->
  <div 
    v-if="visible"
    class="player-input-panel"
    :class="{ 'is-active': isMyTurn, 'is-disabled': !isMyTurn }"
  >
    <!-- 面板头部 -->
    <div class="panel-header">
      <div class="header-left">
        <el-icon class="header-icon"><Microphone /></el-icon>
        <span class="header-title">我的发言</span>
      </div>
      <div class="header-right">
        <span v-if="isMyTurn" class="turn-indicator">
          <span class="pulse-dot"></span>
          轮到你发言
        </span>
        <span v-else class="waiting-indicator">
          等待发言
        </span>
      </div>
    </div>
    
    <!-- 输入区域 -->
    <div class="input-area">
      <el-input
        v-model="inputContent"
        type="textarea"
        :autosize="{ minRows: 3, maxRows: 6 }"
        :placeholder="placeholderText"
        :disabled="!isMyTurn || isSubmitting"
        :maxlength="maxLength"
        show-word-limit
        resize="none"
        class="speech-input"
        @keydown.enter.ctrl="handleSubmit"
        @keydown.enter.meta="handleSubmit"
      />
    </div>
    
    <!-- 底部操作栏 -->
    <div class="panel-footer">
      <div class="footer-left">
        <span class="hint-text">
          <el-icon><InfoFilled /></el-icon>
          {{ hintText }}
        </span>
      </div>
      <div class="footer-right">
        <!-- 跳过发言按钮 -->
        <el-button
          v-if="allowSkip && isMyTurn"
          type="info"
          size="default"
          :disabled="isSubmitting"
          @click="handleSkip"
        >
          跳过发言
        </el-button>
        
        <!-- 提交发言按钮 -->
        <el-button
          type="primary"
          size="default"
          :disabled="!canSubmit"
          :loading="isSubmitting"
          @click="handleSubmit"
        >
          <el-icon v-if="!isSubmitting"><Position /></el-icon>
          {{ submitButtonText }}
        </el-button>
      </div>
    </div>
    
    <!-- 倒计时提示（可选） -->
    <div v-if="showCountdown && timeRemaining > 0" class="countdown-overlay">
      <div class="countdown-content">
        <span class="countdown-label">剩余时间</span>
        <span class="countdown-value" :class="{ 'is-urgent': timeRemaining <= 10 }">
          {{ timeRemaining }}s
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Microphone, InfoFilled, Position } from '@element-plus/icons-vue'

// Props 定义
const props = defineProps({
  /**
   * 是否显示面板
   */
  visible: {
    type: Boolean,
    default: true
  },
  /**
   * 是否轮到当前玩家发言
   */
  isMyTurn: {
    type: Boolean,
    default: false
  },
  /**
   * 是否正在提交
   */
  isSubmitting: {
    type: Boolean,
    default: false
  },
  /**
   * 是否允许跳过发言
   */
  allowSkip: {
    type: Boolean,
    default: false
  },
  /**
   * 最大字数限制
   */
  maxLength: {
    type: Number,
    default: 500
  },
  /**
   * 显示倒计时
   */
  showCountdown: {
    type: Boolean,
    default: false
  },
  /**
   * 剩余时间（秒）
   */
  timeRemaining: {
    type: Number,
    default: 0
  },
  /**
   * 当前轮次信息
   */
  currentRound: {
    type: Number,
    default: 1
  }
})

// 事件定义
const emit = defineEmits(['submit', 'skip'])

// 响应式数据
const inputContent = ref('')

// 计算属性
const placeholderText = computed(() => {
  if (!props.isMyTurn) {
    return '等待轮到你发言时再输入...'
  }
  return '请输入你的发言内容，分析局势、表明立场...'
})

const hintText = computed(() => {
  if (!props.isMyTurn) {
    return '请耐心等待'
  }
  return 'Ctrl+Enter 快速提交'
})

const canSubmit = computed(() => {
  return props.isMyTurn && 
         !props.isSubmitting && 
         inputContent.value.trim().length > 0
})

const submitButtonText = computed(() => {
  if (props.isSubmitting) {
    return '提交中...'
  }
  return '提交发言'
})

// 监听 isMyTurn 变化，清空输入
watch(() => props.isMyTurn, (newVal, oldVal) => {
  // 当轮次结束时清空输入
  if (!newVal && oldVal) {
    inputContent.value = ''
  }
})

// 事件处理
const handleSubmit = () => {
  if (!canSubmit.value) return
  
  emit('submit', inputContent.value.trim())
}

const handleSkip = () => {
  emit('skip')
}

// 暴露方法给父组件
defineExpose({
  clearInput: () => {
    inputContent.value = ''
  },
  focusInput: () => {
    // 通过 ref 聚焦输入框（需要时实现）
  }
})
</script>

<style scoped>
.player-input-panel {
  background: linear-gradient(135deg, rgba(30, 30, 45, 0.95), rgba(20, 20, 35, 0.95));
  border: 1px solid rgba(0, 240, 255, 0.15);
  border-radius: 12px;
  padding: 16px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
}

.player-input-panel.is-active {
  border-color: rgba(0, 240, 255, 0.4);
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.3),
    0 0 40px rgba(0, 240, 255, 0.1);
}

.player-input-panel.is-disabled {
  opacity: 0.7;
}

/* 面板头部 */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-icon {
  font-size: 18px;
  color: #00f0ff;
}

.header-title {
  font-size: 15px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.95);
}

.header-right {
  display: flex;
  align-items: center;
}

/* 轮次指示器 */
.turn-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #4ade80;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  background: #4ade80;
  border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.3);
    opacity: 0.7;
  }
}

.waiting-indicator {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
}

/* 输入区域 */
.input-area {
  margin-bottom: 12px;
}

:deep(.speech-input .el-textarea__inner) {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.95);
  font-size: 14px;
  line-height: 1.6;
  padding: 12px;
  transition: all 0.3s ease;
}

:deep(.speech-input .el-textarea__inner:focus) {
  border-color: rgba(0, 240, 255, 0.5);
  box-shadow: 0 0 0 2px rgba(0, 240, 255, 0.1);
}

:deep(.speech-input .el-textarea__inner::placeholder) {
  color: rgba(255, 255, 255, 0.35);
}

:deep(.speech-input .el-textarea__inner:disabled) {
  background: rgba(0, 0, 0, 0.2);
  border-color: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.4);
  cursor: not-allowed;
}

/* 字数统计 */
:deep(.speech-input .el-input__count) {
  background: transparent;
  color: rgba(255, 255, 255, 0.4);
  font-size: 11px;
}

/* 底部操作栏 */
.panel-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-left {
  flex: 1;
}

.hint-text {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
}

.footer-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 按钮样式 */
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #0ea5e9, #06b6d4);
  border: none;
  font-weight: 500;
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #38bdf8, #22d3ee);
}

:deep(.el-button--info) {
  background: rgba(100, 116, 139, 0.3);
  border: 1px solid rgba(100, 116, 139, 0.4);
  color: rgba(255, 255, 255, 0.7);
}

:deep(.el-button--info:hover) {
  background: rgba(100, 116, 139, 0.5);
  border-color: rgba(100, 116, 139, 0.6);
  color: rgba(255, 255, 255, 0.9);
}

/* 倒计时覆盖层 */
.countdown-overlay {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 10;
}

.countdown-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 8px;
  padding: 8px 12px;
}

.countdown-label {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 2px;
}

.countdown-value {
  font-size: 18px;
  font-weight: 700;
  color: #00f0ff;
}

.countdown-value.is-urgent {
  color: #ef4444;
  animation: urgentPulse 0.5s ease-in-out infinite;
}

@keyframes urgentPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

/* 响应式 */
@media (max-width: 768px) {
  .player-input-panel {
    padding: 12px;
  }
  
  .panel-footer {
    flex-direction: column;
    gap: 10px;
  }
  
  .footer-left {
    display: none;
  }
  
  .footer-right {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
