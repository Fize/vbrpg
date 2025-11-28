<template>
  <div class="seat-circle" ref="circleRef">
    <div class="circle-container" :style="containerStyle">
      <!-- 中心信息区域 -->
      <div class="center-area">
        <slot name="center">
          <div class="center-info">
            <span class="alive-count">{{ aliveCount }}</span>
            <span class="alive-label">存活</span>
          </div>
        </slot>
      </div>
      
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
.seat-circle {
  width: 100%;
  height: 100%;
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.circle-container {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.center-area {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 1;
}

.center-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100px;
  height: 100px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  color: white;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
}

.alive-count {
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
}

.alive-label {
  font-size: 14px;
  margin-top: 4px;
  opacity: 0.9;
}

.seat-wrapper {
  position: absolute;
  top: 50%;
  left: 50%;
  margin-top: -50px; /* 座位高度的一半 */
  margin-left: -45px; /* 座位宽度的一半 */
  z-index: 2;
}

/* 响应式 */
@media (max-width: 768px) {
  .seat-circle {
    min-height: 300px;
    padding: 10px;
  }
  
  .center-info {
    width: 70px;
    height: 70px;
  }
  
  .alive-count {
    font-size: 24px;
  }
  
  .alive-label {
    font-size: 12px;
  }
  
  .seat-wrapper {
    margin-top: -40px;
    margin-left: -35px;
  }
}
</style>
