<template>
  <!-- F12-F16: 常驻主持人公告面板 -->
  <div class="host-announcement-panel" :class="{ expanded: isHistoryExpanded }">
    <!-- 面板标题栏 -->
    <div class="panel-header">
      <div class="header-left">
        <el-icon class="host-icon"><Microphone /></el-icon>
        <span class="panel-title">主持人</span>
        <el-badge v-if="unreadCount > 0" :value="unreadCount" class="unread-badge" />
      </div>
      <div class="header-right">
        <!-- 历史折叠按钮 -->
        <el-button
          type="text"
          size="small"
          @click="toggleHistory"
          class="history-toggle"
        >
          <el-icon><component :is="isHistoryExpanded ? 'ArrowUp' : 'ArrowDown'" /></el-icon>
          {{ isHistoryExpanded ? '收起历史' : `历史 (${historyCount})` }}
        </el-button>
      </div>
    </div>

    <!-- 当前公告内容区 -->
    <div class="current-announcement">
      <div v-if="currentAnnouncement.content || currentAnnouncement.isStreaming" class="announcement-content">
        <div class="announcement-type-tag" v-if="currentAnnouncement.type">
          {{ getTypeLabel(currentAnnouncement.type) }}
        </div>
        <p class="announcement-text">
          {{ currentAnnouncement.content }}
          <span v-if="currentAnnouncement.isStreaming" class="typing-cursor">|</span>
        </p>
      </div>
      <div v-else class="no-announcement">
        <span class="placeholder">等待主持人公告...</span>
      </div>
    </div>

    <!-- 历史公告区（可折叠） -->
    <el-collapse-transition>
      <div v-if="isHistoryExpanded" class="history-section">
        <div class="history-divider">
          <span>历史公告</span>
        </div>
        <div class="history-list" ref="historyListRef">
          <div
            v-for="(item, index) in displayedHistory"
            :key="index"
            class="history-item"
          >
            <div class="history-meta">
              <span class="history-type">{{ getTypeLabel(item.type) }}</span>
              <span class="history-time">第{{ item.day }}天</span>
            </div>
            <p class="history-content">{{ truncateContent(item.content) }}</p>
          </div>
          <!-- 加载更多 -->
          <div v-if="hasMoreHistory" class="load-more">
            <el-button type="text" size="small" @click="loadMoreHistory">
              加载更多...
            </el-button>
          </div>
          <!-- 空状态 -->
          <div v-if="announcementHistory.length === 0" class="empty-history">
            暂无历史公告
          </div>
        </div>
      </div>
    </el-collapse-transition>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { Microphone, ArrowUp, ArrowDown } from '@element-plus/icons-vue'

// Props 定义
const props = defineProps({
  /**
   * 当前公告
   */
  currentAnnouncement: {
    type: Object,
    default: () => ({
      type: null,
      content: '',
      isStreaming: false
    })
  },
  /**
   * 历史公告列表
   */
  announcementHistory: {
    type: Array,
    default: () => []
  }
})

// 状态
const isHistoryExpanded = ref(false)
const displayCount = ref(5) // 初始显示数量
const unreadCount = ref(0)
const historyListRef = ref(null)

// 计算属性
const historyCount = computed(() => props.announcementHistory.length)

const displayedHistory = computed(() => {
  // 倒序显示（最新的在前）
  const reversed = [...props.announcementHistory].reverse()
  return reversed.slice(0, displayCount.value)
})

const hasMoreHistory = computed(() => {
  return displayCount.value < props.announcementHistory.length
})

// 监听新公告
watch(() => props.announcementHistory.length, (newLen, oldLen) => {
  if (newLen > oldLen && !isHistoryExpanded.value) {
    unreadCount.value += (newLen - oldLen)
  }
})

// 方法
function toggleHistory() {
  isHistoryExpanded.value = !isHistoryExpanded.value
  if (isHistoryExpanded.value) {
    unreadCount.value = 0
  }
}

function loadMoreHistory() {
  displayCount.value += 5
}

