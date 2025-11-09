<template>
  <div class="ai-thinking-indicator">
    <div class="thinking-content">
      <div class="thinking-icon">
        <el-icon class="rotating"><Loading /></el-icon>
      </div>
      <div class="thinking-text">
        <div class="ai-name">{{ aiPlayerName }}</div>
        <div class="thinking-message">AI正在思考...</div>
      </div>
    </div>
    <div class="thinking-dots">
      <span class="dot"></span>
      <span class="dot"></span>
      <span class="dot"></span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'

const props = defineProps({
  aiPlayerId: {
    type: String,
    required: true
  },
  participants: {
    type: Array,
    default: () => []
  }
})

const aiPlayer = computed(() => {
  return props.participants.find(
    p => (p.player_id === props.aiPlayerId || `AI_${p.id}` === props.aiPlayerId) && p.is_ai_agent
  )
})

const aiPlayerName = computed(() => {
  if (!aiPlayer.value) return 'AI'
  return `AI-${aiPlayer.value.ai_personality}`
})
</script>

<style scoped>
.ai-thinking-indicator {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  animation: fadeIn 0.3s ease-in;
}

.thinking-content {
  display: flex;
  align-items: center;
  gap: 15px;
  color: white;
}

.thinking-icon {
  font-size: 36px;
}

.rotating {
  animation: rotate 2s linear infinite;
}

.thinking-text {
  flex: 1;
}

.ai-name {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 5px;
}

.thinking-message {
  font-size: 14px;
  opacity: 0.9;
}

.thinking-dots {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-top: 10px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: white;
  animation: bounce 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) {
  animation-delay: -0.32s;
}

.dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* Responsive */
@media (max-width: 768px) {
  .ai-thinking-indicator {
    padding: 15px;
  }

  .thinking-icon {
    font-size: 28px;
  }

  .ai-name {
    font-size: 16px;
  }
}
</style>
