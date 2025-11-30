<template>
  <div class="night-action-panel">
    <div class="panel-header">
      <h3 class="panel-title">{{ actionTitle }}</h3>
      <p class="panel-desc">{{ actionDescription }}</p>
    </div>
    
    <!-- 狼人行动 -->
    <div v-if="roleType === 'werewolf' || role?.name === '狼人'" class="action-content">
      <p class="action-hint">选择一名玩家击杀，或选择空刀</p>
      <div class="target-list">
        <div 
          v-for="target in validTargets" 
          :key="target.id"
          class="target-item"
          :class="{ selected: selectedTarget?.id === target.id }"
          @click="selectTarget(target)"
        >
          <span class="target-seat">{{ target.seat_number || '?' }}</span>
          <span class="target-name">{{ target.name || target.username }}</span>
          <el-tag v-if="isTeammate(target)" size="small" type="danger">同伴</el-tag>
        </div>
      </div>
      <div class="action-buttons">
        <el-button @click="emptyKill" :disabled="disabled">
          空刀（不击杀）
        </el-button>
        <el-button 
          type="danger" 
          :disabled="!selectedTarget || disabled"
          @click="confirmAction"
        >
          确认击杀
        </el-button>
      </div>
    </div>
    
    <!-- 预言家查验 -->
    <div v-else-if="role?.name === '预言家'" class="action-content">
      <p class="action-hint">选择一名玩家查验身份</p>
      <div class="target-list">
        <div 
          v-for="target in validTargets" 
          :key="target.id"
          class="target-item"
          :class="{ selected: selectedTarget?.id === target.id }"
          @click="selectTarget(target)"
        >
          <span class="target-seat">{{ target.seat_number || '?' }}</span>
          <span class="target-name">{{ target.name || target.username }}</span>
        </div>
      </div>
      <el-button 
        type="primary" 
        :disabled="!selectedTarget || disabled"
        @click="confirmAction"
      >
        查验
      </el-button>
    </div>
    
    <!-- 女巫行动 -->
    <div v-else-if="role?.name === '女巫'" class="action-content">
      <div class="witch-actions">
        <!-- 解药 -->
        <div v-if="!antidoteUsed" class="witch-action">
          <div class="action-label">
            <el-icon><FirstAidKit /></el-icon>
            <span>解药</span>
          </div>
          <p class="action-hint" v-if="killedPlayer">
            今晚 <strong>{{ killedPlayer.name }}</strong> 被杀，是否使用解药？
            <span v-if="isSelfKilled" class="self-save-hint">（可以自救）</span>
          </p>
          <p class="action-hint" v-else>
            今晚无人被杀
          </p>
          <el-button 
            v-if="killedPlayer"
            type="success" 
            :disabled="disabled"
            @click="useAntidote"
          >
            使用解药{{ isSelfKilled ? '（自救）' : '' }}
          </el-button>
        </div>
        <div v-else class="witch-action used">
          <div class="action-label">
            <el-icon><FirstAidKit /></el-icon>
            <span>解药（已使用）</span>
          </div>
        </div>
        
        <!-- 毒药 -->
        <div v-if="!poisonUsed" class="witch-action">
          <div class="action-label">
            <el-icon><Warning /></el-icon>
            <span>毒药</span>
          </div>
          <p class="action-hint">选择一名玩家毒杀（可选）</p>
          <div class="target-list">
            <div 
              v-for="target in poisonTargets" 
              :key="target.id"
              class="target-item"
              :class="{ selected: selectedTarget?.id === target.id }"
              @click="selectTarget(target)"
            >
              <span class="target-seat">{{ target.seat_number || '?' }}</span>
              <span class="target-name">{{ target.name || target.username }}</span>
            </div>
          </div>
          <el-button 
            type="danger" 
            :disabled="!selectedTarget || disabled"
            @click="usePoison"
          >
            使用毒药
          </el-button>
        </div>
        <div v-else class="witch-action used">
          <div class="action-label">
            <el-icon><Warning /></el-icon>
            <span>毒药（已使用）</span>
          </div>
        </div>
        
        <el-button @click="skipAction" :disabled="disabled">
          跳过（不使用药水）
        </el-button>
      </div>
    </div>
    
    <!-- 猎人（死亡时触发） -->
    <div v-else-if="role?.name === '猎人'" class="action-content">
      <p class="action-hint">你已死亡，选择是否开枪带走一人</p>
      <div class="target-list">
        <div 
          v-for="target in validTargets" 
          :key="target.id"
          class="target-item"
          :class="{ selected: selectedTarget?.id === target.id }"
          @click="selectTarget(target)"
        >
          <span class="target-seat">{{ target.seat_number || '?' }}</span>
          <span class="target-name">{{ target.name || target.username }}</span>
        </div>
      </div>
      <div class="action-buttons">
        <el-button @click="skipAction" :disabled="disabled">
          不开枪
        </el-button>
        <el-button 
          type="danger" 
          :disabled="!selectedTarget || disabled"
          @click="confirmAction"
        >
          开枪
        </el-button>
      </div>
    </div>
    
    <!-- 村民（无技能） -->
    <div v-else class="action-content">
      <div class="no-action">
        <el-icon :size="48"><Moon /></el-icon>
        <p>夜晚来临，请闭眼休息...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Moon, FirstAidKit, Warning } from '@element-plus/icons-vue'

