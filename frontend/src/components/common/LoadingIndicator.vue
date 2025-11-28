<template>
  <div class="loading-indicator" :class="[size, { fullscreen }]">
    <div class="loading-content">
      <!-- Spinner -->
      <div class="spinner" :class="variant">
        <div class="spinner-circle"></div>
      </div>
      
      <!-- Loading Text -->
      <p v-if="text" class="loading-text">
        {{ text }}
      </p>
      
      <!-- Tip Text -->
      <p v-if="tip" class="loading-tip">
        {{ tip }}
      </p>
    </div>
    
    <!-- Background Overlay (for fullscreen) -->
    <div v-if="fullscreen" class="loading-overlay" @click="handleOverlayClick"></div>
  </div>
</template>

<script setup>
const props = defineProps({
  // Loading text
  text: {
    type: String,
    default: '加载中...'
  },
  
  // Tip text (shown below loading text)
  tip: {
    type: String,
    default: ''
  },
  
  // Size variant
  size: {
    type: String,
    default: 'medium',
    validator: (value) => ['small', 'medium', 'large'].includes(value)
  },
  
  // Spinner variant
  variant: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'primary', 'dots', 'pulse'].includes(value)
  },
  
  // Fullscreen mode
  fullscreen: {
    type: Boolean,
    default: false
  },
  
  // Allow clicking overlay to close (when fullscreen)
  closeOnClickOverlay: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close'])

const handleOverlayClick = () => {
  if (props.closeOnClickOverlay) {
    emit('close')
  }
}
</script>

<style scoped>
.loading-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-lg);
}

.loading-indicator.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: var(--z-modal);
  background: rgba(255, 255, 255, 0.9);
  padding: 0;
}

[data-theme="dark"] .loading-indicator.fullscreen {
  background: rgba(26, 26, 26, 0.9);
}

.loading-content {
  position: relative;
  z-index: calc(var(--z-modal) + 1);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
}

/* ==================== Spinner Variants ==================== */

/* Default Spinner */
.spinner {
  width: 48px;
  height: 48px;
  position: relative;
}

.spinner.small {
  width: 32px;
  height: 32px;
}

.loading-indicator.large .spinner {
  width: 64px;
  height: 64px;
}

.spinner-circle {
  width: 100%;
  height: 100%;
  border: 3px solid var(--color-border-base);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinner.primary .spinner-circle {
  border-color: var(--color-primary-light-7);
  border-top-color: var(--color-primary);
}

/* Dots Spinner */
.spinner.dots {
  display: flex;
  gap: 8px;
  align-items: center;
}

.spinner.dots .spinner-circle {
  width: 12px;
  height: 12px;
  border: none;
  background: var(--color-primary);
  animation: dotPulse 1.4s ease-in-out infinite;
}

.spinner.dots .spinner-circle:nth-child(1) {
  animation-delay: 0s;
}

.spinner.dots .spinner-circle:nth-child(2) {
  animation-delay: 0.2s;
}

.spinner.dots .spinner-circle:nth-child(3) {
  animation-delay: 0.4s;
}

/* Pulse Spinner */
.spinner.pulse .spinner-circle {
  border: none;
  background: var(--color-primary);
  animation: pulse 1.5s ease-in-out infinite;
}

/* ==================== Text ==================== */
.loading-text {
  margin: 0;
  font-size: 1rem;
  font-weight: 500;
  color: var(--color-text-primary);
}

.loading-indicator.small .loading-text {
  font-size: 0.875rem;
}

.loading-indicator.large .loading-text {
  font-size: 1.125rem;
}

.loading-tip {
  margin: 0;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  max-width: 300px;
  text-align: center;
}

/* ==================== Overlay ==================== */
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: var(--z-modal);
}

/* ==================== Animations ==================== */
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes dotPulse {
  0%, 80%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.2);
    opacity: 0.5;
  }
}

/* ==================== Size Variants ==================== */
.loading-indicator.small {
  padding: var(--space-md);
}

.loading-indicator.large {
  padding: var(--space-xl);
}
</style>
