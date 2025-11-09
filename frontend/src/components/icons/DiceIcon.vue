<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 100 100"
    :class="['animated-icon', 'dice-icon', className]"
    xmlns="http://www.w3.org/2000/svg"
  >
    <!-- Dice -->
    <g :transform="diceTransform">
      <!-- Dice body -->
      <rect
        x="25"
        y="25"
        width="50"
        height="50"
        rx="8"
        :fill="color"
        class="dice-body"
        :style="{ filter: 'drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2))' }"
      />
      
      <!-- Dots (showing different numbers based on roll) -->
      <g v-if="currentNumber === 1">
        <circle cx="50" cy="50" r="5" fill="white" class="dot" />
      </g>
      
      <g v-else-if="currentNumber === 2">
        <circle cx="37" cy="37" r="4" fill="white" class="dot" />
        <circle cx="63" cy="63" r="4" fill="white" class="dot" />
      </g>
      
      <g v-else-if="currentNumber === 3">
        <circle cx="35" cy="35" r="4" fill="white" class="dot" />
        <circle cx="50" cy="50" r="4" fill="white" class="dot" />
        <circle cx="65" cy="65" r="4" fill="white" class="dot" />
      </g>
      
      <g v-else-if="currentNumber === 4">
        <circle cx="35" cy="35" r="4" fill="white" class="dot" />
        <circle cx="65" cy="35" r="4" fill="white" class="dot" />
        <circle cx="35" cy="65" r="4" fill="white" class="dot" />
        <circle cx="65" cy="65" r="4" fill="white" class="dot" />
      </g>
      
      <g v-else-if="currentNumber === 5">
        <circle cx="35" cy="35" r="4" fill="white" class="dot" />
        <circle cx="65" cy="35" r="4" fill="white" class="dot" />
        <circle cx="50" cy="50" r="4" fill="white" class="dot" />
        <circle cx="35" cy="65" r="4" fill="white" class="dot" />
        <circle cx="65" cy="65" r="4" fill="white" class="dot" />
      </g>
      
      <g v-else>
        <circle cx="35" cy="33" r="3.5" fill="white" class="dot" />
        <circle cx="65" cy="33" r="3.5" fill="white" class="dot" />
        <circle cx="35" cy="50" r="3.5" fill="white" class="dot" />
        <circle cx="65" cy="50" r="3.5" fill="white" class="dot" />
        <circle cx="35" cy="67" r="3.5" fill="white" class="dot" />
        <circle cx="65" cy="67" r="3.5" fill="white" class="dot" />
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
  rollSpeed: {
    type: Number,
    default: 100 // ms between rolls
  },
  className: {
    type: String,
    default: ''
  }
})

const rotation = ref(0)
const currentNumber = ref(1)
let animationFrame = null
let rollInterval = null

const diceTransform = computed(() => {
  if (!props.animate) return ''
  return `rotate(${rotation.value} 50 50)`
})

const animate = () => {
  if (!props.animate) return
  rotation.value += 2
  animationFrame = requestAnimationFrame(animate)
}

const roll = () => {
  if (!props.animate) return
  currentNumber.value = Math.floor(Math.random() * 6) + 1
}

onMounted(() => {
  if (props.animate) {
    animate()
    rollInterval = setInterval(roll, props.rollSpeed)
  }
})

onBeforeUnmount(() => {
  if (animationFrame) {
    cancelAnimationFrame(animationFrame)
  }
  if (rollInterval) {
    clearInterval(rollInterval)
  }
})
</script>

<style scoped>
.dice-icon {
  display: inline-block;
}

.dice-body {
  transition: transform 0.3s ease;
}

.dot {
  animation: dotPulse 1s ease-in-out infinite;
}

@keyframes dotPulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.1);
  }
}

.dice-icon:hover .dice-body {
  filter: drop-shadow(0 6px 12px rgba(0, 0, 0, 0.3)) !important;
}
</style>
