<template>
  <div class="participant-list">
    <div class="list-header">
      <h3 class="list-title">{{ title }}</h3>
      <span class="participant-count">{{ participants.length }} / {{ maxCount }}</span>
    </div>
    
    <div class="participants">
      <div 
        v-for="(participant, index) in participants" 
        :key="participant.id || index"
        class="participant-item"
        :class="{ 
          'is-host': participant.is_host,
          'is-ai': participant.is_ai,
          'is-spectator': participant.is_spectator,
          'is-offline': !participant.is_online,
          'is-current': participant.id === currentPlayerId
        }"
      >
        <!-- 头像/序号 -->
        <div class="participant-avatar">
          <el-icon v-if="participant.is_ai" :size="24"><Monitor /></el-icon>
          <el-icon v-else-if="participant.is_spectator" :size="24"><View /></el-icon>
          <span v-else class="seat-number">{{ index + 1 }}</span>
        </div>
        
        <!-- 信息 -->
        <div class="participant-info">
          <div class="participant-name">
            {{ participant.name || participant.username || `玩家${index + 1}` }}
            <el-tag v-if="participant.is_host" size="small" type="warning">房主</el-tag>
            <el-tag v-if="participant.is_ai" size="small" type="info">AI</el-tag>
            <el-tag v-if="participant.is_spectator" size="small">观战</el-tag>
          </div>
          <div class="participant-status">
            <span v-if="showRole && participant.role_name" class="role-name">
              {{ participant.role_name }}
            </span>
            <span v-else-if="participant.is_ready" class="ready-status">已准备</span>
            <span v-else class="waiting-status">等待中</span>
          </div>
        </div>
        
        <!-- 在线状态 -->
        <div class="online-indicator" :class="{ online: participant.is_online !== false }">
          <span class="dot"></span>
        </div>
        
        <!-- 操作按钮 -->
        <div v-if="showActions && canRemove(participant)" class="participant-actions">
          <el-button 
            size="small" 
            type="danger" 
            text
            @click="$emit('remove', participant)"
          >
            移除
          </el-button>
        </div>
      </div>
      
      <!-- 空位 -->
      <div 
        v-for="i in emptySlots" 
        :key="'empty-' + i"
        class="participant-item empty-slot"
      >
        <div class="participant-avatar">
          <span class="seat-number">{{ participants.length + i }}</span>
        </div>
        <div class="participant-info">
          <div class="participant-name empty">等待加入...</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Monitor, View } from '@element-plus/icons-vue'

const props = defineProps({
  title: {
    type: String,
    default: '参与者列表'
  },
  participants: {
    type: Array,
    default: () => []
  },
  maxCount: {
    type: Number,
    default: 10
  },
  currentPlayerId: {
    type: String,
    default: null
  },
  isHost: {
    type: Boolean,
    default: false
  },
  showRole: {
    type: Boolean,
    default: false
  },
  showActions: {
    type: Boolean,
    default: false
  },
  showEmptySlots: {
    type: Boolean,
    default: true
  }
})

defineEmits(['remove'])

// 计算空位数量
const emptySlots = computed(() => {
  if (!props.showEmptySlots) return 0
  return Math.max(0, props.maxCount - props.participants.length)
})

// 判断是否可以移除
function canRemove(participant) {
  // 房主可以移除 AI，不能移除自己
  return props.isHost && participant.is_ai && participant.id !== props.currentPlayerId
}
</script>

<style scoped>
/* ===== 赛博朋克主题变量 ===== */
.participant-list {
  --cyber-bg: #0a0a12;
  --cyber-surface: rgba(18, 18, 31, 0.9);
  --cyber-cyan: #00f0ff;
  --cyber-purple: #a855f7;
  --cyber-pink: #ff00aa;
  --cyber-yellow: #ffd700;
  --cyber-red: #ff3366;
  --cyber-green: #00ff88;
  --cyber-text: #e0e0ff;
  --cyber-text-dim: rgba(224, 224, 255, 0.5);
  --cyber-border: rgba(0, 240, 255, 0.3);
  --cyber-glow: 0 0 10px rgba(0, 240, 255, 0.3);
}

