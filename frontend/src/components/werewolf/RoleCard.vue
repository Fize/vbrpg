<template>
  <div
    class="role-card"
    :class="{
      'role-card--selected': selected,
      'role-card--disabled': disabled,
      [`role-card--${roleSlug}`]: true
    }"
    @click="handleClick"
  >
    <!-- 卡片光效 -->
    <div class="card-glow"></div>
    
    <!-- 角色图标 -->
    <div class="role-card__icon">
      <span class="icon-emoji">{{ roleEmoji }}</span>
      <div class="icon-ring"></div>
    </div>

    <!-- 角色信息 -->
    <div class="role-card__content">
      <h4 class="role-card__name">{{ role.name }}</h4>
      <p class="role-card__team">{{ roleTeam }}</p>
    </div>

    <!-- 选中标记 -->
    <div v-if="selected" class="role-card__check">
      <el-icon><Check /></el-icon>
    </div>
    
    <!-- 边框动画 -->
    <div class="card-border"></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Check } from '@element-plus/icons-vue'

const props = defineProps({
  role: {
    type: Object,
    required: true
  },
  selected: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['select'])

// 获取角色标识（兼容不同的数据格式）
const roleSlug = computed(() => {
  const slug = props.role.slug || props.role.name?.toLowerCase() || ''
  // 中文名称映射
  const nameMap = {
    '村民': 'villager',
    '狼人': 'werewolf',
    '预言家': 'seer',
    '女巫': 'witch',
    '猎人': 'hunter'
  }
  return nameMap[props.role.name] || slug
})

// 角色emoji映射
const roleEmojis = {
  villager: '👤',
  werewolf: '🐺',
  seer: '🔮',
  witch: '🧪',
  hunter: '🏹'
}

// 角色阵营
const roleTeams = {
  villager: '村民阵营',
  werewolf: '狼人阵营',
  seer: '神职阵营',
  witch: '神职阵营',
  hunter: '神职阵营'
}

const roleEmoji = computed(() => roleEmojis[roleSlug.value] || '❓')
const roleTeam = computed(() => roleTeams[roleSlug.value] || props.role.team || '未知阵营')

// 点击处理
const handleClick = () => {
  if (!props.disabled) {
    emit('select', props.role)
  }
}
</script>

<style scoped>
.role-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 16px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.card-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
  background: radial-gradient(ellipse, rgba(0, 240, 255, 0.1), transparent 70%);
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}

.card-border {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border: 1px solid rgba(0, 240, 255, 0.15);
  border-radius: var(--radius-md);
  pointer-events: none;
  transition: all 0.3s;
}

.role-card:hover:not(.role-card--disabled) {
  transform: translateY(-4px);
}

.role-card:hover:not(.role-card--disabled) .card-glow {
  opacity: 1;
}

.role-card:hover:not(.role-card--disabled) .card-border {
  border-color: rgba(0, 240, 255, 0.4);
}

/* Selected State */
.role-card--selected {
  transform: translateY(-4px);
}

.role-card--selected .card-border {
  border-color: var(--color-primary);
  box-shadow: var(--neon-box-primary);
}

.role-card--selected .card-glow {
  opacity: 1;
}

/* Disabled State */
.role-card--disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Role Colors */
.role-card--werewolf .icon-ring {
  border-color: #ef4444;
  box-shadow: 0 0 15px rgba(239, 68, 68, 0.5);
}

.role-card--villager .icon-ring {
  border-color: #22c55e;
  box-shadow: 0 0 15px rgba(34, 197, 94, 0.5);
}

.role-card--seer .icon-ring {
  border-color: #3b82f6;
  box-shadow: 0 0 15px rgba(59, 130, 246, 0.5);
}

.role-card--witch .icon-ring {
  border-color: #a855f7;
  box-shadow: 0 0 15px rgba(168, 85, 247, 0.5);
}

.role-card--hunter .icon-ring {
  border-color: #f97316;
  box-shadow: 0 0 15px rgba(249, 115, 22, 0.5);
}

/* Icon */
.role-card__icon {
  position: relative;
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.icon-emoji {
  font-size: 2rem;
  position: relative;
  z-index: 1;
}

.icon-ring {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border: 2px solid var(--color-border-base);
  border-radius: 50%;
  transition: all 0.3s;
}

/* Content */
.role-card__content {
  text-align: center;
}

.role-card__name {
  font-size: 1rem;
  font-weight: 600;
  margin: 0 0 4px 0;
  color: var(--color-text-primary);
}

.role-card__team {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Check Mark */
.role-card__check {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--color-primary);
  color: var(--color-bg-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
}
</style>
