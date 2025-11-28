<template>
  <div class="empty-state" :class="size">
    <!-- Icon/Illustration -->
    <div class="empty-icon">
      <component 
        v-if="icon" 
        :is="icon" 
        class="icon"
      />
      <el-icon v-else :size="iconSize" class="icon">
        <Box />
      </el-icon>
    </div>
    
    <!-- Title -->
    <h3 v-if="title" class="empty-title">
      {{ title }}
    </h3>
    
    <!-- Description -->
    <p v-if="description" class="empty-description">
      {{ description }}
    </p>
    
    <!-- Slot for custom content -->
    <div v-if="$slots.default" class="empty-content">
      <slot />
    </div>
    
    <!-- Action Button -->
    <div v-if="actionText || $slots.action" class="empty-action">
      <slot name="action">
        <el-button 
          v-if="actionText"
          type="primary" 
          @click="$emit('action')"
        >
          {{ actionText }}
        </el-button>
      </slot>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Box } from '@element-plus/icons-vue'

const props = defineProps({
  // Icon component to display
  icon: {
    type: [Object, String],
    default: null
  },
  
  // Title text
  title: {
    type: String,
    default: '暂无数据'
  },
  
  // Description text
  description: {
    type: String,
    default: ''
  },
  
  // Action button text
  actionText: {
    type: String,
    default: ''
  },
  
  // Size variant
  size: {
    type: String,
    default: 'medium',
    validator: (value) => ['small', 'medium', 'large'].includes(value)
  }
})

defineEmits(['action'])

const iconSize = computed(() => {
  const sizes = {
    small: 48,
    medium: 64,
    large: 80
  }
  return sizes[props.size]
})
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--space-2xl) var(--space-xl);
  animation: fadeIn var(--transition-base);
}

/* Size Variants */
.empty-state.small {
  padding: var(--space-xl) var(--space-lg);
}

.empty-state.small .empty-title {
  font-size: 1rem;
}

.empty-state.small .empty-description {
  font-size: 0.875rem;
}

.empty-state.large {
  padding: var(--space-3xl) var(--space-2xl);
}

.empty-state.large .empty-title {
  font-size: 1.75rem;
}

.empty-state.large .empty-description {
  font-size: 1.125rem;
}

/* Icon */
.empty-icon {
  margin-bottom: var(--space-lg);
  color: var(--color-text-placeholder);
  animation: slideInDown var(--transition-slow);
}

.empty-icon .icon {
  opacity: 0.5;
}

/* Title */
.empty-title {
  margin: 0 0 var(--space-sm) 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-text-primary);
  animation: slideInUp var(--transition-slow) 0.1s backwards;
}

/* Description */
.empty-description {
  margin: 0 0 var(--space-lg) 0;
  max-width: 400px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  font-size: 0.9375rem;
  animation: slideInUp var(--transition-slow) 0.2s backwards;
}

/* Content Slot */
.empty-content {
  margin: var(--space-md) 0;
  animation: slideInUp var(--transition-slow) 0.3s backwards;
}

/* Action */
.empty-action {
  margin-top: var(--space-md);
  animation: slideInUp var(--transition-slow) 0.4s backwards;
}

/* Responsive */
@media (max-width: 640px) {
  .empty-state {
    padding: var(--space-xl) var(--space-md);
  }
  
  .empty-title {
    font-size: 1.125rem;
  }
  
  .empty-description {
    font-size: 0.875rem;
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideInDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
