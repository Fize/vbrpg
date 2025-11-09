<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 100 100"
    :class="['animated-icon', 'trophy-icon', className]"
    xmlns="http://www.w3.org/2000/svg"
  >
    <!-- Trophy -->
    <g class="trophy-container">
      <!-- Base -->
      <rect x="35" y="75" width="30" height="5" :fill="baseColor" rx="2" class="base" />
      <rect x="40" y="70" width="20" height="5" :fill="color" class="stem" />
      
      <!-- Cup body -->
      <path
        d="M 35 40 L 30 65 Q 30 70 35 70 L 65 70 Q 70 70 70 65 L 65 40 Z"
        :fill="color"
        class="cup-body"
      />
      
      <!-- Cup rim -->
      <ellipse cx="50" cy="40" rx="18" ry="4" :fill="color" class="cup-rim" />
      
      <!-- Handles -->
      <path
        d="M 30 45 Q 20 45 20 55 Q 20 60 25 60"
        fill="none"
        :stroke="color"
        stroke-width="3"
        class="handle-left"
      />
      <path
        d="M 70 45 Q 80 45 80 55 Q 80 60 75 60"
        fill="none"
        :stroke="color"
        stroke-width="3"
        class="handle-right"
      />
      
      <!-- Star decoration -->
      <g :transform="starTransform">
        <path
          d="M 50 48 L 52 54 L 58 54 L 53 58 L 55 64 L 50 60 L 45 64 L 47 58 L 42 54 L 48 54 Z"
          :fill="starColor"
          class="star"
        />
      </g>
      
      <!-- Shine effects -->
      <line x1="40" y1="50" x2="42" y2="62" stroke="white" stroke-width="2" opacity="0.4" class="shine shine-1" />
      <line x1="45" y1="45" x2="46" y2="55" stroke="white" stroke-width="1.5" opacity="0.3" class="shine shine-2" />
    </g>
    
    <!-- Sparkles -->
    <g class="sparkles">
      <circle
        v-for="(sparkle, index) in sparkles"
        :key="index"
        :cx="sparkle.x"
        :cy="sparkle.y"
        :r="sparkle.r"
        :fill="starColor"
        :opacity="sparkle.opacity"
        class="sparkle"
      />
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
    default: '#f39c12'
  },
  baseColor: {
    type: String,
    default: '#95a5a6'
  },
  starColor: {
    type: String,
    default: '#ffd700'
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

const starRotation = ref(0)
const sparkles = ref([
  { x: 25, y: 35, r: 1.5, opacity: 0 },
  { x: 75, y: 35, r: 1.5, opacity: 0 },
  { x: 30, y: 25, r: 1, opacity: 0 },
  { x: 70, y: 25, r: 1, opacity: 0 }
])

let animationFrame = null
let time = 0

const starTransform = computed(() => {
  if (!props.animate) return ''
  return `rotate(${starRotation.value} 50 56)`
})

const animate = () => {
  if (!props.animate) return
  
  time += 0.02
  starRotation.value = Math.sin(time) * 15
  
  // Animate sparkles
  sparkles.value.forEach((sparkle, index) => {
    const phase = time * 2 + index * Math.PI / 2
    sparkle.opacity = Math.max(0, Math.sin(phase) * 0.8)
    sparkle.r = 1 + Math.sin(phase) * 0.8
  })
  
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
.trophy-icon {
  display: inline-block;
}

.trophy-container {
  animation: bounce 2s ease-in-out infinite;
  transform-origin: 50% 80%;
}

.cup-body {
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3));
}

.star {
  animation: starPulse 1.5s ease-in-out infinite;
  transform-origin: center;
}

.shine {
  animation: shimmer 2s ease-in-out infinite;
}

.shine-1 {
  animation-delay: 0s;
}

.shine-2 {
  animation-delay: 0.5s;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

@keyframes starPulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.2);
    opacity: 0.8;
  }
}

@keyframes shimmer {
  0%, 100% {
    opacity: 0.4;
  }
  50% {
    opacity: 0.8;
  }
}

.trophy-icon:hover .trophy-container {
  animation-duration: 1s;
}

.trophy-icon:hover .star {
  animation-duration: 0.8s;
}
</style>
