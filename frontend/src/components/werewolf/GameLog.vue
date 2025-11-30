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
import { ref, watch, nextTick } from 'vue'
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

// 滚动到底部
function scrollToBottom() {
  if (logContentRef.value) {
    logContentRef.value.scrollTop = logContentRef.value.scrollHeight
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

// 自动滚动
watch(() => props.logs.length, () => {
  if (props.autoScroll) {
    nextTick(scrollToBottom)
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
  background: white;
  border-radius: 12px;
  overflow: hidden;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
}

.log-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.log-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.day-marker {
  text-align: center;
  margin: 16px 0 12px;
}

.day-marker:first-child {
  margin-top: 0;
}

.day-text {
  display: inline-block;
  padding: 4px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-size: 12px;
  font-weight: 500;
  border-radius: 12px;
}

.log-entry {
  margin-bottom: 8px;
}

.entry-content {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 12px;
  background: #f9fafc;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
}

.entry-time {
  color: #909399;
  font-size: 11px;
  white-space: nowrap;
}

.entry-icon {
  flex-shrink: 0;
  color: #909399;
}

.entry-message {
  flex: 1;
  color: #606266;
}

/* 消息类型样式 */
.log-entry.type-death .entry-content {
  background: #fef0f0;
}

.log-entry.type-death .entry-icon {
  color: #f56c6c;
}

.log-entry.type-vote .entry-content {
  background: #fdf6ec;
}

.log-entry.type-vote .entry-icon {
  color: #e6a23c;
}

.log-entry.type-speech .entry-content {
  background: #f0f9eb;
}

.log-entry.type-speech .entry-icon {
  color: #67c23a;
}

.log-entry.type-skill .entry-content {
  background: #ecf5ff;
}

.log-entry.type-skill .entry-icon {
  color: #409eff;
}

.log-entry.is-system .entry-content {
  background: #f5f7fa;
  border-left: 3px solid #909399;
}

/* 主持人发言样式 */
.host-entry {
  background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
  border: 1px solid #667eea30;
  border-radius: 12px;
  padding: 12px 16px;
  margin: 8px 0;
}

.host-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.host-icon {
  color: #667eea;
  font-size: 18px;
}

.host-label {
  color: #667eea;
  font-weight: 600;
  font-size: 14px;
}

.host-content {
  color: #303133;
  font-size: 14px;
  line-height: 1.6;
}

.host-message {
  white-space: pre-wrap;
}

/* 玩家发言样式 */
.speech-entry {
  background: #f0f9eb;
  border-radius: 12px;
  padding: 12px 16px;
  margin: 8px 0;
}

.speech-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.speaker-name {
  color: #67c23a;
  font-weight: 600;
  font-size: 14px;
}

.speech-content {
  color: #303133;
  font-size: 14px;
  line-height: 1.6;
}

.speech-message {
  white-space: pre-wrap;
}

/* 打字光标动画 */
.typing-cursor {
  display: inline-block;
  color: var(--el-color-primary);
  font-weight: bold;
  animation: blink 0.8s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* 流式状态样式 */
.log-entry.is-streaming .host-entry,
.log-entry.is-streaming .speech-entry {
  border-left: 3px solid var(--el-color-primary);
}

/* 高亮文本 */
.entry-message :deep(.player-name) {
  color: var(--el-color-primary);
  font-weight: 500;
}

.entry-message :deep(.target-name) {
  color: var(--el-color-danger);
  font-weight: 500;
}

.empty-log {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #c0c4cc;
  gap: 12px;
}

/* 滚动条样式 */
.log-content::-webkit-scrollbar {
  width: 6px;
}

.log-content::-webkit-scrollbar-thumb {
  background: #dcdfe6;
  border-radius: 3px;
}

.log-content::-webkit-scrollbar-thumb:hover {
  background: #c0c4cc;
}

/* 响应式 */
@media (max-width: 768px) {
  .log-header {
    padding: 10px 12px;
  }
  
  .log-content {
    padding: 8px;
  }
  
  .entry-content {
    padding: 6px 10px;
    font-size: 12px;
  }
}
</style>
