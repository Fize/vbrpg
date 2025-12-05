<template>
  <div class="last-words-panel" v-if="isVisible">
    <div class="panel-header">
      <span class="header-icon">💀</span>
      <span class="header-title">遗言时刻</span>
      <span class="death-reason" v-if="deathReasonText">
        {{ deathReasonText }}
      </span>
    </div>
    
    <!-- 倒计时 -->
    <div class="countdown-section" v-if="remainingTime > 0">
      <div class="countdown-bar">
        <div 
          class="countdown-progress" 
          :style="{ width: `${(remainingTime / timeout) * 100}%` }"
          :class="{ 'warning': remainingTime <= 10 }"
        ></div>
      </div>
      <span class="countdown-text">
        剩余 {{ remainingTime }} 秒
      </span>
    </div>
    
    <!-- 预设选项 -->
    <div class="options-section" v-if="options.length > 0">
      <div class="section-label">选择遗言：</div>
      <div class="options-list">
        <button
          v-for="option in filteredOptions"
          :key="option.id"
          @click="selectOption(option)"
          :class="{
            'option-button': true,
            'selected': selectedOption?.id === option.id,
            'skip-option': option.type === 'skip'
          }"
        >
          {{ option.text }}
        </button>
      </div>
    </div>
    
    <!-- 自由输入 -->
    <div class="custom-input-section">
      <div class="section-label">或自由输入遗言：</div>
      <textarea
        v-model="customContent"
        placeholder="输入你想说的遗言..."
        :disabled="isSubmitting"
        class="custom-textarea"
        rows="3"
      ></textarea>
    </div>
    
    <!-- 目标选择（如果需要） -->
    <div class="target-selection" v-if="needsTarget">
      <div class="section-label">选择提及的玩家：</div>
      <div class="target-options">
        <button
          v-for="target in targetOptions"
          :key="target.seat_number"
          @click="selectTarget(target)"
          :class="{
            'target-button': true,
            'selected': selectedTarget?.seat_number === target.seat_number
          }"
        >
          {{ target.seat_number }}号
        </button>
      </div>
    </div>
    
    <!-- 操作按钮 -->
    <div class="action-buttons">
      <button 
        @click="skipLastWords" 
        :disabled="isSubmitting"
        class="skip-button"
      >
        跳过遗言
      </button>
      <button 
        @click="submitLastWords" 
        :disabled="!canSubmit || isSubmitting"
        class="submit-button"
      >
        {{ isSubmitting ? '提交中...' : '发表遗言' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
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
  gameId: {
    type: String,
    default: ''
  }
})

// Emits
const emit = defineEmits(['last-words-submitted', 'last-words-skipped'])

// 本地状态
const customContent = ref('')
const selectedOption = ref(null)
const selectedTarget = ref(null)
const isSubmitting = ref(false)
const remainingTime = ref(0)
let countdownTimer = null

// 计算属性
const isVisible = computed(() => {
  return gameStore.isLastWordsPhase && 
         gameStore.lastWordsSeat === gameStore.mySeatNumber
})

const options = computed(() => {
  return gameStore.lastWordsOptions || []
})

const timeout = computed(() => {
  return gameStore.lastWordsTimeout || 60
})

const deathReasonText = computed(() => {
  const reason = gameStore.lastWordsDeathReason
  const reasonMap = {
    'night_kill': '你昨夜被狼人杀害',
    'vote': '你被放逐出局',
    'poison': '你被女巫毒杀',
    'hunter_shot': '你被猎人带走'
  }
  return reasonMap[reason] || ''
})

const filteredOptions = computed(() => {
  // 过滤掉需要目标但还没选择目标的选项（除非已经选了目标）
  return options.value.filter(opt => {
    if (opt.needs_target && !selectedTarget.value) {
      return true // 显示但需要选择目标才能使用
    }
    return true
  })
})

const needsTarget = computed(() => {
  return selectedOption.value?.needs_target && !selectedTarget.value
})

const targetOptions = computed(() => {
  // 获取所有存活玩家（排除自己）
  const players = Object.values(gameStore.playerStates || {})
  return players
    .filter(p => p.is_alive && p.seat_number !== gameStore.mySeatNumber)
    .map(p => ({
      seat_number: p.seat_number,
      player_name: p.player_name || `玩家${p.seat_number}`
    }))
})

const canSubmit = computed(() => {
  if (customContent.value.trim()) {
    return true
  }
  if (selectedOption.value) {
    if (selectedOption.value.needs_target) {
      return selectedTarget.value !== null
    }
    return true
  }
  return false
})

