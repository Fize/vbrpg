<template>
  <!-- F17-F21: 发言气泡组件 -->
  <div 
    v-if="visible"
    class="speech-bubble"
    :class="[
      positionClass,
      { 'is-streaming': isStreaming, 'is-human': isHuman }
    ]"
    :style="bubbleStyle"
  >
    <!-- 气泡主体 -->
    <div class="bubble-content">
      <!-- 发言者信息 -->
      <div class="speaker-info">
        <span class="speaker-seat">{{ seatNumber }}号</span>
        <span class="speaker-name">{{ playerName }}</span>
      </div>
      
      <!-- 发言内容 -->
      <div class="speech-content">
        <p class="speech-text">
          {{ content }}
          <span v-if="isStreaming" class="typing-cursor">|</span>
        </p>
      </div>
    </div>
    
    <!-- 气泡尾巴指向玩家头像 -->
    <div class="bubble-tail" :class="tailPosition"></div>
    
    <!-- 流式加载指示器 -->
    <div v-if="isStreaming" class="streaming-indicator">
      <span class="dot"></span>
      <span class="dot"></span>
      <span class="dot"></span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

// Props 定义
const props = defineProps({
  /**
   * 座位号
   */
  seatNumber: {
    type: Number,
    required: true
  },
  /**
   * 玩家名称
   */
  playerName: {
    type: String,
    default: ''
  },
  /**
   * 发言内容
   */
  content: {
    type: String,
    default: ''
  },
  /**
   * 是否正在流式输出
   */
  isStreaming: {
    type: Boolean,
    default: false
  },
  /**
   * 是否为人类玩家
   */
  isHuman: {
    type: Boolean,
    default: false
  },
  /**
   * 是否显示
   */
  visible: {
    type: Boolean,
    default: true
  },
  /**
   * 气泡位置 (top/bottom/left/right 或自定义坐标)
   */
  position: {
    type: [String, Object],
    default: 'top'
  }
})

// 计算属性：位置类
const positionClass = computed(() => {
  if (typeof props.position === 'string') {
    return `position-${props.position}`
  }
  return 'position-custom'
})

// 计算属性：自定义位置样式
const bubbleStyle = computed(() => {
  if (typeof props.position === 'object') {
    return {
      top: props.position.top,
      left: props.position.left,
      right: props.position.right,
      bottom: props.position.bottom,
      transform: props.position.transform || 'none'
    }
  }
  return {}
})

// 计算属性：尾巴位置
const tailPosition = computed(() => {
  if (typeof props.position === 'string') {
    // 根据气泡位置确定尾巴方向
    const tailMap = {
      top: 'tail-bottom',
      bottom: 'tail-top',
      left: 'tail-right',
      right: 'tail-left'
    }
    return tailMap[props.position] || 'tail-bottom'
  }
  return 'tail-bottom'
})
</script>

<style scoped>
.speech-bubble {
  position: absolute;
  z-index: 100;
  max-width: 280px;
  min-width: 150px;
  animation: bubbleAppear 0.3s ease-out;
}

@keyframes bubbleAppear {
  0% {
    opacity: 0;
    transform: scale(0.9);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

/* 气泡主体 */
.bubble-content {
  background: linear-gradient(135deg, rgba(30, 30, 45, 0.98), rgba(20, 20, 35, 0.98));
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 12px;
  padding: 12px 14px;
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.4),
    0 0 30px rgba(0, 240, 255, 0.1);
  position: relative;
}

.speech-bubble.is-streaming .bubble-content {
  border-color: rgba(0, 240, 255, 0.5);
  animation: streamingPulse 1.5s ease-in-out infinite;
}

@keyframes streamingPulse {
  0%, 100% {
    box-shadow: 
      0 4px 20px rgba(0, 0, 0, 0.4),
      0 0 30px rgba(0, 240, 255, 0.1);
  }
  50% {
    box-shadow: 
      0 4px 25px rgba(0, 0, 0, 0.5),
      0 0 40px rgba(0, 240, 255, 0.2);
  }
}

.speech-bubble.is-human .bubble-content {
  border-color: rgba(74, 222, 128, 0.4);
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.4),
    0 0 30px rgba(74, 222, 128, 0.1);
}

/* 发言者信息 */
.speaker-info {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.speaker-seat {
  font-size: 11px;
  font-weight: 700;
  color: #00f0ff;
  background: rgba(0, 240, 255, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

.speech-bubble.is-human .speaker-seat {
  color: #4ade80;
  background: rgba(74, 222, 128, 0.1);
}

.speaker-name {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

/* 发言内容 */
.speech-content {
  max-height: 120px;
  overflow-y: auto;
}

.speech-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.95);
  word-break: break-word;
}

/* 打字光标 */
.typing-cursor {
  display: inline-block;
  font-weight: bold;
  color: #00f0ff;
  text-shadow: 0 0 8px #00f0ff;
  animation: cursorBlink 0.8s infinite;
  margin-left: 2px;
}

@keyframes cursorBlink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* 气泡尾巴 */
.bubble-tail {
  position: absolute;
  width: 0;
  height: 0;
}

.bubble-tail.tail-bottom {
  bottom: -8px;
  left: 50%;
  transform: translateX(-50%);
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-top: 8px solid rgba(30, 30, 45, 0.98);
}

.bubble-tail.tail-top {
  top: -8px;
  left: 50%;
  transform: translateX(-50%);
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-bottom: 8px solid rgba(30, 30, 45, 0.98);
}

.bubble-tail.tail-left {
  left: -8px;
  top: 50%;
  transform: translateY(-50%);
  border-top: 8px solid transparent;
  border-bottom: 8px solid transparent;
  border-right: 8px solid rgba(30, 30, 45, 0.98);
}

.bubble-tail.tail-right {
  right: -8px;
  top: 50%;
  transform: translateY(-50%);
  border-top: 8px solid transparent;
  border-bottom: 8px solid transparent;
  border-left: 8px solid rgba(30, 30, 45, 0.98);
}

/* 流式加载指示器 */
.streaming-indicator {
  position: absolute;
  bottom: 6px;
  right: 10px;
  display: flex;
  gap: 3px;
}

.streaming-indicator .dot {
  width: 4px;
  height: 4px;
  background: #00f0ff;
  border-radius: 50%;
  animation: dotPulse 1.4s ease-in-out infinite;
}

.streaming-indicator .dot:nth-child(2) {
  animation-delay: 0.2s;
}

.streaming-indicator .dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes dotPulse {
  0%, 80%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1.2);
    opacity: 1;
  }
}

/* 位置变体 - 可根据需要扩展具体样式 */
.position-top,
.position-bottom,
.position-left,
.position-right {
  /* 基础样式已在 .speech-bubble 中定义，这些类用于条件判断 */
  pointer-events: auto;
}

/* 滚动条 */
.speech-content::-webkit-scrollbar {
  width: 3px;
}

.speech-content::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 2px;
}

.speech-content::-webkit-scrollbar-thumb {
  background: rgba(0, 240, 255, 0.3);
  border-radius: 2px;
}

/* 响应式 */
@media (max-width: 768px) {
  .speech-bubble {
    max-width: 220px;
    min-width: 120px;
  }
  
  .bubble-content {
    padding: 10px 12px;
  }
  
  .speech-text {
    font-size: 12px;
  }
  
  .speech-content {
    max-height: 80px;
  }
}
</style>