function getTypeLabel(type) {
  const typeMap = {
    game_start: '游戏开始',
    night_start: '夜幕降临',
    dawn: '天亮了',
    discussion_start: '讨论开始',
    discussion_end: '讨论结束',
    vote_start: '投票开始',
    vote_result: '投票结果',
    hunter_shoot: '猎人开枪',
    game_end: '游戏结束',
    werewolf_action: '狼人行动',
    seer_action: '预言家行动',
    witch_action: '女巫行动',
    request_speech: '点名发言',
    speech_end_transition: '发言结束',
    death_announcement: '死亡公告'
  }
  return typeMap[type] || type || '公告'
}

function truncateContent(content, maxLength = 80) {
  if (!content) return ''
  if (content.length <= maxLength) return content
  return content.substring(0, maxLength) + '...'
}
</script>

<style scoped>
.host-announcement-panel {
  background: linear-gradient(135deg, rgba(15, 15, 25, 0.98), rgba(10, 10, 20, 0.98));
  border: 1px solid rgba(168, 85, 247, 0.3);
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.host-announcement-panel.expanded {
  border-color: rgba(168, 85, 247, 0.5);
  box-shadow: 0 8px 32px rgba(168, 85, 247, 0.2);
}

/* 面板标题栏 */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: rgba(168, 85, 247, 0.1);
  border-bottom: 1px solid rgba(168, 85, 247, 0.2);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.host-icon {
  font-size: 20px;
  color: #a855f7;
  text-shadow: 0 0 10px rgba(168, 85, 247, 0.5);
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #a855f7;
  letter-spacing: 1px;
}

.unread-badge {
  margin-left: 4px;
}

.history-toggle {
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
}

.history-toggle:hover {
  color: #a855f7;
}

/* 当前公告区 */
.current-announcement {
  padding: 16px;
  min-height: 60px;
}

.announcement-content {
  position: relative;
}

.announcement-type-tag {
  display: inline-block;
  font-size: 10px;
  padding: 2px 8px;
  background: rgba(168, 85, 247, 0.15);
  border: 1px solid rgba(168, 85, 247, 0.3);
  border-radius: 10px;
  color: #a855f7;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.announcement-text {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.95);
  white-space: pre-wrap;
  word-break: break-word;
}

.typing-cursor {
  display: inline-block;
  font-weight: bold;
  color: #a855f7;
  text-shadow: 0 0 10px #a855f7;
  animation: cursorBlink 0.8s infinite;
  margin-left: 2px;
}

@keyframes cursorBlink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.no-announcement {
  text-align: center;
  padding: 20px 0;
}

.placeholder {
  color: rgba(255, 255, 255, 0.4);
  font-size: 13px;
  font-style: italic;
}

/* 历史公告区 */
.history-section {
  border-top: 1px solid rgba(168, 85, 247, 0.2);
}

.history-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  background: rgba(168, 85, 247, 0.05);
}

.history-divider span {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 2px;
}

.history-list {
  max-height: 300px;
  overflow-y: auto;
  padding: 8px 16px 16px;
}

.history-item {
  padding: 10px 12px;
  margin-bottom: 8px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  border-left: 2px solid rgba(168, 85, 247, 0.3);
  transition: all 0.2s ease;
}

.history-item:hover {
  background: rgba(168, 85, 247, 0.1);
  border-left-color: #a855f7;
}

.history-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.history-type {
  font-size: 10px;
  color: #a855f7;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.history-time {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
}

.history-content {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.7);
}

.load-more {
  text-align: center;
  padding: 8px 0;
}

.empty-history {
  text-align: center;
  padding: 20px 0;
  color: rgba(255, 255, 255, 0.4);
  font-size: 12px;
}

/* 滚动条样式 */
.history-list::-webkit-scrollbar {
  width: 4px;
}

.history-list::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 2px;
}

.history-list::-webkit-scrollbar-thumb {
  background: rgba(168, 85, 247, 0.3);
  border-radius: 2px;
}

.history-list::-webkit-scrollbar-thumb:hover {
  background: rgba(168, 85, 247, 0.5);
}

/* 响应式 */
@media (max-width: 768px) {
  .panel-header {
    padding: 10px 12px;
  }
  
  .current-announcement {
    padding: 12px;
  }
  
  .history-list {
    max-height: 200px;
  }
}
</style>
