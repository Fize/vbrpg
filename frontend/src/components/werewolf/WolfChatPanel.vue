<template>
  <div class="wolf-chat-panel" v-if="isVisible">
    <div class="panel-header">
      <span class="header-icon">🐺</span>
      <span class="header-title">狼人私密讨论</span>
    </div>
    
    <!-- 狼队友信息 -->
    <div class="teammates-info">
      <span class="label">狼队友：</span>
      <span 
        v-for="teammate in teammates" 
        :key="teammate.seat_number"
        class="teammate-tag"
      >
        {{ teammate.seat_number }}号 {{ teammate.player_name }}
      </span>
      <span v-if="teammates.length === 0" class="no-teammate">
        你是唯一的狼人
      </span>
    </div>
    
    <!-- 讨论消息列表 -->
    <div class="chat-messages" ref="messagesContainer">
      <div 
        v-for="msg in messages" 
        :key="msg.id"
        class="message"
        :class="{ 'my-message': msg.seat_number === mySeatNumber }"
      >
        <span class="sender">{{ msg.seat_number }}号 {{ msg.sender_name }}：</span>
        <span class="content">{{ msg.content }}</span>
      </div>
      <div v-if="messages.length === 0" class="no-messages">
        暂无讨论消息，开始与狼队友沟通吧
      </div>
    </div>
    
    <!-- 输入区域 -->
    <div class="chat-input" v-if="isChatEnabled">
      <input
        v-model="inputText"
        type="text"
        placeholder="与狼队友讨论..."
        @keyup.enter="sendMessage"
        :disabled="isSending"
        class="message-input"
      />
      <button 
        @click="sendMessage" 
        :disabled="!inputText.trim() || isSending"
        class="send-button"
      >
        {{ isSending ? '发送中...' : '发送' }}
      </button>
    </div>
    
    <!-- 目标选择区域 -->
    <div class="target-selection" v-if="showTargetSelection">
      <div class="selection-label">选择击杀目标：</div>
      <div class="target-options">
        <button
          v-for="target in killTargets"
          :key="target.seat_number ?? 'skip'"
          @click="selectTarget(target)"
          :class="{
            'target-button': true,
            'selected': selectedTarget?.seat_number === target.seat_number,
            'skip-button': target.seat_number === null
          }"
        >
          {{ target.seat_number !== null ? `${target.seat_number}号` : '空刀' }}
        </button>
      </div>
      <button 
        @click="confirmKill" 
        :disabled="selectedTarget === null"
        class="confirm-button"
      >
        确认击杀
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useGameStore } from '@/stores/game'
import { useSocketStore } from '@/stores/socket'

const gameStore = useGameStore()
const socketStore = useSocketStore()

// Props
const props = defineProps({
  roomCode: {
    type: String,
    required: true
  },
  showTargetSelection: {
    type: Boolean,
    default: false
  },
  killTargets: {
    type: Array,
    default: () => []
  }
})

// Emits
const emit = defineEmits(['select-target', 'confirm-kill'])

// 本地状态
const inputText = ref('')
const isSending = ref(false)
const selectedTarget = ref(null)
const messagesContainer = ref(null)

// 计算属性
const isVisible = computed(() => {
  return gameStore.isWerewolf && (
    gameStore.currentPhase === 'night_werewolf' ||
    gameStore.nightActionType === 'werewolf_kill'
  )
})

const isChatEnabled = computed(() => {
  return gameStore.isWolfChatEnabled
})

const teammates = computed(() => {
  return gameStore.werewolfTeammates || []
})

const messages = computed(() => {
  return gameStore.wolfChatMessages || []
})

const mySeatNumber = computed(() => {
  return gameStore.mySeatNumber
})

// 方法
async function sendMessage() {
  if (!inputText.value.trim() || isSending.value) return
  
  const content = inputText.value.trim()
  isSending.value = true
  
  try {
    await socketStore.sendWolfChatMessage(props.roomCode, content)
    inputText.value = ''
  } catch (error) {
    console.error('发送狼人讨论消息失败:', error)
  } finally {
    isSending.value = false
  }
}

function selectTarget(target) {
  selectedTarget.value = target
  emit('select-target', target)
}

function confirmKill() {
  if (selectedTarget.value !== null) {
    emit('confirm-kill', selectedTarget.value)
  }
}

// 监听消息变化，自动滚动到底部
watch(messages, async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}, { deep: true })
</script>

<style scoped>
.wolf-chat-panel {
  background: linear-gradient(135deg, #2a1a3d 0%, #1a0a2d 100%);
  border: 2px solid #8b0000;
  border-radius: 12px;
  padding: 16px;
  color: #fff;
  box-shadow: 0 4px 20px rgba(139, 0, 0, 0.3);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(139, 0, 0, 0.5);
}

.header-icon {
  font-size: 24px;
}

.header-title {
  font-size: 18px;
  font-weight: bold;
  color: #ff6b6b;
}

.teammates-info {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
}

.label {
  color: #aaa;
}

.teammate-tag {
  background: rgba(139, 0, 0, 0.5);
  padding: 4px 10px;
  border-radius: 16px;
  font-size: 13px;
}

.no-teammate {
  color: #888;
  font-style: italic;
}

.chat-messages {
  max-height: 200px;
  overflow-y: auto;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.message {
  margin-bottom: 8px;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
}

.message.my-message {
  background: rgba(139, 0, 0, 0.3);
  border-left: 3px solid #8b0000;
}

.sender {
  font-weight: bold;
  color: #ff9999;
  margin-right: 4px;
}

.content {
  color: #ddd;
}

.no-messages {
  text-align: center;
  color: #666;
  font-style: italic;
  padding: 20px;
}

.chat-input {
  display: flex;
  gap: 8px;
}

.message-input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid rgba(139, 0, 0, 0.5);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.3);
  color: #fff;
  font-size: 14px;
}

.message-input:focus {
  outline: none;
  border-color: #8b0000;
}

.message-input::placeholder {
  color: #666;
}

.send-button {
  padding: 10px 20px;
  background: linear-gradient(135deg, #8b0000, #5a0000);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
}

.send-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #a50000, #6a0000);
  transform: translateY(-1px);
}

.send-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.target-selection {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(139, 0, 0, 0.5);
}

.selection-label {
  margin-bottom: 12px;
  font-weight: bold;
  color: #ff6b6b;
}

.target-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.target-button {
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(139, 0, 0, 0.5);
  border-radius: 6px;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s;
}

.target-button:hover {
  background: rgba(139, 0, 0, 0.3);
  border-color: #8b0000;
}

.target-button.selected {
  background: #8b0000;
  border-color: #ff6b6b;
}

.target-button.skip-button {
  border-style: dashed;
  color: #aaa;
}

.confirm-button {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #8b0000, #5a0000);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
}

.confirm-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #a50000, #6a0000);
}

.confirm-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
