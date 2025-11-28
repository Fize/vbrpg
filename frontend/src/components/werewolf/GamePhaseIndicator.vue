<template>
  <div class="game-phase-indicator" :class="phaseClass">
    <div class="phase-background">
      <!-- 背景动画 -->
      <div class="stars" v-if="isNight">
        <span v-for="i in 20" :key="i" class="star"></span>
      </div>
      <div class="sun" v-else></div>
    </div>
    
    <div class="phase-content">
      <!-- 天数显示 -->
      <div class="day-info">
        <span class="day-label">第</span>
        <span class="day-number">{{ dayNumber }}</span>
        <span class="day-label">天</span>
      </div>
      
      <!-- 阶段图标 -->
      <div class="phase-icon">
        <el-icon v-if="isNight" :size="32"><Moon /></el-icon>
        <el-icon v-else-if="phase === 'discussion'" :size="32"><ChatDotRound /></el-icon>
        <el-icon v-else-if="phase === 'vote'" :size="32"><Stamp /></el-icon>
        <el-icon v-else :size="32"><Sunny /></el-icon>
      </div>
      
      <!-- 阶段名称 -->
      <div class="phase-name">{{ phaseName }}</div>
      
      <!-- 子阶段（夜晚专用） -->
      <div v-if="isNight && subPhase" class="sub-phase">
        {{ subPhaseName }}
      </div>
      
      <!-- 倒计时 -->
      <div v-if="countdown > 0" class="countdown">
        <el-icon><Timer /></el-icon>
        <span class="countdown-time">{{ formatCountdown }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Moon, Sunny, ChatDotRound, Stamp, Timer } from '@element-plus/icons-vue'

const props = defineProps({
  // 当前天数
  dayNumber: {
    type: Number,
    default: 1
  },
  // 游戏阶段: 'night' | 'day' | 'discussion' | 'vote' | 'result'
  phase: {
    type: String,
    default: 'night',
    validator: (v) => ['night', 'day', 'discussion', 'vote', 'result'].includes(v)
  },
  // 夜晚子阶段: 'werewolf' | 'seer' | 'witch' | 'hunter' | null
  subPhase: {
    type: String,
    default: null
  },
  // 倒计时秒数
  countdown: {
    type: Number,
    default: 0
  }
})

// 是否是夜晚
const isNight = computed(() => props.phase === 'night')

// 阶段样式类
const phaseClass = computed(() => ({
  'is-night': isNight.value,
  'is-day': !isNight.value,
  'is-vote': props.phase === 'vote'
}))

// 阶段名称
const phaseName = computed(() => {
  switch (props.phase) {
    case 'night': return '夜晚'
    case 'day': return '白天'
    case 'discussion': return '讨论'
    case 'vote': return '投票'
    case 'result': return '结算'
    default: return props.phase
  }
})

// 子阶段名称
const subPhaseName = computed(() => {
  switch (props.subPhase) {
    case 'werewolf': return '狼人行动'
    case 'seer': return '预言家查验'
    case 'witch': return '女巫行动'
    case 'hunter': return '猎人技能'
    default: return ''
  }
})

// 格式化倒计时
const formatCountdown = computed(() => {
  const minutes = Math.floor(props.countdown / 60)
  const seconds = props.countdown % 60
  if (minutes > 0) {
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }
  return `${seconds}s`
})
</script>

<style scoped>
.game-phase-indicator {
  position: relative;
  padding: 16px 24px;
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.5s ease;
}

.game-phase-indicator.is-night {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  color: white;
}

.game-phase-indicator.is-day {
  background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
  color: #5a3e36;
}

.game-phase-indicator.is-vote {
  background: linear-gradient(135deg, #f5af19 0%, #f12711 100%);
  color: white;
}

.phase-background {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

/* 星星动画 */
.stars {
  width: 100%;
  height: 100%;
  position: relative;
}

.star {
  position: absolute;
  width: 2px;
  height: 2px;
  background: white;
  border-radius: 50%;
  animation: twinkle 2s infinite;
}

.star:nth-child(odd) {
  animation-delay: 0.5s;
}

.star:nth-child(1) { top: 10%; left: 20%; }
.star:nth-child(2) { top: 20%; left: 80%; }
.star:nth-child(3) { top: 30%; left: 40%; }
.star:nth-child(4) { top: 40%; left: 60%; }
.star:nth-child(5) { top: 50%; left: 10%; }
.star:nth-child(6) { top: 60%; left: 90%; }
.star:nth-child(7) { top: 70%; left: 30%; }
.star:nth-child(8) { top: 80%; left: 70%; }
.star:nth-child(9) { top: 15%; left: 50%; }
.star:nth-child(10) { top: 85%; left: 15%; }
.star:nth-child(11) { top: 25%; left: 5%; }
.star:nth-child(12) { top: 35%; left: 85%; }
.star:nth-child(13) { top: 45%; left: 25%; }
.star:nth-child(14) { top: 55%; left: 75%; }
.star:nth-child(15) { top: 65%; left: 45%; }
.star:nth-child(16) { top: 75%; left: 55%; }
.star:nth-child(17) { top: 5%; left: 35%; }
.star:nth-child(18) { top: 90%; left: 65%; }
.star:nth-child(19) { top: 95%; left: 95%; }
.star:nth-child(20) { top: 8%; left: 92%; }

@keyframes twinkle {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}

/* 太阳 */
.sun {
  position: absolute;
  top: -20px;
  right: -20px;
  width: 60px;
  height: 60px;
  background: radial-gradient(circle, #fff 0%, #ffd700 50%, transparent 70%);
  border-radius: 50%;
  opacity: 0.6;
}

.phase-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.day-info {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.day-label {
  font-size: 14px;
  opacity: 0.8;
}

.day-number {
  font-size: 24px;
  font-weight: 700;
}

.phase-icon {
  margin: 8px 0;
}

.phase-name {
  font-size: 20px;
  font-weight: 600;
}

.sub-phase {
  font-size: 14px;
  opacity: 0.8;
  padding: 4px 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
}

.countdown {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 6px 16px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 20px;
}

.countdown-time {
  font-size: 18px;
  font-weight: 600;
  font-family: monospace;
}

/* 响应式 */
@media (max-width: 768px) {
  .game-phase-indicator {
    padding: 12px 16px;
  }
  
  .day-number {
    font-size: 20px;
  }
  
  .phase-name {
    font-size: 16px;
  }
}
</style>
