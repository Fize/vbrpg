<template>
  <div class="cyber-phase-indicator" :class="phaseClass">
    <!-- 背景效果 -->
    <div class="phase-bg">
      <div class="cyber-grid"></div>
      <div class="glow-effect"></div>
      <div v-if="isNight" class="stars-container">
        <span v-for="i in 15" :key="i" class="star"></span>
      </div>
      <div v-else class="sun-rays"></div>
    </div>
    
    <div class="phase-content">
      <!-- 顶部装饰线 -->
      <div class="top-line">
        <span class="line-segment"></span>
        <span class="line-dot"></span>
        <span class="line-segment"></span>
      </div>
      
      <!-- 天数显示 -->
      <div class="day-display">
        <span class="day-bracket">[</span>
        <span class="day-text">DAY</span>
        <span class="day-num">{{ String(dayNumber).padStart(2, '0') }}</span>
        <span class="day-bracket">]</span>
      </div>
      
      <!-- 阶段图标 -->
      <div class="phase-icon-container">
        <div class="icon-ring"></div>
        <div class="phase-icon">
          <el-icon v-if="isNight" :size="36"><Moon /></el-icon>
          <el-icon v-else-if="phase === 'discussion'" :size="36"><ChatDotRound /></el-icon>
          <el-icon v-else-if="phase === 'vote'" :size="36"><Stamp /></el-icon>
          <el-icon v-else :size="36"><Sunny /></el-icon>
        </div>
      </div>
      
      <!-- 阶段名称 -->
      <div class="phase-label">
        <span class="phase-name">{{ phaseName }}</span>
        <span class="phase-name-glow">{{ phaseName }}</span>
      </div>
      
      <!-- 子阶段 -->
      <div v-if="isNight && subPhase" class="sub-phase-badge">
        <span class="sub-icon">▶</span>
        <span class="sub-text">{{ subPhaseName }}</span>
      </div>
      
      <!-- 倒计时 -->
      <div v-if="countdown > 0" class="countdown-display">
        <el-icon class="countdown-icon"><Timer /></el-icon>
        <span class="countdown-time">{{ formatCountdown }}</span>
        <div class="countdown-bar">
          <div class="countdown-progress" :style="{ width: countdownProgress + '%' }"></div>
        </div>
      </div>
      
      <!-- 底部装饰线 -->
      <div class="bottom-line">
        <span class="line-segment"></span>
        <span class="line-dot"></span>
        <span class="line-segment"></span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Moon, Sunny, ChatDotRound, Stamp, Timer } from '@element-plus/icons-vue'
import { getPhaseCategory, getNightSubPhaseLabel } from '@/utils/phase'

const props = defineProps({
  // 当前天数
  dayNumber: {
    type: Number,
    default: 1
  },
  // 游戏阶段: 'night' | 'day' | 'discussion' | 'vote' | 'result' | 'waiting'
  phase: {
    type: String,
    default: 'night',
    validator: (v) => ['night', 'day', 'discussion', 'vote', 'result', 'waiting'].includes(v)
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
  },
  // 倒计时总时长（用于计算进度条）
  totalCountdown: {
    type: Number,
    default: 60
  }
})

// 归一化阶段
const phaseCategory = computed(() => getPhaseCategory(props.phase) || props.phase || 'night')

// 是否是夜晚
const isNight = computed(() => phaseCategory.value === 'night')

// 阶段样式类
const phaseClass = computed(() => ({
  'is-night': isNight.value,
  'is-day': !isNight.value,
  'is-vote': phaseCategory.value === 'vote'
}))

// 阶段名称
const phaseName = computed(() => {
  switch (phaseCategory.value) {
    case 'night': return 'NIGHT'
    case 'day': return 'DAY'
    case 'discussion': return 'DISCUSS'
    case 'vote': return 'VOTE'
    case 'result': return 'RESULT'
    case 'waiting': return 'WAITING'
    default: {
      const fallback = phaseCategory.value || props.phase || 'PHASE'
      return fallback.toString().toUpperCase()
    }
  }
})

