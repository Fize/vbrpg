<template>
  <div class="cyber-seat-circle" ref="circleRef">
    <!-- 科幻圆桌背景 -->
    <div class="table-background">
      <div class="table-ring ring-outer"></div>
      <div class="table-ring ring-middle"></div>
      <div class="table-ring ring-inner"></div>
      <div class="table-grid"></div>
      <div class="energy-pulse"></div>
    </div>
    
    <div class="circle-container" :style="containerStyle">
      <!-- 中心全息投影区域 -->
      <div class="hologram-center">
        <div class="hologram-ring"></div>
        <slot name="center">
          <div class="center-hologram">
            <div class="holo-scanline"></div>
            <span class="alive-count">{{ aliveCount }}</span>
            <span class="alive-label">ACTIVE</span>
            <div class="holo-corners">
              <span class="corner top-left"></span>
              <span class="corner top-right"></span>
              <span class="corner bottom-left"></span>
              <span class="corner bottom-right"></span>
            </div>
          </div>
        </slot>
      </div>
      
      <!-- 连接线 -->
      <svg class="connection-lines" :viewBox="`0 0 ${containerSize} ${containerSize}`">
        <defs>
          <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="rgba(0, 240, 255, 0)" />
            <stop offset="50%" stop-color="rgba(0, 240, 255, 0.6)" />
            <stop offset="100%" stop-color="rgba(0, 240, 255, 0)" />
          </linearGradient>
        </defs>
        <line 
          v-for="(player, index) in players"
          :key="'line-' + index"
          :x1="containerSize / 2"
          :y1="containerSize / 2"
          :x2="getLineEndX(index)"
          :y2="getLineEndY(index)"
          stroke="url(#lineGradient)"
          stroke-width="1"
          :class="{ 'line-active': player.is_alive, 'line-dead': !player.is_alive }"
        />
      </svg>
      
      <!-- 座位 -->
      <div 
        v-for="(player, index) in players"
        :key="player.id || index"
        class="seat-wrapper"
        :style="getSeatStyle(index)"
      >
        <PlayerSeat
          :player="player"
          :seat-number="index + 1"
          :is-current="player.id === currentPlayerId"
          :is-selected="selectedPlayerId === player.id"
          :selectable="selectable && player.is_alive"
          :is-speaking="speakingPlayerId === player.id"
          :show-role="showRoles"
          :vote-count="getVoteCount(player.id)"
          @select="handleSelect"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import PlayerSeat from './PlayerSeat.vue'

const props = defineProps({
  players: {
    type: Array,
    required: true,
    default: () => []
  },
  currentPlayerId: {
    type: String,
    default: null
  },
  selectedPlayerId: {
    type: String,
    default: null
  },
  speakingPlayerId: {
    type: String,
    default: null
  },
  selectable: {
    type: Boolean,
    default: false
  },
  showRoles: {
    type: Boolean,
    default: false
  },
  votes: {
    type: Object,
    default: () => ({})
  },
  // 圆的半径（相对于容器尺寸的比例）
  radiusRatio: {
    type: Number,
    default: 0.38
  }
})

const emit = defineEmits(['select'])

const circleRef = ref(null)
const containerSize = ref(500)

// 存活玩家数量
const aliveCount = computed(() => {
  return props.players.filter(p => p.is_alive).length
})

// 容器样式
const containerStyle = computed(() => ({
  width: `${containerSize.value}px`,
  height: `${containerSize.value}px`
}))

// 计算每个座位的位置
function getSeatStyle(index) {
  const totalPlayers = props.players.length || 10
  const angle = (index * 360 / totalPlayers) - 90 // 从12点方向开始
  const radian = (angle * Math.PI) / 180
  const radius = containerSize.value * props.radiusRatio
  
  const x = Math.cos(radian) * radius
  const y = Math.sin(radian) * radius
  
  return {
    transform: `translate(${x}px, ${y}px)`
  }
}

// 获取投票数
function getVoteCount(playerId) {
  return props.votes[playerId] || 0
}

// 获取连接线终点坐标
function getLineEndX(index) {
  const totalPlayers = props.players.length || 10
  const angle = (index * 360 / totalPlayers) - 90
  const radian = (angle * Math.PI) / 180
  const radius = containerSize.value * props.radiusRatio * 0.75
  return containerSize.value / 2 + Math.cos(radian) * radius
}

function getLineEndY(index) {
  const totalPlayers = props.players.length || 10
  const angle = (index * 360 / totalPlayers) - 90
  const radian = (angle * Math.PI) / 180
  const radius = containerSize.value * props.radiusRatio * 0.75
  return containerSize.value / 2 + Math.sin(radian) * radius
}

// 选择处理
function handleSelect(player) {
  emit('select', player)
}

// 响应式调整大小
function updateSize() {
  if (circleRef.value) {
    const rect = circleRef.value.getBoundingClientRect()
    const minSize = Math.min(rect.width, rect.height)
    containerSize.value = Math.max(300, Math.min(600, minSize))
  }
}

