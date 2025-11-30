<template>
  <el-dialog
    v-model="dialogVisible"
    title="选择游戏模式"
    width="600px"
    :close-on-click-modal="false"
    :close-on-press-escape="!isStarting"
    :show-close="!isStarting"
    class="werewolf-mode-dialog"
    @closed="handleClosed"
  >
    <div class="dialog-content">
      <!-- 模式选择 -->
      <div class="mode-selection">
        <h4 class="section-title">游戏模式</h4>
        <div class="mode-options">
          <div
            class="mode-card"
            :class="{ active: selectedMode === 'player', disabled: isStarting }"
            @click="selectMode('player')"
          >
            <el-icon class="mode-icon"><User /></el-icon>
            <div class="mode-info">
              <span class="mode-name">玩家模式</span>
              <span class="mode-desc">作为玩家参与游戏，体验角色扮演</span>
            </div>
          </div>
          <div
            class="mode-card"
            :class="{ active: selectedMode === 'spectator', disabled: isStarting }"
            @click="selectMode('spectator')"
          >
            <el-icon class="mode-icon"><View /></el-icon>
            <div class="mode-info">
              <span class="mode-name">观战模式</span>
              <span class="mode-desc">观看 AI 对战，学习游戏策略</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 角色选择（仅玩家模式） -->
      <div v-if="selectedMode === 'player'" class="role-selection">
        <h4 class="section-title">选择角色</h4>
        <RoleSelector
          ref="roleSelectorRef"
          v-model="selectedRole"
          game-type="werewolf"
          @change="handleRoleChange"
        />
      </div>

      <!-- 游戏配置信息 -->
      <div class="game-info">
        <el-alert
          type="info"
          :closable="false"
          show-icon
        >
          <template #title>
            <span>10人局配置</span>
          </template>
          <template #default>
            <span>狼人×3、预言家×1、女巫×1、猎人×1、村民×4</span>
          </template>
        </el-alert>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleCancel" :disabled="isStarting">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="isStarting"
          :disabled="!canStart"
          @click="handleStart"
        >
          {{ isStarting ? '正在准备游戏...' : '开始游戏' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { User, View } from '@element-plus/icons-vue'
import RoleSelector from './RoleSelector.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'start', 'cancel'])

// 状态
const dialogVisible = ref(props.modelValue)
const selectedMode = ref('player')
const selectedRole = ref(null)
const isStarting = ref(false)
const roleSelectorRef = ref(null)

// 计算属性
const canStart = computed(() => {
  if (isStarting.value) return false
  if (!selectedMode.value) return false
  return true
})

// 选择模式
function selectMode(mode) {
  if (isStarting.value) return
  selectedMode.value = mode
  if (mode === 'spectator') {
    selectedRole.value = null
  }
}

// 处理角色变化
function handleRoleChange(role) {
  selectedRole.value = role
}

// 开始游戏
function handleStart() {
  if (!canStart.value) return
  
  isStarting.value = true
  emit('start', {
    mode: selectedMode.value,
    role: selectedRole.value?.name || null
  })
}

// 取消
function handleCancel() {
  if (isStarting.value) return
  dialogVisible.value = false
  emit('update:modelValue', false)
  emit('cancel')
}

// 对话框关闭后重置状态
function handleClosed() {
  if (!isStarting.value) {
    selectedMode.value = 'player'
    selectedRole.value = null
  }
}

// 重置启动状态（供父组件调用）
function resetStarting() {
  isStarting.value = false
}

// 监听 props 变化
watch(() => props.modelValue, (val) => {
  dialogVisible.value = val
  if (!val) {
    isStarting.value = false
  }
})

// 监听内部状态变化
watch(dialogVisible, (val) => {
  emit('update:modelValue', val)
})

// 暴露方法
defineExpose({
  resetStarting
})
</script>

<style scoped>
.werewolf-mode-dialog :deep(.el-dialog) {
  background: var(--color-bg-primary);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: var(--radius-lg);
}

.werewolf-mode-dialog :deep(.el-dialog__header) {
  border-bottom: 1px solid rgba(0, 240, 255, 0.1);
  padding: 20px 24px;
}

.werewolf-mode-dialog :deep(.el-dialog__title) {
  color: var(--color-text-primary);
  font-size: 1.25rem;
  font-weight: 600;
}

.werewolf-mode-dialog :deep(.el-dialog__body) {
  padding: 24px;
}

.dialog-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.section-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 16px;
}

/* 模式选择 */
.mode-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.mode-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: rgba(0, 0, 0, 0.3);
  border: 2px solid rgba(0, 240, 255, 0.1);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.3s ease;
}

.mode-card:hover:not(.disabled) {
  border-color: rgba(0, 240, 255, 0.3);
  background: rgba(0, 0, 0, 0.4);
}

.mode-card.active {
  border-color: var(--color-primary);
  background: rgba(0, 240, 255, 0.1);
}

.mode-card.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mode-icon {
  font-size: 32px;
  color: var(--color-primary);
  flex-shrink: 0;
}

.mode-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mode-name {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.mode-desc {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

/* 角色选择 */
.role-selection {
  max-height: 300px;
  overflow-y: auto;
}

/* 游戏信息 */
.game-info {
  margin-top: 8px;
}

.game-info :deep(.el-alert) {
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid rgba(0, 240, 255, 0.2);
}

.game-info :deep(.el-alert__title) {
  color: var(--color-primary);
  font-weight: 600;
}

.game-info :deep(.el-alert__description) {
  color: var(--color-text-secondary);
}

/* 底部按钮 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 响应式 */
@media (max-width: 768px) {
  .mode-options {
    grid-template-columns: 1fr;
  }
  
  .werewolf-mode-dialog :deep(.el-dialog) {
    width: 90% !important;
    max-width: 600px;
  }
}
</style>
