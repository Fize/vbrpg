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
      
      <!-- 选中角色的技能描述 -->
      <div v-if="selectedRole" class="role-description">
        <div class="description-header">
          <span class="description-icon">{{ getRoleEmoji(selectedRole) }}</span>
          <span class="description-title">{{ selectedRole.name }}</span>
          <span class="description-team" :class="getTeamClass(selectedRole)">
            {{ getTeamName(selectedRole) }}
          </span>
        </div>
        <div class="description-content">
          <p class="skill-label">技能说明：</p>
          <p class="skill-text">{{ getRoleSkillDescription(selectedRole) }}</p>
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
      
      <!-- 确认选择按钮 -->
      <div class="confirm-action">
        <el-button 
          type="primary" 
          size="large"
          :disabled="!canConfirm"
          :loading="confirming"
          @click="handleConfirmSelection"
        >
          {{ confirmButtonText }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { Check } from '@element-plus/icons-vue';
import { rolesApi } from '@/services/api';
import { useSocketStore } from '@/stores/socket';
import RoleCard from './RoleCard.vue';

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
  },
  roomCode: {
    type: String,
    default: ''
  },
  playerId: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['update:modelValue', 'change', 'confirmed']);

const socketStore = useSocketStore();

const loading = ref(false);
const error = ref(null);
const roles = ref([]);
const selectedRole = ref(props.modelValue);
const randomAssign = ref(!props.modelValue);
const confirming = ref(false);

// 角色类型分组配置
const roleTypeConfig = {
  werewolf: { label: '狼人阵营', order: 1 },
  villager: { label: '村民阵营', order: 2 },
  god: { label: '神职阵营', order: 3 }
};

// 中文名称到阵营的映射
const roleTeamMap = {
  '狼人': 'werewolf',
  '村民': 'villager',
  '预言家': 'god',
  '女巫': 'god',
  '猎人': 'god'
};

// 角色英文名映射
const roleNameToSlug = {
  '狼人': 'werewolf',
  '村民': 'villager',
  '预言家': 'seer',
  '女巫': 'witch',
  '猎人': 'hunter'
};

// 角色emoji映射
const roleEmojis = {
  werewolf: '🐺',
  villager: '👤',
  seer: '🔮',
  witch: '🧪',
  hunter: '🏹'
};

// 角色技能描述
const roleSkillDescriptions = {
  werewolf: '每晚可以与狼队友一起商议并选择击杀一名玩家。可以选择"空刀"（不杀人）或"自刀"（杀害自己）。白天需要伪装成好人，避免被投票出局。',
  villager: '没有特殊技能，需要通过观察和推理找出狼人。在白天讨论和投票阶段发挥作用，帮助好人阵营获胜。',
  seer: '每晚可以查验一名玩家的身份，得知其是否为狼人。是好人阵营最重要的信息来源，需要合理运用查验结果引导投票。',
  witch: '拥有一瓶解药和一瓶毒药。解药可以在夜间救活被狼人杀害的玩家，毒药可以毒杀任意一名玩家。每种药只能使用一次。',
  hunter: '当被投票出局或被狼人杀死时（非毒杀），可以开枪带走一名玩家。是好人阵营的保险手段。'
};

// 按类型分组角色
const roleGroups = computed(() => {
  const groups = {};
  
  // 确保 roles.value 是数组
  const roleList = Array.isArray(roles.value) ? roles.value : [];
  
  roleList.forEach(role => {
    // 根据角色名称或team字段确定阵营
    const type = role.team || roleTeamMap[role.name] || 'villager';
    if (!groups[type]) {
      const config = roleTypeConfig[type] || { label: type, order: 99 };
      groups[type] = {
        type,
        label: config.label,
        order: config.order,
        roles: []
      };
    }
    groups[type].roles.push(role);
  });
  
  return Object.values(groups).sort((a, b) => a.order - b.order);
});

// 是否可以确认选择
const canConfirm = computed(() => {
  return (selectedRole.value || randomAssign.value) && !confirming.value;
});

// 确认按钮文本
const confirmButtonText = computed(() => {
  if (confirming.value) return '确认中...';
  if (randomAssign.value) return '随机分配角色';
  if (selectedRole.value) return `确认选择 ${selectedRole.value.name}`;
  return '请选择角色';
});

// 获取角色emoji
function getRoleEmoji(role) {
  const slug = roleNameToSlug[role.name] || role.slug || '';
  return roleEmojis[slug] || '❓';
}

// 获取角色技能描述
function getRoleSkillDescription(role) {
  const slug = roleNameToSlug[role.name] || role.slug || '';
  return roleSkillDescriptions[slug] || role.description || '暂无技能描述';
}

// 获取阵营名称
function getTeamName(role) {
  const type = role.team || roleTeamMap[role.name] || 'villager';
  if (type === 'werewolf') return '狼人阵营';
  if (type === 'god') return '神职阵营';
  return '村民阵营';
}