.participant-list {
  background: var(--cyber-surface);
  border-radius: 8px;
  padding: 20px;
  border: 1px solid var(--cyber-border);
  box-shadow: var(--cyber-glow);
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--cyber-border);
}

.list-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--cyber-cyan);
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 2px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.list-title::before {
  content: '▸';
  color: var(--cyber-purple);
}

.participant-count {
  font-size: 13px;
  color: var(--cyber-text-dim);
  font-family: 'Orbitron', monospace;
}

.participants {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.participant-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 6px;
  border: 1px solid rgba(0, 240, 255, 0.1);
  transition: all 0.3s ease;
}

.participant-item:hover {
  border-color: var(--cyber-border);
  background: rgba(0, 240, 255, 0.05);
}

.participant-item.is-current {
  background: rgba(0, 240, 255, 0.1);
  border-color: var(--cyber-cyan);
  box-shadow: var(--cyber-glow);
}

.participant-item.is-host {
  border-color: var(--cyber-yellow);
  box-shadow: 0 0 10px rgba(255, 215, 0, 0.2);
}

.participant-item.is-offline {
  opacity: 0.4;
}

.participant-item.empty-slot {
  background: transparent;
  border-style: dashed;
  border-color: rgba(0, 240, 255, 0.15);
}

.participant-avatar {
  width: 44px;
  height: 44px;
  border-radius: 6px;
  background: linear-gradient(135deg, var(--cyber-cyan), var(--cyber-purple));
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--cyber-bg);
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
}

.participant-avatar::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(45deg, transparent 40%, rgba(255,255,255,0.3) 50%, transparent 60%);
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.participant-item.is-ai .participant-avatar {
  background: linear-gradient(135deg, var(--cyber-purple), var(--cyber-pink));
}

.participant-item.is-spectator .participant-avatar {
  background: linear-gradient(135deg, var(--cyber-green), var(--cyber-cyan));
}

.participant-item.empty-slot .participant-avatar {
  background: rgba(0, 240, 255, 0.1);
  border: 1px dashed var(--cyber-border);
}

.participant-item.empty-slot .participant-avatar::before {
  display: none;
}

.seat-number {
  font-size: 16px;
  font-weight: 700;
  font-family: 'Orbitron', monospace;
  position: relative;
  z-index: 1;
}

.participant-info {
  flex: 1;
  min-width: 0;
}

.participant-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--cyber-text);
  display: flex;
  align-items: center;
  gap: 8px;
}

.participant-name.empty {
  color: var(--cyber-text-dim);
  font-weight: 400;
  font-style: italic;
}

.participant-name :deep(.el-tag) {
  background: transparent;
  border: 1px solid currentColor;
  font-size: 10px;
  padding: 0 6px;
  height: 18px;
  line-height: 16px;
  font-family: 'Orbitron', monospace;
  text-transform: uppercase;
}

.participant-name :deep(.el-tag--warning) {
  color: var(--cyber-yellow);
  border-color: var(--cyber-yellow);
}

.participant-name :deep(.el-tag--info) {
  color: var(--cyber-purple);
  border-color: var(--cyber-purple);
}

.participant-status {
  font-size: 12px;
  color: var(--cyber-text-dim);
  margin-top: 4px;
}

.role-name {
  color: var(--cyber-cyan);
  font-weight: 500;
}

.ready-status {
  color: var(--cyber-green);
}

.waiting-status {
  color: var(--cyber-text-dim);
}

.online-indicator {
  width: 10px;
  height: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.online-indicator .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--cyber-text-dim);
  transition: all 0.3s;
}

.online-indicator.online .dot {
  background: var(--cyber-green);
  box-shadow: 0 0 10px var(--cyber-green);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(0.9); }
}

.participant-actions {
  flex-shrink: 0;
}

.participant-actions :deep(.el-button) {
  color: var(--cyber-red);
  font-size: 12px;
}

.participant-actions :deep(.el-button:hover) {
  color: #ff6699;
}

/* 响应式 */
@media (max-width: 768px) {
  .participant-list {
    padding: 14px;
  }
  
  .participant-item {
    padding: 10px;
  }
  
  .participant-avatar {
    width: 38px;
    height: 38px;
  }
}
</style>
