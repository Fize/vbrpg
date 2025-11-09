<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 100 100"
    :class="['animated-icon', 'clue-icon', className]"
    xmlns="http://www.w3.org/2000/svg"
  >
    <!-- Magnifying glass -->
    <g class="magnifier">
      <!-- Handle -->
      <line
        x1="65"
        y1="65"
        x2="80"
        y2="80"
        :stroke="handleColor"
        stroke-width="5"
        stroke-linecap="round"
        class="handle"
      />
      
      <!-- Lens ring -->
      <circle
        cx="50"
        cy="50"
        r="22"
        fill="none"
        :stroke="color"
        stroke-width="4"
        class="lens-ring"
      />
      
      <!-- Lens glass -->
      <circle
        cx="50"
        cy="50"
        r="20"
        fill="rgba(255, 255, 255, 0.3)"
        class="lens-glass"
      />
      
      <!-- Shine effect -->
      <circle
        cx="44"
        cy="44"
        r="6"
        fill="white"
        opacity="0.6"
        class="shine"
      />
    </g>
    
    <!-- Sparkles -->
    <g class="sparkles">
      <g
        v-for="(sparkle, index) in sparkles"
        :key="index"
        :transform="`translate(${sparkle.x}, ${sparkle.y})`"
        :opacity="sparkle.opacity"
        class="sparkle"
      >
        <line x1="-3" y1="0" x2="3" y2="0" :stroke="sparkleColor" stroke-width="1.5" />
        <line x1="0" y1="-3" x2="0" y2="3" :stroke="sparkleColor" stroke-width="1.5" />
      </g>
    </g>
    
    <!-- Question mark inside lens -->
    <text
      x="50"
      y="58"
      font-family="Arial, sans-serif"
      font-size="24"
      font-weight="bold"
      :fill="color"
      text-anchor="middle"
      opacity="0.3"
      class="question-mark"
    >
      ?
    </text>
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
    default: '#3498db'
  },
  handleColor: {
    type: String,
    default: '#8b4513'
  },
  sparkleColor: {
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

const sparkles = ref([
  { x: 30, y: 30, opacity: 0 },
  { x: 70, y: 30, opacity: 0 },
  { x: 30, y: 70, opacity: 0 },
  { x: 70, y: 70, opacity: 0 }
])

let animationFrame = null
let time = 0

const animate = () => {
  if (!props.animate) return
  
  time += 0.03
  
  // Animate sparkles in sequence
  sparkles.value.forEach((sparkle, index) => {
    const phase = time + index * Math.PI / 2
    sparkle.opacity = Math.max(0, Math.sin(phase) * 0.9)
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
.clue-icon {
  display: inline-block;
}

.magnifier {
  animation: search 3s ease-in-out infinite;
  transform-origin: 50% 50%;
}

.lens-glass {
  animation: glassShine 2s ease-in-out infinite;
}

.shine {
  animation: shineMove 2s ease-in-out infinite;
}

.question-mark {
  animation: questionPulse 2s ease-in-out infinite;
}

.sparkle line {
  animation: sparkleRotate 1.5s linear infinite;
}

@keyframes search {
  0%, 100% {
    transform: translate(0, 0) rotate(0deg);
  }
  25% {
    transform: translate(-3px, -3px) rotate(-5deg);
  }
  75% {
    transform: translate(3px, 3px) rotate(5deg);
  }
}

@keyframes glassShine {
  0%, 100% {
    opacity: 0.3;
  }
  50% {
    opacity: 0.5;
  }
}

@keyframes shineMove {
  0%, 100% {
    transform: translate(0, 0);
  }
  50% {
    transform: translate(2px, 2px);
  }
}

@keyframes questionPulse {
  0%, 100% {
    opacity: 0.3;
  }
  50% {
    opacity: 0.6;
  }
}

@keyframes sparkleRotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.clue-icon:hover .magnifier {
  animation-duration: 1.5s;
}

.clue-icon:hover .sparkle line {
  animation-duration: 0.8s;
}
</style>
