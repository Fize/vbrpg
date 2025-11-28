<template>
  <transition name="fade">
    <div 
      v-if="visible" 
      class="error-message" 
      :class="[type, { dismissible, inline }]"
      role="alert"
    >
      <!-- Icon -->
      <div class="error-icon">
        <el-icon :size="iconSize">
          <component :is="iconComponent" />
        </el-icon>
      </div>
      
      <!-- Content -->
      <div class="error-content">
        <p v-if="title" class="error-title">
          {{ title }}
        </p>
        <p class="error-text">
          {{ message }}
        </p>
        
        <!-- Slot for additional content -->
        <div v-if="$slots.default" class="error-extra">
          <slot />
        </div>
      </div>
      
      <!-- Close Button -->
      <button 
        v-if="dismissible" 
        class="error-close"
        @click="handleClose"
        aria-label="关闭"
      >
        <el-icon><Close /></el-icon>
      </button>
    </div>
  </transition>
</template>

<script setup>
import { ref, computed } from 'vue'
import { 
  Close, 
  CircleClose, 
  Warning, 
  InfoFilled, 
  SuccessFilled 
} from '@element-plus/icons-vue'

const props = defineProps({
  // Error message text
  message: {
    type: String,
    required: true
  },
  
  // Optional title
  title: {
    type: String,
    default: ''
  },
  
  // Message type
  type: {
    type: String,
    default: 'error',
    validator: (value) => ['error', 'warning', 'info', 'success'].includes(value)
  },
  
  // Can be dismissed
  dismissible: {
    type: Boolean,
    default: true
  },
  
  // Inline display (no margin, smaller padding)
  inline: {
    type: Boolean,
    default: false
  },
  
  // Auto dismiss after duration (ms)
  duration: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['close'])

const visible = ref(true)

const iconComponent = computed(() => {
  const icons = {
    error: CircleClose,
    warning: Warning,
    info: InfoFilled,
    success: SuccessFilled
  }
  return icons[props.type]
})

const iconSize = computed(() => {
  return props.inline ? 18 : 20
})

const handleClose = () => {
  visible.value = false
  emit('close')
}

// Auto dismiss
if (props.duration > 0) {
  setTimeout(() => {
    handleClose()
  }, props.duration)
}
</script>

<style scoped>
.error-message {
  display: flex;
  align-items: flex-start;
  gap: var(--space-md);
  padding: var(--space-md) var(--space-lg);
  margin: var(--space-md) 0;
  border-radius: var(--radius-md);
  border: 1px solid;
  background-color: var(--color-bg-primary);
  animation: slideInDown var(--transition-base);
}

.error-message.inline {
  margin: 0;
  padding: var(--space-sm) var(--space-md);
}

/* Type Variants */
.error-message.error {
  color: var(--color-danger);
  background-color: #fef0f0;
  border-color: #fde2e2;
}

.error-message.warning {
  color: var(--color-warning);
  background-color: #fdf6ec;
  border-color: #faecd8;
}

.error-message.info {
  color: var(--color-info);
  background-color: #ecf5ff;
  border-color: #d9ecff;
}

.error-message.success {
  color: var(--color-success);
  background-color: #f0f9ff;
  border-color: #e1f3d8;
}

[data-theme="dark"] .error-message.error {
  background-color: rgba(245, 108, 108, 0.1);
  border-color: rgba(245, 108, 108, 0.2);
}

[data-theme="dark"] .error-message.warning {
  background-color: rgba(230, 162, 60, 0.1);
  border-color: rgba(230, 162, 60, 0.2);
}

[data-theme="dark"] .error-message.info {
  background-color: rgba(64, 158, 255, 0.1);
  border-color: rgba(64, 158, 255, 0.2);
}

[data-theme="dark"] .error-message.success {
  background-color: rgba(103, 194, 58, 0.1);
  border-color: rgba(103, 194, 58, 0.2);
}

/* Icon */
.error-icon {
  flex-shrink: 0;
  line-height: 1;
}

/* Content */
.error-content {
  flex: 1;
  min-width: 0;
}

.error-title {
  margin: 0 0 var(--space-xs) 0;
  font-weight: 600;
  font-size: 0.9375rem;
}

.error-text {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.6;
  word-wrap: break-word;
}

.error-extra {
  margin-top: var(--space-sm);
}

/* Close Button */
.error-close {
  flex-shrink: 0;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  color: inherit;
  opacity: 0.6;
  transition: opacity var(--transition-fast);
  line-height: 1;
}

.error-close:hover {
  opacity: 1;
}

.error-close:focus {
  outline: 2px solid currentColor;
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

/* Dismissible Spacing */
.error-message.dismissible {
  padding-right: var(--space-md);
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-base), transform var(--transition-base);
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@keyframes slideInDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
