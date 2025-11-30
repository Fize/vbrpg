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
  background: rgba(10, 10, 20, .95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(168, 85, 247, .4);
  border-radius: 16px;
  padding: 22px;
  margin: 16px 0;
  color: var(--color-text-primary);
  box-shadow: 
    0 8px 40px rgba(168, 85, 247, .25),
    0 0 60px rgba(168, 85, 247, .1);
  opacity: 0;
  transform: translateY(-20px);
  transition: all .4s ease;
  overflow: hidden;
}

/* 顶部发光线 */
.host-announcement:before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--color-primary), #a855f7, var(--color-accent));
  animation: lineGlow 3s ease-in-out infinite;
}

@keyframes lineGlow {
  0%, 100% { opacity: 1; }
  50% { opacity: .6; }
}

/* 背景网格 */
.host-announcement:after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: 
    linear-gradient(rgba(168, 85, 247, .03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(168, 85, 247, .03) 1px, transparent 1px);
  background-size: 30px 30px;
  pointer-events: none;
}

.host-announcement.is-visible {
  opacity: 1;
  transform: translateY(0);
}

.host-announcement.is-streaming {
  animation: streamPulse 2s infinite;
}

@keyframes streamPulse {
  0%, 100% {
    box-shadow: 
      0 8px 40px rgba(168, 85, 247, .25),
      0 0 60px rgba(168, 85, 247, .1);
  }
  50% {
    box-shadow: 
      0 8px 60px rgba(168, 85, 247, .4),
      0 0 80px rgba(168, 85, 247, .2);
  }
}

.announcement-container {
  display: flex;
  gap: 18px;
  position: relative;
  z-index: 1;
}

.host-avatar {
  flex-shrink: 0;
  width: 52px;
  height: 52px;
  background: linear-gradient(135deg, rgba(168, 85, 247, .2), rgba(0, 240, 255, .2));
  border: 2px solid rgba(168, 85, 247, .5);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.host-avatar:before {
  content: '';
  position: absolute;
  inset: -4px;
  border: 1px solid rgba(168, 85, 247, .3);
  border-radius: 50%;
  animation: ringPulse 2s ease-in-out infinite;
}

@keyframes ringPulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.1); opacity: .5; }
}

.avatar-icon {
  font-size: 26px;
  color: #a855f7;
  text-shadow: 0 0 15px #a855f7;
}

.announcement-content {
  flex: 1;
  min-width: 0;
}

.announcement-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 10px;
}

.host-name {
  font-size: 14px;
  font-weight: 700;
  color: #a855f7;
  text-transform: uppercase;
  letter-spacing: 2px;
  text-shadow: 0 0 10px rgba(168, 85, 247, .5);
}

.announcement-type {
  font-size: 10px;
  padding: 3px 10px;
  background: rgba(168, 85, 247, .15);
  border: 1px solid rgba(168, 85, 247, .3);
  border-radius: 12px;
  color: #a855f7;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.announcement-body {
  font-size: 14px;
  line-height: 1.7;
}

.announcement-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--color-text-primary);
}

/* 打字光标 */
.typing-cursor {
  display: inline-block;
  font-weight: bold;
  color: var(--color-primary);
  text-shadow: 0 0 10px var(--color-primary);
  animation: cursorBlink .8s infinite;
  margin-left: 2px;
}

@keyframes cursorBlink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* 关闭按钮 */
.close-btn {
  position: absolute;
  top: 14px;
  right: 14px;
  color: var(--color-text-secondary);
  z-index: 2;
  transition: all .3s;
}

.close-btn:hover {
  color: var(--color-primary);
  text-shadow: 0 0 10px var(--color-primary);
}

.close-btn :deep(.el-icon) {
  font-size: 18px;
}

/* 响应式 */
@media (max-width: 768px) {
  .host-announcement {
    padding: 18px;
    margin: 12px 0;
  }
  
  .host-avatar {
    width: 44px;
    height: 44px;
  }
  
  .avatar-icon {
    font-size: 22px;
  }
  
  .announcement-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }
  
  .host-name {
    font-size: 12px;
  }
  
  .announcement-body {
    font-size: 13px;
  }
}
</style>