// 子阶段名称
const subPhaseName = computed(() => getNightSubPhaseLabel(props.subPhase))

// 格式化倒计时
const formatCountdown = computed(() => {
  const minutes = Math.floor(props.countdown / 60)
  const seconds = props.countdown % 60
  if (minutes > 0) {
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }
  return `${seconds.toString().padStart(2, '0')}`
})

// 倒计时进度百分比
const countdownProgress = computed(() => {
  if (props.totalCountdown <= 0) return 0
  return (props.countdown / props.totalCountdown) * 100
})
</script>

<style scoped>
.cyber-phase-indicator {
  position: relative;
  padding: 20px 28px;
  border-radius: 16px;
  overflow: hidden;
  transition: all .5s ease;
  border: 1px solid rgba(0, 240, 255, .3);
  background: rgba(10, 10, 20, .9);
  backdrop-filter: blur(10px);
}

.cyber-phase-indicator.is-night {
  border-color: rgba(168, 85, 247, .4);
  background: linear-gradient(135deg, rgba(10, 10, 30, .95), rgba(20, 10, 40, .95));
}

.cyber-phase-indicator.is-day {
  border-color: rgba(255, 170, 0, .4);
  background: linear-gradient(135deg, rgba(30, 20, 10, .95), rgba(40, 25, 10, .95));
}

.cyber-phase-indicator.is-vote {
  border-color: rgba(255, 51, 102, .5);
  background: linear-gradient(135deg, rgba(30, 10, 20, .95), rgba(40, 10, 25, .95));
}

/* 背景效果 */
.phase-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.cyber-grid {
  position: absolute;
  inset: 0;
  background-image: 
    linear-gradient(rgba(0, 240, 255, .03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 240, 255, .03) 1px, transparent 1px);
  background-size: 20px 20px;
}

.glow-effect {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 150%;
  height: 150%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  opacity: .3;
}

.is-night .glow-effect {
  background: radial-gradient(circle, rgba(168, 85, 247, .3), transparent 70%);
}

.is-day .glow-effect {
  background: radial-gradient(circle, rgba(255, 170, 0, .3), transparent 70%);
}

.is-vote .glow-effect {
  background: radial-gradient(circle, rgba(255, 51, 102, .3), transparent 70%);
}

/* 星星 */
.stars-container {
  position: absolute;
  inset: 0;
}

.star {
  position: absolute;
  width: 2px;
  height: 2px;
  background: white;
  border-radius: 50%;
  animation: twinkle 2s infinite;
}

.star:nth-child(odd) { animation-delay: .7s; }
.star:nth-child(1) { top: 15%; left: 10%; }
.star:nth-child(2) { top: 25%; left: 85%; }
.star:nth-child(3) { top: 40%; left: 30%; }
.star:nth-child(4) { top: 55%; left: 70%; }
.star:nth-child(5) { top: 70%; left: 20%; }
.star:nth-child(6) { top: 80%; left: 90%; }
.star:nth-child(7) { top: 10%; left: 50%; }
.star:nth-child(8) { top: 35%; left: 65%; }
.star:nth-child(9) { top: 60%; left: 45%; }
.star:nth-child(10) { top: 85%; left: 35%; }
.star:nth-child(11) { top: 20%; left: 5%; }
.star:nth-child(12) { top: 45%; left: 95%; }
.star:nth-child(13) { top: 65%; left: 8%; }
.star:nth-child(14) { top: 30%; left: 75%; }
.star:nth-child(15) { top: 90%; left: 55%; }

@keyframes twinkle {
  0%, 100% { opacity: .3; }
  50% { opacity: 1; }
}

/* 太阳光芒 */
.sun-rays {
  position: absolute;
  top: -30px;
  right: -30px;
  width: 80px;
  height: 80px;
  background: radial-gradient(circle, rgba(255, 200, 50, .4) 0%, transparent 70%);
  animation: sun-pulse 3s ease-in-out infinite;
}

@keyframes sun-pulse {
  0%, 100% { transform: scale(1); opacity: .4; }
  50% { transform: scale(1.2); opacity: .6; }
}

