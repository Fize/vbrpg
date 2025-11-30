<template>
  <div class="host-announcement" :class="{ 'is-streaming': isStreaming, 'is-visible': visible }">
    <div class="announcement-container">
      <!-- 主持人头像/图标 -->
      <div class="host-avatar">
        <el-icon class="avatar-icon"><Microphone /></el-icon>
      </div>
      
      <!-- 发言内容区 -->
      <div class="announcement-content">
        <div class="announcement-header">
          <span class="host-name">主持人</span>
          <span v-if="announcementType" class="announcement-type">{{ getTypeLabel(announcementType) }}</span>
        </div>
        <div class="announcement-body">
          <p class="announcement-text">
            {{ content }}
            <span v-if="isStreaming" class="typing-cursor">|</span>
          </p>
        </div>
      </div>
    </div>
    
    <!-- 关闭按钮（非流式时显示） -->
    <el-button 
      v-if="!isStreaming && closable" 
      class="close-btn"
      type="text" 
      circle
      @click="handleClose"
    >
      <el-icon><Close /></el-icon>
    </el-button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Microphone, Close } from '@element-plus/icons-vue'

const props = defineProps({
  content: {
    type: String,
    default: ''
  },
  isStreaming: {
    type: Boolean,
    default: false
  },
  announcementType: {
    type: String,
    default: ''
  },
  visible: {
    type: Boolean,
    default: true
  },
  closable: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['close'])

// 获取公告类型标签
function getTypeLabel(type) {
  const typeMap = {
    game_start: '游戏开始',
    night_start: '夜幕降临',
    dawn: '天亮了',
    discussion_start: '讨论开始',
    vote_start: '投票开始',
    vote_result: '投票结果',
    hunter_shoot: '猎人开枪',
    game_end: '游戏结束',
    werewolf_action: '狼人行动',
    seer_action: '预言家行动',
    witch_action: '女巫行动'
  }
  return typeMap[type] || type
}

// 关闭处理
function handleClose() {
  emit('close')
}
</script>

<style scoped>
.host-announcement {
  position: relative;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  padding: 20px;
  margin: 16px 0;
  color: white;
  box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
  opacity: 0;
  transform: translateY(-20px);
  transition: all 0.4s ease;
}

.host-announcement.is-visible {
  opacity: 1;
  transform: translateY(0);
}

.host-announcement.is-streaming {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
  }
  50% {
    box-shadow: 0 8px 48px rgba(102, 126, 234, 0.5);
  }
}

.announcement-container {
  display: flex;
  gap: 16px;
}

.host-avatar {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-icon {
  font-size: 24px;
  color: white;
}

.announcement-content {
  flex: 1;
  min-width: 0;
}

.announcement-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.host-name {
  font-size: 16px;
  font-weight: 600;
}

.announcement-type {
  font-size: 12px;
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 10px;
}

.announcement-body {
  font-size: 15px;
  line-height: 1.6;
}

.announcement-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

/* 打字光标 */
.typing-cursor {
  display: inline-block;
  font-weight: bold;
  animation: blink 0.8s infinite;
  margin-left: 2px;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* 关闭按钮 */
.close-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  color: rgba(255, 255, 255, 0.7);
  transition: color 0.3s;
}

.close-btn:hover {
  color: white;
}

.close-btn :deep(.el-icon) {
  font-size: 18px;
}

/* 响应式 */
@media (max-width: 768px) {
  .host-announcement {
    padding: 16px;
    margin: 12px 0;
  }
  
  .host-avatar {
    width: 40px;
    height: 40px;
  }
  
  .avatar-icon {
    font-size: 20px;
  }
  
  .announcement-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .host-name {
    font-size: 14px;
  }
  
  .announcement-body {
    font-size: 14px;
  }
}
</style>