const props = defineProps({
  role: {
    type: Object,
    default: null
  },
  myPlayerId: {
    type: String,
    default: ''
  },
  teammates: {
    type: Array,
    default: () => []
  },
  targets: {
    type: Array,
    default: () => []
  },
  killedPlayer: {
    type: Object,
    default: null
  },
  antidoteUsed: {
    type: Boolean,
    default: false
  },
  poisonUsed: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['use-skill', 'use-antidote', 'use-poison', 'skip', 'empty-kill'])

const selectedTarget = ref(null)

// 角色类型
const roleType = computed(() => props.role?.team || props.role?.type)

// 行动标题
const actionTitle = computed(() => {
  if (!props.role) return '等待中'
  switch (props.role.name) {
    case '狼人': return '狼人行动'
    case '预言家': return '预言家查验'
    case '女巫': return '女巫行动'
    case '猎人': return '猎人技能'
    default: return '夜晚'
  }
})

// 行动描述
const actionDescription = computed(() => {
  if (!props.role) return ''
  switch (props.role.name) {
    case '狼人': return '与同伴商议，选择击杀目标或空刀'
    case '预言家': return '查验一名玩家的真实身份'
    case '女巫': return '你可以使用解药或毒药'
    case '猎人': return '死亡时可以开枪带走一人'
    default: return '请等待其他玩家行动'
  }
})

// 有效目标（排除已死亡的）
const validTargets = computed(() => {
  return props.targets.filter(t => t.is_alive)
})

// 毒药目标（排除自己）
const poisonTargets = computed(() => {
  return validTargets.value.filter(t => t.id !== props.myPlayerId)
})

// 检查是否是队友
function isTeammate(target) {
  return props.teammates.some(t => t.id === target.id)
}

// 是否是自己被杀（女巫自救判断）
const isSelfKilled = computed(() => {
  return props.killedPlayer && props.killedPlayer.id === props.myPlayerId
})

// 选择目标
function selectTarget(target) {
  if (props.disabled) return
  selectedTarget.value = selectedTarget.value?.id === target.id ? null : target
}

// 确认行动
function confirmAction() {
  if (selectedTarget.value) {
    emit('use-skill', selectedTarget.value)
    selectedTarget.value = null
  }
}

// 空刀（狼人不击杀任何人）
function emptyKill() {
  emit('empty-kill')
}

// 使用解药
function useAntidote() {
  emit('use-antidote', props.killedPlayer)
}

// 使用毒药
function usePoison() {
  if (selectedTarget.value) {
    emit('use-poison', selectedTarget.value)
    selectedTarget.value = null
  }
}

// 跳过行动
function skipAction() {
  emit('skip')
}
</script>

<style scoped>
.night-action-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-header {
  text-align: center;
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 4px;
}

.panel-desc {
  font-size: 12px;
  color: #909399;
  margin: 0;
}

.action-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.action-hint {
  font-size: 13px;
  color: #606266;
  margin: 0;
}

.target-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.target-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: #f5f7fa;
  border: 2px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.target-item:hover {
  background: #ecf5ff;
  border-color: #b3d8ff;
}

.target-item.selected {
  background: #ecf5ff;
  border-color: var(--el-color-primary);
}

.target-seat {
  width: 24px;
  height: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.target-name {
  flex: 1;
  font-size: 14px;
  color: #303133;
}

.witch-actions {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.witch-action {
  padding: 12px;
  background: #f9fafc;
  border-radius: 8px;
}

.action-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.witch-action.used {
  opacity: 0.5;
}

.witch-action.used .action-label {
  color: #909399;
}

.self-save-hint {
  color: #67c23a;
  font-weight: 500;
}

.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.no-action {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px;
  color: #909399;
}

/* 响应式 */
@media (max-width: 768px) {
  .target-list {
    max-height: 150px;
  }
}
</style>