/* 内容区 */
.phase-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

/* 装饰线 */
.top-line,
.bottom-line {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.line-segment {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 240, 255, .5), transparent);
}

.line-dot {
  width: 6px;
  height: 6px;
  background: var(--color-primary);
  clip-path: polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%);
}

/* 天数显示 */
.day-display {
  display: flex;
  align-items: center;
  gap: 4px;
  font-family: 'Courier New', monospace;
}

.day-bracket {
  color: var(--color-primary);
  font-size: 18px;
  font-weight: 700;
  text-shadow: 0 0 10px var(--color-primary);
}

.day-text {
  color: var(--color-text-secondary);
  font-size: 12px;
  letter-spacing: 2px;
}

.day-num {
  color: var(--color-primary);
  font-size: 22px;
  font-weight: 700;
  text-shadow: 0 0 15px var(--color-primary);
}

/* 阶段图标 */
.phase-icon-container {
  position: relative;
  margin: 8px 0;
}

.icon-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 70px;
  height: 70px;
  transform: translate(-50%, -50%);
  border: 2px solid rgba(0, 240, 255, .3);
  border-radius: 50%;
  animation: icon-ring-spin 6s linear infinite;
}

.is-night .icon-ring { border-color: rgba(168, 85, 247, .4); }
.is-day .icon-ring { border-color: rgba(255, 170, 0, .4); }
.is-vote .icon-ring { border-color: rgba(255, 51, 102, .5); }

@keyframes icon-ring-spin {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

.phase-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  background: rgba(0, 240, 255, .1);
  border-radius: 50%;
  color: var(--color-primary);
}

.is-night .phase-icon {
  background: rgba(168, 85, 247, .15);
  color: #a855f7;
}

.is-day .phase-icon {
  background: rgba(255, 170, 0, .15);
  color: #ffaa00;
}

.is-vote .phase-icon {
  background: rgba(255, 51, 102, .15);
  color: #ff3366;
}

/* 阶段名称 */
.phase-label {
  position: relative;
}

.phase-name {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 4px;
  text-transform: uppercase;
  color: var(--color-text-primary);
}

.phase-name-glow {
  position: absolute;
  top: 0;
  left: 0;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 4px;
  text-transform: uppercase;
  color: var(--color-primary);
  filter: blur(8px);
  opacity: .5;
}

.is-night .phase-name-glow { color: #a855f7; }
.is-day .phase-name-glow { color: #ffaa00; }
.is-vote .phase-name-glow { color: #ff3366; }

/* 子阶段 */
.sub-phase-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: rgba(168, 85, 247, .15);
  border: 1px solid rgba(168, 85, 247, .3);
  border-radius: 20px;
  font-size: 12px;
  color: #a855f7;
}

.sub-icon {
  font-size: 8px;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: .3; }
}

/* 倒计时 */
.countdown-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  padding: 8px 20px;
  background: rgba(0, 0, 0, .3);
  border-radius: 12px;
  border: 1px solid rgba(0, 240, 255, .2);
  min-width: 120px;
}

.countdown-icon {
  color: var(--color-text-secondary);
  font-size: 16px;
}

.countdown-time {
  font-size: 28px;
  font-weight: 700;
  font-family: 'Courier New', monospace;
  color: var(--color-primary);
  text-shadow: 0 0 15px var(--color-primary);
}

.countdown-bar {
  width: 100%;
  height: 3px;
  background: rgba(0, 240, 255, .2);
  border-radius: 2px;
  overflow: hidden;
}

.countdown-progress {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-accent));
  border-radius: 2px;
  transition: width .3s linear;
}

/* 响应式 */
@media (max-width: 768px) {
  .cyber-phase-indicator {
    padding: 14px 20px;
  }
  
  .day-num {
    font-size: 18px;
  }
  
  .phase-name {
    font-size: 18px;
    letter-spacing: 2px;
  }
  
  .phase-name-glow {
    font-size: 18px;
    letter-spacing: 2px;
  }
  
  .countdown-time {
    font-size: 22px;
  }
}
</style>