// 方法
function selectOption(option) {
  selectedOption.value = option
  customContent.value = ''
  
  if (!option.needs_target) {
    selectedTarget.value = null
  }
}

function selectTarget(target) {
  selectedTarget.value = target
}

function getFinalContent() {
  if (customContent.value.trim()) {
    return customContent.value.trim()
  }
  
  if (selectedOption.value) {
    let text = selectedOption.value.text
    if (selectedOption.value.needs_target && selectedTarget.value) {
      text = text.replace('X号', `${selectedTarget.value.seat_number}号`)
    }
    return text
  }
  
  return ''
}

async function submitLastWords() {
  if (!canSubmit.value || isSubmitting.value) return
  
  const content = getFinalContent()
  isSubmitting.value = true
  
  try {
    socketStore.submitLastWords(props.roomCode, props.gameId, content)
    emit('last-words-submitted', content)
    
    // 清除状态
    stopCountdown()
    gameStore.clearLastWordsState()
  } catch (error) {
    console.error('提交遗言失败:', error)
  } finally {
    isSubmitting.value = false
  }
}

async function skipLastWords() {
  if (isSubmitting.value) return
  
  isSubmitting.value = true
  
  try {
    socketStore.submitLastWords(props.roomCode, props.gameId, '')
    emit('last-words-skipped')
    
    // 清除状态
    stopCountdown()
    gameStore.clearLastWordsState()
  } catch (error) {
    console.error('跳过遗言失败:', error)
  } finally {
    isSubmitting.value = false
  }
}

function startCountdown() {
  remainingTime.value = timeout.value
  
  countdownTimer = setInterval(() => {
    remainingTime.value -= 1
    
    if (remainingTime.value <= 0) {
      stopCountdown()
      // 超时自动跳过
      skipLastWords()
    }
  }, 1000)
}

function stopCountdown() {
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
}

// 监听阶段变化
watch(isVisible, (newVal) => {
  if (newVal) {
    startCountdown()
    // 重置状态
    customContent.value = ''
    selectedOption.value = null
    selectedTarget.value = null
  } else {
    stopCountdown()
  }
})

// 生命周期
onMounted(() => {
  if (isVisible.value) {
    startCountdown()
  }
})

onUnmounted(() => {
  stopCountdown()
})
</script>

<style scoped>
.last-words-panel {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border: 2px solid #4a4a6a;
  border-radius: 12px;
  padding: 20px;
  color: #fff;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.header-icon {
  font-size: 28px;
}

.header-title {
  font-size: 20px;
  font-weight: bold;
  color: #e74c3c;
}

.death-reason {
  margin-left: auto;
  font-size: 14px;
  color: #999;
  font-style: italic;
}

.countdown-section {
  margin-bottom: 16px;
}

.countdown-bar {
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 6px;
}

.countdown-progress {
  height: 100%;
  background: linear-gradient(90deg, #3498db, #2980b9);
  border-radius: 3px;
  transition: width 1s linear;
}

.countdown-progress.warning {
  background: linear-gradient(90deg, #e74c3c, #c0392b);
}

.countdown-text {
  font-size: 13px;
  color: #aaa;
}

.section-label {
  font-size: 14px;
  color: #bbb;
  margin-bottom: 10px;
}

.options-section {
  margin-bottom: 16px;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.option-button {
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #ddd;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.option-button:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

.option-button.selected {
  background: rgba(52, 152, 219, 0.2);
  border-color: #3498db;
  color: #fff;
}

.option-button.skip-option {
  border-style: dashed;
  color: #888;
}

.custom-input-section {
  margin-bottom: 16px;
}

.custom-textarea {
  width: 100%;
  padding: 12px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  resize: vertical;
  font-family: inherit;
}

.custom-textarea:focus {
  outline: none;
  border-color: #3498db;
}

.custom-textarea::placeholder {
  color: #666;
}

.target-selection {
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.target-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.target-button {
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s;
}

.target-button:hover {
  background: rgba(52, 152, 219, 0.2);
}

.target-button.selected {
  background: #3498db;
  border-color: #3498db;
}

.action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.skip-button {
  flex: 1;
  padding: 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: #999;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.skip-button:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
}

.skip-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.submit-button {
  flex: 2;
  padding: 12px;
  background: linear-gradient(135deg, #3498db, #2980b9);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
}

.submit-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #4aa3df, #3498db);
  transform: translateY(-1px);
}

.submit-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
