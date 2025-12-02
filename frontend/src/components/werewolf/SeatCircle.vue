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
      <svg class="connection-lines" :viewBox="`0 0 ${containerWidth} ${containerHeight}`">
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
          :x1="containerWidth / 2"
          :y1="containerHeight / 2"
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
        :key="player.id || `seat-${player.seat_number || index}`"
        class="seat-wrapper"
        :style="getSeatStyle(index)"
      >
        <PlayerSeat
          :player="player"
          :seat-number="player.seat_number || index + 1"
          :is-current="player.id === currentPlayerId"
          :is-selected="selectedPlayerId === player.id"
          :selectable="selectable && player.is_alive"
          :is-speaking="isSpeaking(player)"
          :show-role="showRoles"
          :vote-count="getVoteCount(player.id)"
          :speech-bubble="getSpeechBubble(player.seat_number || index + 1)"
          :is-left-side="isLeftSide(index)"
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
    type: [String, Number],
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
  // 发言气泡数据
  speechBubbles: {
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
const containerWidth = ref(800)
const containerHeight = ref(600)

// 存活玩家数量
const aliveCount = computed(() => {
  return props.players.filter(p => p.is_alive).length
})

// 容器样式
const containerStyle = computed(() => ({
  width: `${containerWidth.value}px`,
  height: `${containerHeight.value}px`
}))

// 计算每个座位的位置 - 两侧对称布局
function getSeatStyle(index) {
  const totalPlayers = props.players.length || 10
  const halfPlayers = Math.ceil(totalPlayers / 2)
  
  // 使用实际容器尺寸
  const width = containerWidth.value
  const height = containerHeight.value
  
  // 判断左侧还是右侧
  const isLeftSide = index < halfPlayers
  const positionInSide = isLeftSide ? index : index - halfPlayers
  const playersOnSide = isLeftSide ? halfPlayers : totalPlayers - halfPlayers
  
  // 计算垂直间距，让玩家更均匀分布
  // 留出上下边距 (假设座位高度约120px，留出160px空间确保不溢出)
  const availableHeight = Math.max(height - 160, height * 0.6)
  
  let y = 0
  if (playersOnSide > 1) {
    // 分布在 availableHeight 范围内，首尾对齐
    const step = availableHeight / (playersOnSide - 1)
    y = -(availableHeight / 2) + (step * positionInSide)
  } else {
    // 只有一个玩家时居中
    y = 0
  }
  
  // 左侧玩家在左边，右侧玩家在右边
  // 使用 45% 的宽度作为偏移量，这样左右两边相距 90% 的宽度
  const horizontalOffset = width * 0.45
  const x = isLeftSide ? -horizontalOffset : horizontalOffset
  
  return {
    transform: `translate(${x}px, ${y}px)`
  }
}

// 获取投票数
function getVoteCount(playerId) {
  return props.votes[playerId] || 0
}

// 获取发言气泡数据
function getSpeechBubble(seatNumber) {
  return props.speechBubbles[seatNumber] || null
}

// 判断是否在左侧
function isLeftSide(index) {
  const totalPlayers = props.players.length || 10
  const halfPlayers = Math.ceil(totalPlayers / 2)
  return index < halfPlayers
}

// 判断玩家是否正在发言
function isSpeaking(player) {
  if (!props.speakingPlayerId) return false
  // speakingPlayerId 可能是座位号（Number）或玩家ID（String）
  const speakingSeat = Number(props.speakingPlayerId)
  if (!isNaN(speakingSeat)) {
    return player.seat_number === speakingSeat
  }
  return player.id === props.speakingPlayerId
}

// 获取连接线终点坐标 - 两侧对称布局
function getLineEndX(index) {
  const totalPlayers = props.players.length || 10
  const halfPlayers = Math.ceil(totalPlayers / 2)
  const isLeftSide = index < halfPlayers
  
  const width = containerWidth.value
  const horizontalOffset = width * 0.45
  
  return (width / 2) + (isLeftSide ? -horizontalOffset : horizontalOffset)
}

function getLineEndY(index) {
  const totalPlayers = props.players.length || 10
  const halfPlayers = Math.ceil(totalPlayers / 2)
  const isLeftSide = index < halfPlayers
  const positionInSide = isLeftSide ? index : index - halfPlayers
  const playersOnSide = isLeftSide ? halfPlayers : totalPlayers - halfPlayers
  
  const height = containerHeight.value
  const availableHeight = Math.max(height - 160, height * 0.6)
  
  let yOffset = 0
  if (playersOnSide > 1) {
    const step = availableHeight / (playersOnSide - 1)
    yOffset = -(availableHeight / 2) + (step * positionInSide)
  }
  
  return (height / 2) + yOffset
}

// 选择处理
function handleSelect(player) {
  emit('select', player)
}

// 响应式调整大小 - 支持更大的尺寸
function updateSize() {
  if (circleRef.value) {
    const rect = circleRef.value.getBoundingClientRect()
    containerWidth.value = rect.width
    containerHeight.value = rect.height
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
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 30px;
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
  width: 200px;
  height: 200px;
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
  width: 180px;
  height: 180px;
  background: linear-gradient(135deg, rgba(0, 240, 255, .1) 0%, rgba(168, 85, 247, .1) 100%);
  border: 2px solid rgba(0, 240, 255, .4);
  border-radius: 50%;
  color: var(--color-primary);
  position: relative;
  overflow: hidden;
  box-shadow: 
    0 0 40px rgba(0, 240, 255, .3),
    inset 0 0 40px rgba(0, 240, 255, .15);
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
  font-size: 48px;
  font-weight: 700;
  line-height: 1;
  text-shadow: 0 0 25px var(--color-primary);
  font-family: 'Courier New', monospace;
}

.alive-label {
  font-size: 13px;
  margin-top: 6px;
  letter-spacing: 3px;
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
    min-height: 450px;
    padding: 15px;
  }
  
  .center-hologram {
    width: 120px;
    height: 120px;
  }
  
  .hologram-ring {
    width: 140px;
    height: 140px;
  }
  
  .alive-count {
    font-size: 32px;
  }
  
  .alive-label {
    font-size: 10px;
  }
  
  .seat-wrapper {
    margin-top: -45px;
    margin-left: -40px;
  }
}
</style>
