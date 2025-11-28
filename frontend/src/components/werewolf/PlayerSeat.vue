<template>
  <div 
    class="player-seat"
    :class="{
      'is-dead': !player.is_alive,
      'is-current': isCurrent,
      'is-selected': isSelected,
      'is-selectable': selectable,
      'is-speaking': isSpeaking,
      'is-ai': player.is_ai
    }"
    @click="handleClick"
  >
    <!-- 座位号 -->
    <div class="seat-number">{{ seatNumber }}</div>
    
    <!-- 玩家头像区域 -->
    <div class="avatar-area">
      <div class="avatar">
        <el-icon v-if="player.is_ai" :size="32"><Monitor /></el-icon>
        <el-icon v-else :size="32"><User /></el-icon>
      </div>
      
      <!-- 死亡标记 -->
      <div v-if="!player.is_alive" class="death-mark">
        <el-icon :size="24"><Close /></el-icon>
      </div>
      
      <!-- 在线状态 -->
      <div class="online-dot" :class="{ online: player.is_online !== false }"></div>
    </div>
    
    <!-- 玩家信息 -->
    <div class="player-info">
      <div class="player-name" :title="player.name || player.username">
        {{ displayName }}
      </div>
      
      <!-- 角色显示（如果已揭示） -->
      <div v-if="showRole && player.role_name" class="role-badge" :class="roleTypeClass">
        {{ player.role_name }}
      </div>
      
      <!-- 状态标签 -->
      <div v-if="statusText" class="status-text" :class="statusClass">
        {{ statusText }}
      </div>
    </div>
    
    <!-- 投票/目标指示 -->
    <div v-if="voteCount > 0" class="vote-indicator">
      <span class="vote-count">{{ voteCount }}</span>
      <span class="vote-label">票</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { User, Monitor, Close } from '@element-plus/icons-vue'

const props = defineProps({
  player: {
    type: Object,
    required: true
  },
  seatNumber: {
    type: Number,
    required: true
  },
  isCurrent: {
    type: Boolean,
    default: false
  },
  isSelected: {
    type: Boolean,
    default: false
  },
  selectable: {
    type: Boolean,
    default: false
  },
  isSpeaking: {
    type: Boolean,
    default: false
  },
  showRole: {
    type: Boolean,
    default: false
  },
  voteCount: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['select'])

// 显示名称（截断长名称）
const displayName = computed(() => {
  const name = props.player.name || props.player.username || `玩家${props.seatNumber}`
  return name.length > 6 ? name.slice(0, 6) + '...' : name
})

// 角色类型样式
const roleTypeClass = computed(() => {
  const roleType = props.player.role_type || props.player.team
  switch (roleType) {
    case 'werewolf': return 'role-werewolf'
    case 'villager': return 'role-villager'
    case 'god': return 'role-god'
    default: return ''
  }
})

// 状态文本
const statusText = computed(() => {
  if (!props.player.is_alive) return '已出局'
  if (props.isSpeaking) return '发言中'
  return ''
})

// 状态样式
const statusClass = computed(() => {
  if (!props.player.is_alive) return 'status-dead'
  if (props.isSpeaking) return 'status-speaking'
  return ''
})

// 点击处理
function handleClick() {
  if (props.selectable && props.player.is_alive) {
    emit('select', props.player)
  }
}
</script>

<style scoped>
.player-seat {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px;
  background: white;
  border-radius: 12px;
  border: 2px solid #ebeef5;
  min-width: 80px;
  transition: all 0.3s ease;
  position: relative;
}

.player-seat.is-selectable {
  cursor: pointer;
}

.player-seat.is-selectable:hover {
  border-color: var(--el-color-primary-light-3);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.player-seat.is-current {
  border-color: var(--el-color-primary);
  background: #ecf5ff;
}

.player-seat.is-selected {
  border-color: var(--el-color-warning);
  background: #fdf6ec;
}

.player-seat.is-dead {
  opacity: 0.6;
  background: #f5f7fa;
}

.player-seat.is-speaking {
  border-color: var(--el-color-success);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(103, 194, 58, 0.4); }
  50% { box-shadow: 0 0 0 8px rgba(103, 194, 58, 0); }
}

.seat-number {
  position: absolute;
  top: -8px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-size: 12px;
  font-weight: 600;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-area {
  position: relative;
  margin-bottom: 8px;
}

.avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.player-seat.is-ai .avatar {
  background: linear-gradient(135deg, #606266 0%, #909399 100%);
}

.player-seat.is-dead .avatar {
  background: #c0c4cc;
  filter: grayscale(1);
}

.death-mark {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(245, 108, 108, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.online-dot {
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #c0c4cc;
  border: 2px solid white;
}

.online-dot.online {
  background: var(--el-color-success);
}

.player-info {
  text-align: center;
  width: 100%;
}

.player-name {
  font-size: 12px;
  font-weight: 500;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 70px;
}

.role-badge {
  display: inline-block;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  margin-top: 4px;
  background: #909399;
  color: white;
}

.role-badge.role-werewolf {
  background: #f56c6c;
}

.role-badge.role-villager {
  background: #67c23a;
}

.role-badge.role-god {
  background: #409eff;
}

.status-text {
  font-size: 10px;
  margin-top: 4px;
  color: #909399;
}

.status-text.status-dead {
  color: #f56c6c;
}

.status-text.status-speaking {
  color: var(--el-color-success);
  font-weight: 500;
}

.vote-indicator {
  position: absolute;
  top: -8px;
  right: -8px;
  background: var(--el-color-danger);
  color: white;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 10px;
  display: flex;
  align-items: center;
  gap: 2px;
}

.vote-count {
  font-weight: 600;
}

/* 响应式 */
@media (max-width: 768px) {
  .player-seat {
    min-width: 60px;
    padding: 8px 4px;
  }
  
  .avatar {
    width: 36px;
    height: 36px;
  }
  
  .death-mark {
    width: 36px;
    height: 36px;
  }
  
  .player-name {
    font-size: 10px;
    max-width: 50px;
  }
}
</style>
