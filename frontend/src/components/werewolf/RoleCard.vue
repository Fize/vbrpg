<template>
  <div
    class="role-card"
    :class="{
      'role-card--selected': selected,
      'role-card--disabled': disabled
    }"
    @click="handleClick"
  >
    <!-- 角色图标 -->
    <div class="role-card__icon" :style="{ backgroundColor: roleColor }">
      <el-icon v-if="!roleIcon" size="32"><User /></el-icon>
      <img v-else :src="roleIcon" :alt="role.name" class="role-card__icon-img" />
    </div>

    <!-- 角色信息 -->
    <div class="role-card__content">
      <h4 class="role-card__name">{{ role.name }}</h4>
      <p class="role-card__description">{{ role.description }}</p>
    </div>

    <!-- 选中标记 -->
    <div v-if="selected" class="role-card__check">
      <el-icon><Check /></el-icon>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { User, Check } from '@element-plus/icons-vue'

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

// 角色颜色映射
const roleColors = {
  villager: '#67c23a',
  werewolf: '#f56c6c',
  seer: '#409eff',
  witch: '#9b59b6',
  hunter: '#e67e22'
}

// 角色颜色
const roleColor = computed(() => {
  return roleColors[props.role.slug] || '#909399'
})

// 角色图标（如果有图片资源）
const roleIcon = computed(() => {
  // 暂时返回 null，使用默认图标
  return null
})

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
  align-items: center;
  padding: 16px;
  border: 2px solid #e4e7ed;
  border-radius: 12px;
  background-color: #fff;
  cursor: pointer;
  transition: all .2s;
  position: relative;
}

.role-card:hover:not(.role-card--disabled) {
  border-color: #409eff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, .2);
}

.role-card--selected {
  border-color: #409eff;
  background-color: #ecf5ff;
}

.role-card--disabled {
  opacity: .5;
  cursor: not-allowed;
}

.role-card__icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.role-card__icon-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

.role-card__content {
  flex: 1;
  margin-left: 16px;
  min-width: 0;
}

.role-card__name {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 4px 0;
  color: #303133;
}

.role-card__description {
  font-size: 14px;
  color: #606266;
  margin: 0;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.role-card__check {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background-color: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
