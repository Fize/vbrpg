<template>
  <div class="game-log">
    <div class="log-header">
      <h3 class="log-title">游戏日志</h3>
      <el-button text size="small" @click="scrollToBottom">
        <el-icon><Bottom /></el-icon>
      </el-button>
    </div>
    
    <div class="log-content" ref="logContentRef">
      <div 
        v-for="(entry, index) in logs"
        :key="entry.id || index"
        class="log-entry"
        :class="[
          `type-${entry.type}`, 
          { 
            'is-system': entry.is_system,
            'is-streaming': entry.isStreaming,
            'is-host': entry.type === 'host_announcement'
          }
        ]"
      >
        <!-- 时间标记 -->
        <div v-if="showDayMarker(index)" class="day-marker">
          <span class="day-text">第 {{ entry.day }} 天 - {{ entry.phase_name }}</span>
        </div>
        
        <!-- 主持人发言 -->
        <div v-if="entry.type === 'host_announcement'" class="host-entry">
          <div class="host-header">
            <el-icon class="host-icon"><Microphone /></el-icon>
            <span class="host-label">主持人</span>
          </div>
          <div class="host-content">
            <span class="host-message">{{ entry.content }}</span>
            <span v-if="entry.isStreaming" class="typing-cursor">|</span>
          </div>
        </div>
        
        <!-- 玩家发言（流式） -->
        <div v-else-if="entry.type === 'speech'" class="speech-entry">
          <div class="speech-header">
            <span class="speaker-name">{{ entry.player_name }}</span>
            <span v-if="entry.time" class="entry-time">{{ formatTime(entry.time) }}</span>
          </div>
          <div class="speech-content">
            <span class="speech-message">{{ entry.content }}</span>
            <span v-if="entry.isStreaming" class="typing-cursor">|</span>
          </div>
        </div>
        
        <!-- 其他类型日志 -->
        <div v-else class="entry-content">
          <span v-if="entry.time" class="entry-time">{{ formatTime(entry.time) }}</span>
          <span class="entry-icon">
            <el-icon v-if="entry.type === 'death'"><Close /></el-icon>
            <el-icon v-else-if="entry.type === 'vote' || entry.type === 'vote_result'"><Stamp /></el-icon>
            <el-icon v-else-if="entry.type === 'action'"><Aim /></el-icon>
            <el-icon v-else-if="entry.type === 'skill' || entry.type === 'seer_result'"><MagicStick /></el-icon>
            <el-icon v-else-if="entry.type === 'hunter_shoot'"><Aim /></el-icon>
            <el-icon v-else-if="entry.type === 'game_end'"><Trophy /></el-icon>
            <el-icon v-else><InfoFilled /></el-icon>
          </span>
          <span class="entry-message" v-html="formatMessage(entry)"></span>
        </div>
      </div>
      
      <!-- 空状态 -->
      <div v-if="logs.length === 0" class="empty-log">
        <el-icon :size="40"><DocumentCopy /></el-icon>
        <span>暂无日志</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { 
  Bottom, Close, Stamp, ChatDotRound, 
  Aim, MagicStick, InfoFilled, DocumentCopy,
  Microphone, Trophy
} from '@element-plus/icons-vue'

const props = defineProps({
  logs: {
    type: Array,
    default: () => []
  },
  autoScroll: {
    type: Boolean,
    default: true
  }
})

const logContentRef = ref(null)
const userScrolled = ref(false) // 用户是否手动滚动
let scrollTimeout = null

// 检查是否在底部附近（允许50px误差）
function isNearBottom() {
  if (!logContentRef.value) return true
  const { scrollTop, scrollHeight, clientHeight } = logContentRef.value
  return scrollHeight - scrollTop - clientHeight < 50
}

// 处理用户滚动
function handleScroll() {
  // 清除之前的定时器
  if (scrollTimeout) {
    clearTimeout(scrollTimeout)
  }
  
  // 如果用户向上滚动，标记为用户滚动
  if (!isNearBottom()) {
    userScrolled.value = true
  }
  
  // 如果用户滚动到底部，5秒后恢复自动滚动
  if (isNearBottom()) {
    scrollTimeout = setTimeout(() => {
      userScrolled.value = false
    }, 5000)
  }
}

