<template>
  <div class="role-selector">
    <div class="selector-header">
      <h3 class="selector-title">选择你的角色</h3>
      <p class="selector-desc">选择一个你想扮演的角色，系统将优先为你分配</p>
    </div>
    
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="3" animated />
    </div>
    
    <div v-else-if="error" class="error-container">
      <el-empty description="加载角色列表失败">
        <el-button type="primary" @click="loadRoles">重新加载</el-button>
      </el-empty>
    </div>
    
    <div v-else class="roles-container">
      <!-- 按角色类型分组显示 -->
      <div v-for="group in roleGroups" :key="group.type" class="role-group">
        <h4 class="group-title">{{ group.label }}</h4>
        <div class="role-list">
          <RoleCard
            v-for="role in group.roles"
            :key="role.id || role.name"
            :role="role"
            :selected="selectedRole?.name === role.name"
            :disabled="isRoleDisabled(role)"
            @select="handleRoleSelect"
          />
        </div>
      </div>
    </div>
    
    <div class="selector-footer" v-if="!loading && !error">
      <div class="selected-info" v-if="selectedRole">
        <el-icon><Check /></el-icon>
        <span>已选择: {{ selectedRole.name }}</span>
      </div>
      <div class="random-option">
        <el-checkbox v-model="randomAssign" @change="handleRandomChange">
          随机分配（不指定角色偏好）
        </el-checkbox>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Check } from '@element-plus/icons-vue'
import { rolesApi } from '@/services/api'
import RoleCard from './RoleCard.vue'

const props = defineProps({
  gameType: {
    type: String,
    default: 'werewolf'
  },
  modelValue: {
    type: Object,
    default: null
  },
  disabledRoles: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const loading = ref(false)
const error = ref(null)
const roles = ref([])
const selectedRole = ref(props.modelValue)
const randomAssign = ref(!props.modelValue)

// 角色类型分组配置
const roleTypeConfig = {
  werewolf: { label: '狼人阵营', order: 1 },
  villager: { label: '村民阵营', order: 2 },
  god: { label: '神职阵营', order: 3 }
}

// 按类型分组角色
const roleGroups = computed(() => {
  const groups = {}
  
  roles.value.forEach(role => {
    const type = role.team || role.type || 'villager'
    if (!groups[type]) {
      const config = roleTypeConfig[type] || { label: type, order: 99 }
      groups[type] = {
        type,
        label: config.label,
        order: config.order,
        roles: []
      }
    }
    groups[type].roles.push(role)
  })
  
  return Object.values(groups).sort((a, b) => a.order - b.order)
})

// 加载角色列表
async function loadRoles() {
  loading.value = true
  error.value = null
  
  try {
    const response = await rolesApi.getRoles(props.gameType)
    roles.value = response.data || response
  } catch (err) {
    console.error('加载角色失败:', err)
    error.value = err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

// 检查角色是否禁用
function isRoleDisabled(role) {
  return props.disabledRoles.includes(role.name) || props.disabledRoles.includes(role.id)
}

// 处理角色选择
function handleRoleSelect(role) {
  if (isRoleDisabled(role)) return
  
  selectedRole.value = role
  randomAssign.value = false
  emit('update:modelValue', role)
  emit('change', role)
}

// 处理随机分配选项
function handleRandomChange(value) {
  if (value) {
    selectedRole.value = null
    emit('update:modelValue', null)
    emit('change', null)
  }
}

// 监听外部值变化
watch(() => props.modelValue, (newVal) => {
  selectedRole.value = newVal
  randomAssign.value = !newVal
})

// 监听游戏类型变化
watch(() => props.gameType, () => {
  loadRoles()
})

onMounted(() => {
  loadRoles()
})

// 暴露方法供父组件调用
defineExpose({
  loadRoles,
  getSelectedRole: () => selectedRole.value
})
</script>

<style scoped>
.role-selector {
  padding: 16px;
}

.selector-header {
  text-align: center;
  margin-bottom: 24px;
}

.selector-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px;
}

.selector-desc {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

.loading-container,
.error-container {
  padding: 40px 0;
}

.roles-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.role-group {
  background: #fafafa;
  border-radius: 12px;
  padding: 16px;
}

.group-title {
  font-size: 14px;
  font-weight: 600;
  color: #606266;
  margin: 0 0 12px;
  padding-left: 8px;
  border-left: 3px solid var(--el-color-primary);
}

.role-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}

.selector-footer {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.selected-info {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--el-color-success);
  font-size: 14px;
}

.random-option {
  color: #909399;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .role-selector {
    padding: 12px;
  }
  
  .selector-title {
    font-size: 18px;
  }
  
  .role-list {
    grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
    gap: 8px;
  }
  
  .selector-footer {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
}
</style>
