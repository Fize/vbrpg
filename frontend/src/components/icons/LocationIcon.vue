<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 100 100"
    :class="['animated-icon', 'location-icon', className]"
    xmlns="http://www.w3.org/2000/svg"
  >
    <!-- Pin -->
    <g class="pin">
      <!-- Pin body -->
      <path
        d="M 50 20 Q 35 20 35 35 Q 35 50 50 70 Q 65 50 65 35 Q 65 20 50 20 Z"
        :fill="color"
        class="pin-body"
      />
      
      <!-- Inner circle -->
      <circle
        cx="50"
        cy="35"
        r="8"
        fill="white"
        class="pin-center"
      />
      
      <!-- Dot in center -->
      <circle
        cx="50"
        cy="35"
        r="3"
        :fill="color"
        class="pin-dot"
      />
    </g>
    
    <!-- Pulse rings -->
    <g class="pulse-rings">
      <circle
        v-for="(ring, index) in rings"
        :key="index"
        cx="50"
        cy="70"
        :r="ring.r"
        fill="none"
        :stroke="color"
        :stroke-width="ring.strokeWidth"
        :opacity="ring.opacity"
        class="pulse-ring"
      />
    </g>
    
    <!-- Shadow -->
    <ellipse
      cx="50"
      cy="75"
      rx="12"
      ry="3"
      fill="rgba(0, 0, 0, 0.2)"
      class="shadow"
    />
  </svg>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  size: {
    type: [Number, String],
    default: 100
  },
  color: {
    type: String,
    default: '#e74c3c'
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

const rings = ref([
  { r: 15, opacity: 0, strokeWidth: 2 },
  { r: 20, opacity: 0, strokeWidth: 1.5 },
  { r: 25, opacity: 0, strokeWidth: 1 }
])

let animationFrame = null
let time = 0

const animate = () => {
  if (!props.animate) return
  
  time += 0.02
  
  // Animate pulse rings
  rings.value.forEach((ring, index) => {
    const phase = time - index * 0.3
    const progress = (Math.sin(phase) + 1) / 2
    
    ring.r = 15 + progress * 15
    ring.opacity = 0.6 * (1 - progress)
    ring.strokeWidth = 2 - progress
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
.location-icon {
  display: inline-block;
}

.pin {
  animation: bounce 2s ease-in-out infinite;
  transform-origin: 50% 70%;
}

.pin-body {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
}

.pin-center {
  animation: centerPulse 1.5s ease-in-out infinite;
}

.pin-dot {
  animation: dotPulse 1s ease-in-out infinite;
}

.shadow {
  animation: shadowScale 2s ease-in-out infinite;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}

@keyframes centerPulse {
  0%, 100% {
    r: 8;
    opacity: 1;
  }
  50% {
    r: 9;
    opacity: 0.8;
  }
}

@keyframes dotPulse {
  0%, 100% {
    r: 3;
  }
  50% {
    r: 4;
  }
}

@keyframes shadowScale {
  0%, 100% {
    transform: scale(1);
    opacity: 0.2;
  }
  50% {
    transform: scale(1.2);
    opacity: 0.1;
  }
}

.location-icon:hover .pin {
  animation-duration: 1s;
}
</style>