// 滚动到底部
function scrollToBottom() {
  if (logContentRef.value) {
    logContentRef.value.scrollTop = logContentRef.value.scrollHeight
    userScrolled.value = false
  }
}

// 是否显示天数标记
function showDayMarker(index) {
  if (index === 0) return true
  const current = props.logs[index]
  const prev = props.logs[index - 1]
  return current.day !== prev.day || current.phase !== prev.phase
}

// 格式化时间
function formatTime(time) {
  if (!time) return ''
  const date = new Date(time)
  return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
}

// 格式化消息
function formatMessage(entry) {
  let message = entry.message || ''
  
  // 高亮玩家名称
  if (entry.player_name) {
    message = message.replace(
      entry.player_name, 
      `<span class="player-name">${entry.player_name}</span>`
    )
  }
  
  // 高亮目标名称
  if (entry.target_name) {
    message = message.replace(
      entry.target_name,
      `<span class="target-name">${entry.target_name}</span>`
    )
  }
  
  return message
}

// 自动滚动 - 只在用户没有手动滚动时才自动滚动
watch(() => props.logs.length, () => {
  if (props.autoScroll && !userScrolled.value) {
    nextTick(scrollToBottom)
  }
})

// 监听滚动事件
onMounted(() => {
  if (logContentRef.value) {
    logContentRef.value.addEventListener('scroll', handleScroll)
  }
})

onUnmounted(() => {
  if (logContentRef.value) {
    logContentRef.value.removeEventListener('scroll', handleScroll)
  }
  if (scrollTimeout) {
    clearTimeout(scrollTimeout)
  }
})

// 暴露方法
defineExpose({
  scrollToBottom
})
</script>

<style scoped>
.game-log {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: rgba(10, 10, 20, .9);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  border: 1px solid rgba(0, 240, 255, .2);
  overflow: hidden;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  background: rgba(0, 240, 255, .05);
  border-bottom: 1px solid rgba(0, 240, 255, .2);
}

.log-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-primary);
  text-transform: uppercase;
  letter-spacing: 2px;
  margin: 0;
}

.log-header .el-button {
  color: var(--color-text-secondary);
}

.log-header .el-button:hover {
  color: var(--color-primary);
}

.log-content {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
}

.day-marker {
  text-align: center;
  margin: 18px 0 14px;
  position: relative;
}

.day-marker:first-child {
  margin-top: 0;
}

.day-marker:before,
.day-marker:after {
  content: '';
  position: absolute;
  top: 50%;
  height: 1px;
  width: calc(50% - 80px);
  background: linear-gradient(90deg, transparent, rgba(0, 240, 255, .3));
}

.day-marker:before {
  left: 0;
}

.day-marker:after {
  right: 0;
  background: linear-gradient(90deg, rgba(0, 240, 255, .3), transparent);
}