// 获取阵营样式类
function getTeamClass(role) {
  const type = role.team || roleTeamMap[role.name] || 'villager';
  return `team-${type}`;
}

// 加载角色列表
async function loadRoles() {
  loading.value = true;
  error.value = null;
  
  try {
    const response = await rolesApi.getRoles(props.gameType);
    // 处理不同的响应格式
    if (Array.isArray(response)) {
      roles.value = response;
    } else if (response && Array.isArray(response.data)) {
      roles.value = response.data;
    } else if (response && typeof response === 'object') {
      // 如果是对象，尝试获取数组
      roles.value = response.roles || response.items || [];
    } else {
      roles.value = [];
    }
  } catch (err) {
    console.error('加载角色失败:', err);
    error.value = err.message || '加载失败';
    roles.value = [];
  } finally {
    loading.value = false;
  }
}

// 检查角色是否禁用
function isRoleDisabled(role) {
  return props.disabledRoles.includes(role.name) || props.disabledRoles.includes(role.id);
}

// 处理角色选择
function handleRoleSelect(role) {
  if (isRoleDisabled(role)) return;
  
  selectedRole.value = role;
  randomAssign.value = false;
  emit('update:modelValue', role);
  emit('change', role);
}

// 处理随机分配选项
function handleRandomChange(value) {
  if (value) {
    selectedRole.value = null;
    emit('update:modelValue', null);
    emit('change', null);
  }
}

// 确认角色选择并发送 WebSocket 事件
async function handleConfirmSelection() {
  if (!canConfirm.value) return;
  
  confirming.value = true;
  
  try {
    // 获取角色英文名（用于发送给后端）
    const roleSlug = selectedRole.value 
      ? (roleNameToSlug[selectedRole.value.name] || selectedRole.value.slug || selectedRole.value.name)
      : null;
    
    // 发送 WebSocket 事件
    socketStore.emit('werewolf_select_role', {
      room_code: props.roomCode,
      player_id: props.playerId,
      role: roleSlug // null 表示随机分配
    });
    
    // 通知父组件
    emit('confirmed', {
      role: selectedRole.value,
      roleSlug: roleSlug,
      isRandom: randomAssign.value
    });
    
  } catch (err) {
    console.error('确认角色选择失败:', err);
  } finally {
    confirming.value = false;
  }
}

// 监听外部值变化
watch(() => props.modelValue, (newVal) => {
  selectedRole.value = newVal;
  randomAssign.value = !newVal;
});

// 监听游戏类型变化
watch(() => props.gameType, () => {
  loadRoles();
});

onMounted(() => {
  loadRoles();
});

// 暴露方法供父组件调用
defineExpose({
  loadRoles,
  getSelectedRole: () => selectedRole.value,
  confirmSelection: handleConfirmSelection
});
</script>

<style scoped>
.role-selector {
  padding: 0;
}

.selector-header {
  text-align: center;
  margin-bottom: 24px;
  display: none; /* 隐藏，因为父组件已有标题 */
}

.loading-container,
.error-container {
  padding: 40px 0;
}

.roles-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.role-group {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(0, 240, 255, 0.1);
  border-radius: var(--radius-md);
  padding: 20px;
}

.group-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin: 0 0 16px;
  padding-left: 12px;
  border-left: 3px solid var(--color-primary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.role-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}

/* 角色技能描述 */
.role-description {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: var(--radius-md);
  padding: 20px;
  margin-top: 8px;
}

.description-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 240, 255, 0.1);
}

.description-icon {
  font-size: 1.5rem;
}

.description-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.description-team {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.description-team.team-werewolf {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.description-team.team-villager {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.description-team.team-god {
  background: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.description-content {
  color: var(--color-text-secondary);
}

.skill-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text-muted);
  margin: 0 0 8px;
}

.skill-text {
  font-size: 0.9rem;
  line-height: 1.6;
  margin: 0;
}

.selector-footer {
  margin-top: 24px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(0, 240, 255, 0.1);
  border-radius: var(--radius-md);
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.selected-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-success);
  font-size: 0.9rem;
}

.random-option {
  color: var(--color-text-secondary);
}

.random-option :deep(.el-checkbox__label) {
  color: var(--color-text-secondary);
}

.random-option :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: var(--color-primary);
  border-color: var(--color-primary);
}

.confirm-action {
  flex: 1;
  display: flex;
  justify-content: flex-end;
}

.confirm-action :deep(.el-button) {
  min-width: 160px;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .role-list {
    grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
    gap: 8px;
  }
  
  .selector-footer {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }
  
  .confirm-action {
    justify-content: center;
  }
  
  .confirm-action :deep(.el-button) {
    width: 100%;
  }
}
</style>