onMounted(() => {
  updateSize()
  window.addEventListener('resize', updateSize)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateSize)
})
</script>

<style scoped>
.cyber-seat-circle {
  width: 100%;
  height: 100%;
  min-height: 450px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  position: relative;
}

/* 科幻圆桌背景 */
.table-background {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 90%;
  height: 90%;
  pointer-events: none;
}

.table-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  border: 1px solid;
}

.ring-outer {
  width: 100%;
  height: 100%;
  border-color: rgba(0, 240, 255, .15);
  animation: ring-rotate 60s linear infinite;
}

.ring-middle {
  width: 75%;
  height: 75%;
  border-color: rgba(0, 240, 255, .25);
  animation: ring-rotate 45s linear infinite reverse;
}

.ring-inner {
  width: 50%;
  height: 50%;
  border-color: rgba(0, 240, 255, .35);
  animation: ring-rotate 30s linear infinite;
}

@keyframes ring-rotate {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

.table-grid {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    radial-gradient(circle at center, rgba(0, 240, 255, .05) 0%, transparent 70%);
}

.energy-pulse {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 30%;
  height: 30%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background: radial-gradient(circle, rgba(0, 240, 255, .1) 0%, transparent 70%);
  animation: energy-pulse 3s ease-in-out infinite;
}

@keyframes energy-pulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: .5; }
  50% { transform: translate(-50%, -50%) scale(1.5); opacity: 0; }
}

.circle-container {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 中心全息投影 */
.hologram-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 5;
}

.hologram-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 140px;
  height: 140px;
  transform: translate(-50%, -50%);
  border: 2px solid rgba(0, 240, 255, .3);
  border-radius: 50%;
  animation: holo-spin 10s linear infinite;
}

.hologram-ring:before {
  content: '';
  position: absolute;
  top: -4px;
  left: 50%;
  width: 8px;
  height: 8px;
  background: var(--color-primary);
  border-radius: 50%;
  box-shadow: 0 0 10px var(--color-primary);
}

@keyframes holo-spin {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

.center-hologram {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 120px;
  height: 120px;
  background: linear-gradient(135deg, rgba(0, 240, 255, .1) 0%, rgba(168, 85, 247, .1) 100%);
  border: 1px solid rgba(0, 240, 255, .4);
  border-radius: 50%;
  color: var(--color-primary);
  position: relative;
  overflow: hidden;
  box-shadow: 
    0 0 30px rgba(0, 240, 255, .2),
    inset 0 0 30px rgba(0, 240, 255, .1);
}

.holo-scanline {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(0, 240, 255, .5), transparent);
  animation: scanline 2s linear infinite;
}

@keyframes scanline {
  0% { top: 0; }
  100% { top: 100%; }
}

.alive-count {
  font-size: 36px;
  font-weight: 700;
  line-height: 1;
  text-shadow: 0 0 20px var(--color-primary);
  font-family: 'Courier New', monospace;
}

.alive-label {
  font-size: 11px;
  margin-top: 4px;
  letter-spacing: 2px;
  opacity: .8;
  text-transform: uppercase;
}

.holo-corners .corner {
  position: absolute;
  width: 12px;
  height: 12px;
  border-color: var(--color-primary);
}

.corner.top-left {
  top: 10px;
  left: 10px;
  border-top: 2px solid;
  border-left: 2px solid;
}

.corner.top-right {
  top: 10px;
  right: 10px;
  border-top: 2px solid;
  border-right: 2px solid;
}

.corner.bottom-left {
  bottom: 10px;
  left: 10px;
  border-bottom: 2px solid;
  border-left: 2px solid;
}

.corner.bottom-right {
  bottom: 10px;
  right: 10px;
  border-bottom: 2px solid;
  border-right: 2px solid;
}

/* 连接线 */
.connection-lines {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.connection-lines line {
  opacity: .3;
  transition: opacity .3s;
}

.connection-lines line.line-dead {
  opacity: .1;
  stroke: rgba(255, 51, 102, .3);
}

.seat-wrapper {
  position: absolute;
  top: 50%;
  left: 50%;
  margin-top: -55px;
  margin-left: -50px;
  z-index: 10;
  transition: transform .3s ease;
}

.seat-wrapper:hover {
  z-index: 20;
}

/* 响应式 */
@media (max-width: 768px) {
  .cyber-seat-circle {
    min-height: 350px;
    padding: 10px;
  }
  
  .center-hologram {
    width: 80px;
    height: 80px;
  }
  
  .hologram-ring {
    width: 100px;
    height: 100px;
  }
  
  .alive-count {
    font-size: 24px;
  }
  
  .alive-label {
    font-size: 9px;
  }
  
  .seat-wrapper {
    margin-top: -45px;
    margin-left: -40px;
  }
}
</style>