.day-text {
  display: inline-block;
  padding: 5px 18px;
  background: linear-gradient(135deg, rgba(0, 240, 255, .15), rgba(168, 85, 247, .15));
  border: 1px solid rgba(0, 240, 255, .3);
  color: var(--color-primary);
  font-size: 11px;
  font-weight: 600;
  border-radius: 20px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.log-entry {
  margin-bottom: 10px;
}

.entry-content {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  background: rgba(0, 240, 255, .05);
  border-radius: 10px;
  border: 1px solid rgba(0, 240, 255, .1);
  font-size: 12px;
  line-height: 1.6;
}

.entry-time {
  color: var(--color-text-secondary);
  font-size: 10px;
  white-space: nowrap;
  font-family: 'Courier New', monospace;
}

.entry-icon {
  flex-shrink: 0;
  color: var(--color-text-secondary);
}

.entry-message {
  flex: 1;
  color: var(--color-text-regular);
}

/* 消息类型样式 */
.log-entry.type-death .entry-content {
  background: rgba(255, 51, 102, .1);
  border-color: rgba(255, 51, 102, .2);
}

.log-entry.type-death .entry-icon {
  color: #ff3366;
}

.log-entry.type-vote .entry-content,
.log-entry.type-vote_result .entry-content {
  background: rgba(255, 170, 0, .1);
  border-color: rgba(255, 170, 0, .2);
}

.log-entry.type-vote .entry-icon,
.log-entry.type-vote_result .entry-icon {
  color: #ffaa00;
}

.log-entry.type-speech .entry-content {
  background: rgba(0, 255, 136, .1);
  border-color: rgba(0, 255, 136, .2);
}

.log-entry.type-speech .entry-icon {
  color: #00ff88;
}

.log-entry.type-skill .entry-content,
.log-entry.type-seer_result .entry-content {
  background: rgba(0, 170, 255, .1);
  border-color: rgba(0, 170, 255, .2);
}

.log-entry.type-skill .entry-icon,
.log-entry.type-seer_result .entry-icon {
  color: #00aaff;
}

.log-entry.type-game_end .entry-content {
  background: rgba(168, 85, 247, .1);
  border-color: rgba(168, 85, 247, .3);
}

.log-entry.type-game_end .entry-icon {
  color: #a855f7;
}

.log-entry.is-system .entry-content {
  background: rgba(100, 100, 120, .1);
  border-left: 3px solid rgba(100, 100, 120, .4);
}

/* 主持人发言样式 */
.host-entry {
  background: linear-gradient(135deg, rgba(168, 85, 247, .1), rgba(0, 240, 255, .1));
  border: 1px solid rgba(168, 85, 247, .3);
  border-radius: 12px;
  padding: 14px 18px;
  margin: 10px 0;
  position: relative;
  overflow: hidden;
}

.host-entry:before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, #a855f7, #00f0ff);
}

.host-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.host-icon {
  color: #a855f7;
  font-size: 18px;
  text-shadow: 0 0 10px #a855f7;
}

.host-label {
  color: #a855f7;
  font-weight: 700;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.host-content {
  color: var(--color-text-primary);
  font-size: 13px;
  line-height: 1.7;
}

.host-message {
  white-space: pre-wrap;
}

/* 玩家发言样式 */
.speech-entry {
  background: rgba(0, 255, 136, .08);
  border: 1px solid rgba(0, 255, 136, .25);
  border-radius: 12px;
  padding: 14px 18px;
  margin: 10px 0;
}

.speech-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.speaker-name {
  color: #00ff88;
  font-weight: 700;
  font-size: 12px;
  text-shadow: 0 0 10px rgba(0, 255, 136, .5);
}

.speech-content {
  color: var(--color-text-primary);
  font-size: 13px;
  line-height: 1.7;
}

.speech-message {
  white-space: pre-wrap;
}

/* 打字光标动画 */
.typing-cursor {
  display: inline-block;
  color: var(--color-primary);
  font-weight: bold;
  animation: blink .8s infinite;
  text-shadow: 0 0 10px var(--color-primary);
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* 流式状态样式 */
.log-entry.is-streaming .host-entry,
.log-entry.is-streaming .speech-entry {
  border-left: 3px solid var(--color-primary);
  box-shadow: 0 0 15px rgba(0, 240, 255, .2);
}

/* 高亮文本 */
.entry-message :deep(.player-name) {
  color: var(--color-primary);
  font-weight: 600;
  text-shadow: 0 0 8px var(--color-primary);
}

.entry-message :deep(.target-name) {
  color: #ff3366;
  font-weight: 600;
  text-shadow: 0 0 8px rgba(255, 51, 102, .5);
}

.empty-log {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--color-text-secondary);
  gap: 14px;
}

.empty-log .el-icon {
  opacity: .5;
}

/* 滚动条样式 */
.log-content::-webkit-scrollbar {
  width: 6px;
}

.log-content::-webkit-scrollbar-track {
  background: rgba(0, 240, 255, .05);
}

.log-content::-webkit-scrollbar-thumb {
  background: rgba(0, 240, 255, .2);
  border-radius: 3px;
}

.log-content::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 240, 255, .4);
}

/* 响应式 */
@media (max-width: 768px) {
  .log-header {
    padding: 10px 14px;
  }
  
  .log-content {
    padding: 10px;
  }
  
  .entry-content {
    padding: 8px 12px;
    font-size: 11px;
  }
  
  .host-entry,
  .speech-entry {
    padding: 12px 14px;
  }
}
</style>
