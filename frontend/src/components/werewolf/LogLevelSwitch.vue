<template>
  <!-- F26-F29: 日志级别切换组件 -->
  <div class="log-level-switch">
    <!-- 主控制器 -->
    <div class="switch-container">
      <el-tooltip
        :content="tooltipContent"
        placement="top"
        :show-after="500"
      >
        <div 
          class="switch-wrapper"
          :class="{ 'is-active': isDetailedMode }"
          @click="toggleLogLevel"
        >
          <!-- 图标 -->
          <el-icon class="switch-icon" :class="{ 'icon-rotated': isDetailedMode }">
            <component :is="currentIcon" />
          </el-icon>
          
          <!-- 标签文字 -->
          <span v-if="showLabel" class="switch-label">
            {{ currentLabel }}
          </span>
        </div>
      </el-tooltip>
    </div>
    
    <!-- 下拉选择器（可选，用于更多级别） -->
    <div v-if="showDropdown" class="dropdown-container">
      <el-dropdown
        trigger="click"
        @command="handleCommand"
      >
        <span class="dropdown-trigger">
          <el-icon><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item 
              v-for="level in logLevels" 
              :key="level.value"
              :command="level.value"
              :class="{ 'is-selected': currentLevel === level.value }"
            >
              <el-icon class="menu-icon"><component :is="level.icon" /></el-icon>
              <span>{{ level.label }}</span>
              <span class="level-desc">{{ level.description }}</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { View, Hide, ArrowDown, Document, Reading } from '@element-plus/icons-vue'
import { useGameStore } from '@/stores/game'

// Props 定义
const props = defineProps({
  /**
   * 是否显示标签文字
   */
  showLabel: {
    type: Boolean,
    default: true
  },
  /**
   * 是否显示下拉选择器
   */
  showDropdown: {
    type: Boolean,
    default: false
  },
  /**
   * 模型绑定值（可选，不传时使用 store）
   */
  modelValue: {
    type: String,
    default: null
  }
})

// 事件定义
const emit = defineEmits(['update:modelValue', 'change'])

// Store
const gameStore = useGameStore()

// 日志级别配置
const logLevels = ref([
  {
    value: 'basic',
    label: '简洁',
    description: '仅显示关键信息',
    icon: Document
  },
  {
    value: 'detailed',
    label: '详细',
    description: '显示完整游戏日志',
    icon: Reading
  }
])

// 计算属性：当前级别
const currentLevel = computed(() => {
  return props.modelValue !== null ? props.modelValue : gameStore.logLevel
})

// 计算属性：是否为详细模式
const isDetailedMode = computed(() => {
  return currentLevel.value === 'detailed'
})

// 计算属性：当前图标
const currentIcon = computed(() => {
  return isDetailedMode.value ? View : Hide
})

// 计算属性：当前标签
const currentLabel = computed(() => {
  return isDetailedMode.value ? '详细日志' : '简洁日志'
})

// 计算属性：提示内容
const tooltipContent = computed(() => {
  return isDetailedMode.value 
    ? '点击切换到简洁模式' 
    : '点击切换到详细模式'
})

// 方法：切换日志级别
const toggleLogLevel = () => {
  console.log('[LogLevelSwitch] toggleLogLevel called, current isDetailedMode:', isDetailedMode.value)
  const newLevel = isDetailedMode.value ? 'basic' : 'detailed'
  console.log('[LogLevelSwitch] switching to:', newLevel)
  updateLevel(newLevel)
}

// 方法：处理下拉选择
const handleCommand = (level) => {
  updateLevel(level)
}

// 方法：更新级别
const updateLevel = (level) => {
  if (props.modelValue !== null) {
    // 使用 v-model 模式
    emit('update:modelValue', level)
  } else {
    // 使用 store 模式
    gameStore.setLogLevel(level)
  }
  emit('change', level)
}
</script>

<style scoped>
.log-level-switch {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 切换器容器 */
.switch-container {
  display: flex;
  align-items: center;
}

.switch-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  user-select: none;
}

.switch-wrapper:hover {
  background: rgba(0, 240, 255, 0.1);
  border-color: rgba(0, 240, 255, 0.3);
}

.switch-wrapper.is-active {
  background: rgba(0, 240, 255, 0.15);
  border-color: rgba(0, 240, 255, 0.4);
}

/* 图标 */
.switch-icon {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.7);
  transition: all 0.3s ease;
}

.switch-wrapper.is-active .switch-icon {
  color: #00f0ff;
}

.switch-icon.icon-rotated {
  transform: rotate(180deg);
}

/* 标签 */
.switch-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  white-space: nowrap;
  transition: color 0.3s ease;
}

.switch-wrapper.is-active .switch-label {
  color: rgba(255, 255, 255, 0.95);
}

/* 下拉容器 */
.dropdown-container {
  margin-left: 2px;
}

.dropdown-trigger {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.dropdown-trigger:hover {
  background: rgba(0, 240, 255, 0.1);
}

.dropdown-trigger .el-icon {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

/* 下拉菜单 */
:deep(.el-dropdown-menu) {
  background: rgba(30, 30, 45, 0.98);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
  transition: all 0.2s ease;
}

:deep(.el-dropdown-menu__item:hover) {
  background: rgba(0, 240, 255, 0.1);
  color: rgba(255, 255, 255, 0.95);
}

:deep(.el-dropdown-menu__item.is-selected) {
  background: rgba(0, 240, 255, 0.15);
  color: #00f0ff;
}

.menu-icon {
  font-size: 14px;
  color: inherit;
}

.level-desc {
  margin-left: auto;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}

/* 响应式 */
@media (max-width: 768px) {
  .switch-wrapper {
    padding: 5px 10px;
  }
  
  .switch-label {
    font-size: 11px;
  }
  
  .switch-icon {
    font-size: 14px;
  }
}
</style>
