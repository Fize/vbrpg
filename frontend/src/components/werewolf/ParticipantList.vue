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
.participant-list {
  background: #fafafa;
  border-radius: 12px;
  padding: 16px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.list-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.participant-count {
  font-size: 14px;
  color: #909399;
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
  padding: 12px;
  background: white;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  transition: all 0.2s ease;
}

.participant-item:hover {
  border-color: #dcdfe6;
}

.participant-item.is-current {
  background: #ecf5ff;
  border-color: var(--el-color-primary-light-5);
}

.participant-item.is-host {
  border-color: var(--el-color-warning-light-3);
}

.participant-item.is-offline {
  opacity: 0.6;
}

.participant-item.empty-slot {
  background: #f5f7fa;
  border-style: dashed;
}

.participant-avatar {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.participant-item.is-ai .participant-avatar {
  background: linear-gradient(135deg, #606266 0%, #909399 100%);
}

.participant-item.is-spectator .participant-avatar {
  background: linear-gradient(135deg, #67c23a 0%, #95d475 100%);
}

.participant-item.empty-slot .participant-avatar {
  background: #dcdfe6;
}

.seat-number {
  font-size: 16px;
  font-weight: 600;
}

.participant-info {
  flex: 1;
  min-width: 0;
}

.participant-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}

.participant-name.empty {
  color: #c0c4cc;
  font-weight: 400;
}

.participant-status {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.role-name {
  color: var(--el-color-primary);
  font-weight: 500;
}

.ready-status {
  color: var(--el-color-success);
}

.waiting-status {
  color: #c0c4cc;
}

.online-indicator {
  width: 8px;
  height: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.online-indicator .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #c0c4cc;
}

.online-indicator.online .dot {
  background: var(--el-color-success);
}

.participant-actions {
  flex-shrink: 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .participant-list {
    padding: 12px;
  }
  
  .participant-item {
    padding: 10px;
  }
  
  .participant-avatar {
    width: 36px;
    height: 36px;
  }
}
</style>
