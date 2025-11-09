<template>
  <el-card shadow="hover" class="player-list">
    <template #header>
      <div class="card-header">
        <span>参与者列表</span>
        <el-tag>{{ participants.length }} 人</el-tag>
      </div>
    </template>

    <el-scrollbar max-height="600px">
      <el-space direction="vertical" fill style="width: 100%">
        <div
          v-for="(participant, index) in participants"
          :key="participant.id"
          class="participant-item"
        >
          <div class="participant-info">
            <el-avatar
              :size="50"
              :style="{
                backgroundColor: getAvatarColor(index)
              }"
            >
              <span v-if="participant.is_ai">
                <el-icon><Avatar /></el-icon>
              </span>
              <span v-else>
                {{ getInitial(participant.name) }}
              </span>
            </el-avatar>

            <div class="participant-details">
              <div class="participant-name">
                {{ participant.name }}
                <el-tag
                  v-if="participant.is_ai"
                  type="info"
                  size="small"
                  effect="plain"
                >
                  AI
                </el-tag>
                <el-tag
                  v-if="participant.personality"
                  type="warning"
                  size="small"
                  effect="plain"
                >
                  {{ participant.personality }}
                </el-tag>
              </div>
              <div class="participant-status">
                <el-icon
                  :color="participant.is_active ? '#67C23A' : '#909399'"
                  size="12"
                >
                  <CircleCheck v-if="participant.is_active" />
                  <CircleClose v-else />
                </el-icon>
                <span class="status-text">
                  {{ participant.is_active ? '在线' : '已离开' }}
                </span>
              </div>
            </div>
          </div>

          <div class="participant-actions">
            <el-tag
              v-if="isCreator(participant)"
              type="success"
              effect="dark"
              size="small"
            >
              房主
            </el-tag>
          </div>
        </div>

        <el-empty
          v-if="participants.length === 0"
          description="暂无参与者"
          :image-size="80"
        />
      </el-space>
    </el-scrollbar>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { Avatar, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import { useGameStore } from '@/stores/game'

const props = defineProps({
  participants: {
    type: Array,
    default: () => []
  }
})

const gameStore = useGameStore()

// Methods
function getInitial(name) {
  if (!name) return '?'
  return name.charAt(0).toUpperCase()
}

function getAvatarColor(index) {
  const colors = [
    '#409EFF', // blue
    '#67C23A', // green
    '#E6A23C', // orange
    '#F56C6C', // red
    '#909399', // gray
    '#9c27b0', // purple
    '#00bcd4', // cyan
    '#ff9800'  // amber
  ]
  return colors[index % colors.length]
}

function isCreator(participant) {
  const room = gameStore.currentRoom
  return room && participant.id === room.created_by
}
</script>

<style scoped>
.player-list {
  height: 100%;
  min-height: 400px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: 16px;
}

.participant-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  transition: all 0.3s ease;
  gap: 12px;
}

.participant-item:hover {
  background: #ebeef5;
  transform: translateX(4px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.participant-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.participant-details {
  flex: 1;
  min-width: 0;
}

.participant-name {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.participant-status {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: #909399;
}

.status-text {
  line-height: 1;
}

.participant-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .player-list {
    min-height: 300px;
  }
  
  .card-header {
    font-size: 14px;
  }
  
  .participant-item {
    padding: 12px;
    gap: 10px;
  }
  
  .participant-info {
    gap: 10px;
  }
  
  .participant-name {
    font-size: 14px;
    margin-bottom: 4px;
  }
  
  .participant-status {
    font-size: 12px;
  }
  
  :deep(.el-avatar) {
    width: 40px !important;
    height: 40px !important;
  }
}

@media (max-width: 480px) {
  .participant-item {
    padding: 10px;
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .participant-info {
    width: 100%;
  }
  
  .participant-actions {
    width: 100%;
    justify-content: flex-end;
  }
  
  :deep(.el-avatar) {
    width: 36px !important;
    height: 36px !important;
  }
  
  .participant-name {
    font-size: 13px;
  }
}
</style>
