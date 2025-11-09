<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 100 100"
    :class="['animated-icon', 'thinking-icon', className]"
    xmlns="http://www.w3.org/2000/svg"
  >
    <!-- AI Brain -->
    <g class="brain-container">
      <!-- Main brain shape -->
      <path
        d="M 50 20 
           Q 35 20 30 30
           Q 25 35 25 45
           Q 25 55 30 60
           Q 32 65 35 68
           Q 40 75 50 78
           Q 60 75 65 68
           Q 68 65 70 60
           Q 75 55 75 45
           Q 75 35 70 30
           Q 65 20 50 20 Z"
        :fill="color"
        class="brain"
        opacity="0.9"
      />
      
      <!-- Brain details (folds) -->
      <path
        d="M 40 35 Q 45 32 50 35 Q 55 32 60 35"
        fill="none"
        stroke="white"
        stroke-width="1.5"
        opacity="0.6"
        class="fold fold-1"
      />
      <path
        d="M 38 45 Q 43 42 48 45 Q 53 42 58 45"
        fill="none"
        stroke="white"
        stroke-width="1.5"
        opacity="0.6"
        class="fold fold-2"
      />
      <path
        d="M 40 55 Q 45 52 50 55 Q 55 52 60 55"
        fill="none"
        stroke="white"
        stroke-width="1.5"
        opacity="0.6"
        class="fold fold-3"
      />
      
      <!-- Thinking dots -->
      <circle
        v-for="(dot, index) in thinkingDots"
        :key="index"
        :cx="dot.x"
        :cy="dot.y"
        :r="dot.r"
        :fill="dotColor"
        :opacity="dot.opacity"
        class="thinking-dot"
      />
      
      <!-- Circuit lines -->
      <g class="circuits" opacity="0.4">
        <line x1="30" y1="40" x2="25" y2="45" stroke="white" stroke-width="1.5" />
        <line x1="70" y1="40" x2="75" y2="45" stroke="white" stroke-width="1.5" />
        <circle cx="24" cy="46" r="2" fill="white" class="circuit-node" />
        <circle cx="76" cy="46" r="2" fill="white" class="circuit-node" />
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
  dotColor: {
    type: String,
    default: '#ffffff'
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

const thinkingDots = ref([
  { x: 35, y: 28, r: 2, opacity: 0.3 },
  { x: 50, y: 25, r: 2.5, opacity: 0.6 },
  { x: 65, y: 28, r: 2, opacity: 0.3 }
])

let animationFrame = null
let dotPhase = 0

const animate = () => {
  if (!props.animate) return
  
  dotPhase += 0.05
  
  // Animate thinking dots (wave pattern)
  thinkingDots.value.forEach((dot, index) => {
    const phase = dotPhase + index * Math.PI / 1.5
    dot.opacity = 0.3 + Math.sin(phase) * 0.5
    dot.r = 2 + Math.sin(phase) * 0.8
    dot.y = 25 + Math.sin(phase) * 2
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
.thinking-icon {
  display: inline-block;
}

.brain-container {
  animation: pulse 2s ease-in-out infinite;
  transform-origin: center;
}

.brain {
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2));
}

.fold {
  animation: foldPulse 3s ease-in-out infinite;
}

.fold-1 {
  animation-delay: 0s;
}

.fold-2 {
  animation-delay: 0.5s;
}

.fold-3 {
  animation-delay: 1s;
}

.circuit-node {
  animation: blink 2s ease-in-out infinite;
}

.thinking-dot {
  filter: blur(0.5px);
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

@keyframes foldPulse {
  0%, 100% {
    opacity: 0.6;
    stroke-width: 1.5;
  }
  50% {
    opacity: 0.9;
    stroke-width: 2;
  }
}

@keyframes blink {
  0%, 49%, 100% {
    opacity: 1;
  }
  50%, 99% {
    opacity: 0.3;
  }
}

.thinking-icon:hover .brain-container {
  animation-duration: 1s;
}
</style>
