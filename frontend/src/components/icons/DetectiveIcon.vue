<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 100 100"
    :class="['animated-icon', 'detective-icon', className]"
    xmlns="http://www.w3.org/2000/svg"
  >
    <!-- Detective with magnifying glass -->
    <g class="detective">
      <!-- Head -->
      <circle cx="50" cy="35" r="12" :fill="color" class="head" />
      
      <!-- Hat -->
      <path
        d="M 38 35 Q 38 25 50 25 Q 62 25 62 35"
        :fill="color"
        class="hat"
      />
      <rect x="35" y="33" width="30" height="3" :fill="color" class="hat-brim" />
      
      <!-- Body -->
      <rect x="43" y="47" width="14" height="20" :fill="color" class="body" />
      
      <!-- Arms -->
      <line x1="43" y1="52" x2="35" y2="58" :stroke="color" stroke-width="3" class="arm-left" />
      <line x1="57" y1="52" x2="65" y2="58" :stroke="color" stroke-width="3" class="arm-right" />
      
      <!-- Legs -->
      <line x1="46" y1="67" x2="43" y2="80" :stroke="color" stroke-width="3" class="leg-left" />
      <line x1="54" y1="67" x2="57" y2="80" :stroke="color" stroke-width="3" class="leg-right" />
      
      <!-- Magnifying glass -->
      <g class="magnifying-glass" :transform="glassTransform">
        <circle cx="70" cy="60" r="10" fill="none" :stroke="color" stroke-width="2" class="glass-lens" />
        <line x1="65" y1="66" x2="58" y2="73" :stroke="color" stroke-width="2" class="glass-handle" />
      </g>
    </g>
  </svg>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  size: {
    type: [Number, String],
    default: 100
  },
  color: {
    type: String,
    default: '#667eea'
  },
  animate: {
    type: Boolean,
    default: true
  },
  className: {
    type: String,
    default: ''
  }
})

const glassPosition = ref(0)
let animationFrame = null

const glassTransform = computed(() => {
  if (!props.animate) return ''
  const rotation = Math.sin(glassPosition.value * 0.02) * 15
  const translateX = Math.sin(glassPosition.value * 0.01) * 3
  return `rotate(${rotation} 70 60) translate(${translateX} 0)`
})

const animate = () => {
  if (!props.animate) return
  glassPosition.value++
  animationFrame = requestAnimationFrame(animate)
}

onMounted(() => {
  if (props.animate) {
    animate()
  }
})

onBeforeUnmount(() => {
  if (animationFrame) {
    cancelAnimationFrame(animationFrame)
  }
})
</script>

<style scoped>
.animated-icon {
  display: inline-block;
}

.detective {
  animation: float 3s ease-in-out infinite;
  transform-origin: center;
}

.magnifying-glass {
  animation: swing 2s ease-in-out infinite;
  transform-origin: 58px 73px;
}

.glass-lens {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}

@keyframes swing {
  0%, 100% {
    transform: rotate(0deg);
  }
  25% {
    transform: rotate(-15deg);
  }
  75% {
    transform: rotate(15deg);
  }
}

/* Hover effects */
.animated-icon:hover .detective {
  animation-duration: 1.5s;
}

.animated-icon:hover .magnifying-glass {
  animation-duration: 1s;
}
</style>
