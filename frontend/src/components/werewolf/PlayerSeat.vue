<template>
  <div 
    class="cyber-player-seat"
    :class="{
      'is-dead': !player.is_alive,
      'is-current': isCurrent,
      'is-selected': isSelected,
      'is-selectable': selectable,
      'is-speaking': isSpeaking,
      'is-ai': player.is_ai
    }"
    @click="handleClick"
  >
    <!-- 发言气泡 -->
    <transition name="bubble-fade">
      <div 
        v-if="speechBubble && speechBubble.content" 
        class="speech-bubble"
        :class="{ 
          'bubble-left': isLeftSide, 
          'bubble-right': !isLeftSide,
          'is-streaming': speechBubble.isStreaming 
        }"
      >
        <div class="bubble-content">
          {{ speechBubble.content }}
          <span v-if="speechBubble.isStreaming" class="typing-cursor">|</span>
        </div>
        <div class="bubble-arrow"></div>
      </div>
    </transition>
    
    <!-- 霓虹边框 -->
    <div class="neon-border"></div>
    
    <!-- 角色图片区域 -->
    <div class="role-image-container" :class="{ 'has-image': roleImage }">
      <!-- 角色图片 -->
      <img 
        v-if="roleImage" 
        :src="roleImage" 
        :alt="player.role_name || '角色'"
        class="role-image"
      />
      <!-- 默认图标 -->
      <div v-else class="default-avatar">
        <el-icon v-if="player.is_ai" :size="40"><Monitor /></el-icon>
        <el-icon v-else :size="40"><User /></el-icon>
      </div>
      
      <!-- 死亡特效 -->
      <div v-if="!player.is_alive" class="death-overlay">
        <div class="death-glitch">
          <el-icon :size="24"><Close /></el-icon>
        </div>
        <div class="death-scan"></div>
      </div>
      
      <!-- 状态指示灯 -->
      <div class="status-led" :class="statusLedClass"></div>
    </div>
    
    <!-- 玩家信息面板 -->
    <div class="info-panel">
      <div class="player-name" :title="fullPlayerName">
        {{ displayName }}
      </div>
      
      <!-- 状态标签 -->
      <div v-if="statusText" class="status-badge" :class="statusClass">
        <span class="status-dot"></span>
        {{ statusText }}
      </div>
    </div>
    
    <!-- 投票计数器 -->
    <div v-if="voteCount > 0" class="vote-counter">
      <span class="vote-num">{{ voteCount }}</span>
      <span class="vote-unit">票</span>
    </div>
    
    <!-- 发言波形 -->
    <div v-if="isSpeaking" class="speaking-waves">
      <span v-for="i in 4" :key="i" class="wave"></span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { User, Monitor, Close } from '@element-plus/icons-vue'

// 导入角色图片
import hunterImg from '@/assets/images/werewolf/roles/hunter.jpeg'
import prophetImg from '@/assets/images/werewolf/roles/prophet.jpeg'
import villager1Img from '@/assets/images/werewolf/roles/villager1.jpeg'
import villager2Img from '@/assets/images/werewolf/roles/villager2.jpeg'
import villager3Img from '@/assets/images/werewolf/roles/villager3.jpeg'
import villager4Img from '@/assets/images/werewolf/roles/villager4.jpeg'
import witchImg from '@/assets/images/werewolf/roles/witch.jpeg'
import wolf1Img from '@/assets/images/werewolf/roles/wolf1.jpeg'
import wolf2Img from '@/assets/images/werewolf/roles/wolf2.jpeg'
import wolf3Img from '@/assets/images/werewolf/roles/wolf3.jpeg'

// 角色图片映射
const roleImageMap = {
  '猎人': hunterImg,
  'hunter': hunterImg,
  '预言家': prophetImg,
  'seer': prophetImg,
  'prophet': prophetImg,
  '女巫': witchImg,
  'witch': witchImg,
  '狼人': wolf1Img,
  'werewolf': wolf1Img,
  '村民': villager1Img,
  'villager': villager1Img,
}

// 根据座位号分配村民/狼人变体图片
const villagerImages = [villager1Img, villager2Img, villager3Img, villager4Img]
const wolfImages = [wolf1Img, wolf2Img, wolf3Img]

const props = defineProps({
  player: {
    type: Object,
    required: true
  },
  seatNumber: {
    type: Number,
    required: true
  },
  isCurrent: {
    type: Boolean,
    default: false
  },
  isSelected: {
    type: Boolean,
    default: false
  },
  selectable: {
    type: Boolean,
    default: false
  },
  isSpeaking: {
    type: Boolean,
    default: false
  },
  showRole: {
    type: Boolean,
    default: false
  },
  voteCount: {
    type: Number,
    default: 0
  },
  // 发言气泡数据
  speechBubble: {
    type: Object,
    default: null
  },
  // 是否在左侧（用于确定气泡方向）
  isLeftSide: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['select'])

// 获取角色图片（游戏结束时显示所有角色图片，或真人玩家始终显示角色图片）
const roleImage = computed(() => {
  // 真人玩家始终显示角色图片，AI玩家只在 showRole 为 true 时显示
  const shouldShowRole = props.showRole || !props.player.is_ai
  
  if (!shouldShowRole) return null
  
  const roleName = props.player.role_name || props.player.role
  const roleId = props.player.role_id || ''
  
  if (!roleName) return null
  
  // 标准化角色名称
  const normalizedRole = roleName.toLowerCase()
  
  // 优先使用精确匹配
  if (roleImageMap[roleName]) {
    // 对于村民和狼人，使用座位号来分配不同的图片变体
    if (normalizedRole.includes('村民') || normalizedRole === 'villager') {
      return villagerImages[(props.seatNumber - 1) % villagerImages.length]
    }
    if (normalizedRole.includes('狼') || normalizedRole === 'werewolf') {
      return wolfImages[(props.seatNumber - 1) % wolfImages.length]
    }
    return roleImageMap[roleName]
  }
  
  // 模糊匹配
  if (normalizedRole.includes('猎人') || normalizedRole.includes('hunter')) {
    return hunterImg
  }
  if (normalizedRole.includes('预言') || normalizedRole.includes('seer') || normalizedRole.includes('prophet')) {
    return prophetImg
  }
  if (normalizedRole.includes('女巫') || normalizedRole.includes('witch')) {
    return witchImg
  }
  if (normalizedRole.includes('狼') || normalizedRole.includes('wolf') || normalizedRole.includes('werewolf')) {
    return wolfImages[(props.seatNumber - 1) % wolfImages.length]
  }
  if (normalizedRole.includes('村民') || normalizedRole.includes('villager')) {
    return villagerImages[(props.seatNumber - 1) % villagerImages.length]
  }
  
  return null
})

// 显示名称 - 真人玩家显示名称，AI玩家显示座位号，游戏结束后显示角色名
const displayName = computed(() => {
  // 如果有角色名且允许显示角色，优先显示角色名
  const roleName = props.player.role_name || props.player.role
  if (props.showRole && roleName) {
    return roleName
  }
  
  // 真人玩家显示玩家名称 + 座位号
  if (!props.player.is_ai) {
    const playerName = props.player.name || props.player.username || '玩家'
    return `${playerName}(${props.seatNumber}号)`
  }
  
  // AI玩家游戏进行中只显示座位号
  return `${props.seatNumber}号`
})

// 完整玩家名称（用于 tooltip）
const fullPlayerName = computed(() => {
  return props.player.name || props.player.username || `玩家${props.seatNumber}`
})

// 阵营名称
const teamName = computed(() => {
  const roleType = props.player.role_type || props.player.team
  switch (roleType) {
    case 'werewolf': return '狼人阵营'
    case 'villager': return '平民阵营'
    case 'god': return '神职阵营'
    default: return ''
  }
})

// 角色类型样式
const roleTypeClass = computed(() => {
  const roleType = props.player.role_type || props.player.team
  switch (roleType) {
    case 'werewolf': return 'role-werewolf'
    case 'villager': return 'role-villager'
    case 'god': return 'role-god'
    default: return ''
  }
})

// 状态LED样式
const statusLedClass = computed(() => {
  if (!props.player.is_alive) return 'led-dead'
  if (props.isSpeaking) return 'led-speaking'
  if (props.player.is_online !== false) return 'led-online'
  return 'led-offline'
})

// 状态文本
const statusText = computed(() => {
  if (!props.player.is_alive) return 'OFFLINE'
  if (props.isSpeaking) return 'SPEAKING'
  return ''
})

// 状态样式
const statusClass = computed(() => {
  if (!props.player.is_alive) return 'status-dead'
  if (props.isSpeaking) return 'status-speaking'
  return ''
})

// 点击处理
function handleClick() {
  if (props.selectable && props.player.is_alive) {
    emit('select', props.player)
  }
}
</script>

<style scoped>
.cyber-player-seat {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0;
  background: rgba(10, 10, 20, .9);
  border-radius: 12px;
  border: 1px solid rgba(0, 240, 255, .3);
  width: 100px;
  transition: all .3s ease;
  position: relative;
  backdrop-filter: blur(10px);
}

.neon-border {
  position: absolute;
  inset: -1px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(0, 240, 255, .5), rgba(168, 85, 247, .5));
  z-index: -1;
  opacity: 0;
  transition: opacity .3s;
}

.cyber-player-seat:hover .neon-border,
.cyber-player-seat.is-selected .neon-border {
  opacity: 1;
}

.cyber-player-seat.is-selectable {
  cursor: pointer;
}

.cyber-player-seat.is-selectable:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 
    0 10px 30px rgba(0, 240, 255, .2),
    0 0 20px rgba(0, 240, 255, .1);
}

.cyber-player-seat.is-current {
  border-color: var(--color-primary);
  box-shadow: 
    0 0 20px rgba(0, 240, 255, .3),
    inset 0 0 20px rgba(0, 240, 255, .1);
}

.cyber-player-seat.is-selected {
  border-color: var(--color-accent);
  box-shadow: 0 0 25px rgba(255, 0, 170, .4);
}

.cyber-player-seat.is-dead {
  opacity: .6;
  border-color: rgba(255, 51, 102, .3);
}

.cyber-player-seat.is-speaking {
  border-color: var(--color-success);
  animation: speak-pulse 1.5s infinite;
}

@keyframes speak-pulse {
  0%, 100% { box-shadow: 0 0 10px rgba(0, 255, 136, .3); }
  50% { box-shadow: 0 0 25px rgba(0, 255, 136, .6); }
}

/* 座位号全息标签 */
.seat-number-holo {
  position: absolute;
  top: 6px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, rgba(0, 240, 255, .9), rgba(0, 128, 255, .9));
  padding: 2px 10px;
  border-radius: 10px;
  box-shadow: 0 0 15px rgba(0, 240, 255, .5);
  z-index: 10;
}

.seat-number-holo .number {
  font-size: 11px;
  font-weight: 700;
  color: #0a0a12;
  font-family: 'Courier New', monospace;
}

/* 角色图片区域 - 充满卡片 */
.role-image-container {
  width: 100%;
  height: 120px;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, rgba(0, 240, 255, .1), rgba(168, 85, 247, .1));
}

.role-image-container.has-image {
  background: transparent;
}

.role-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.default-avatar {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
}

/* 死亡时角色图片变灰 */
.is-dead .role-image {
  filter: grayscale(100%) brightness(0.5);
}

.is-dead .default-avatar {
  color: rgba(255, 51, 102, .6);
}

.cyber-player-seat.is-ai .default-avatar {
  color: #a855f7;
}

/* 死亡特效 */
.death-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 51, 102, .3);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.death-glitch {
  color: #ff3366;
  animation: glitch .5s infinite;
}

@keyframes glitch {
  0%, 100% { transform: translate(0); }
  20% { transform: translate(-2px, 2px); }
  40% { transform: translate(2px, -2px); }
  60% { transform: translate(-2px, -2px); }
  80% { transform: translate(2px, 2px); }
}

.death-scan {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: #ff3366;
  animation: death-scan 1s linear infinite;
}

@keyframes death-scan {
  0% { top: 0; opacity: 1; }
  100% { top: 100%; opacity: 0; }
}

/* 状态LED */
.status-led {
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid rgba(10, 10, 20, .9);
}

.status-led.led-online {
  background: #00ff88;
  box-shadow: 0 0 8px #00ff88;
}

.status-led.led-offline {
  background: #606060;
}

.status-led.led-dead {
  background: #ff3366;
  box-shadow: 0 0 8px #ff3366;
}

.status-led.led-speaking {
  background: #00ff88;
  animation: led-blink .5s infinite;
}

@keyframes led-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: .3; }
}

/* 信息面板 */
.info-panel {
  text-align: center;
  width: 100%;
  padding: 8px 6px;
  background: rgba(10, 10, 20, .95);
}

.player-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  text-shadow: 0 0 10px rgba(0, 240, 255, .3);
}

.role-chip {
  display: inline-block;
  font-size: 9px;
  padding: 2px 8px;
  border-radius: 10px;
  margin-top: 4px;
  background: rgba(100, 100, 120, .3);
  border: 1px solid rgba(100, 100, 120, .5);
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.role-chip.role-werewolf {
  background: rgba(255, 51, 102, .2);
  border-color: rgba(255, 51, 102, .5);
  color: #ff3366;
}

.role-chip.role-villager {
  background: rgba(0, 255, 136, .2);
  border-color: rgba(0, 255, 136, .5);
  color: #00ff88;
}

.role-chip.role-god {
  background: rgba(0, 170, 255, .2);
  border-color: rgba(0, 170, 255, .5);
  color: #00aaff;
}

.status-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 9px;
  margin-top: 4px;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.status-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: currentColor;
}

.status-badge.status-dead {
  color: #ff3366;
}

.status-badge.status-speaking {
  color: #00ff88;
}

/* 投票计数器 */
.vote-counter {
  position: absolute;
  top: -8px;
  right: -8px;
  background: linear-gradient(135deg, #ff3366, #ff0055);
  color: white;
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 10px;
  display: flex;
  align-items: center;
  gap: 2px;
  box-shadow: 0 0 15px rgba(255, 51, 102, .5);
}

.vote-num {
  font-weight: 700;
  font-family: 'Courier New', monospace;
}

.vote-unit {
  font-size: 8px;
  opacity: .8;
}

/* 发言波形 */
.speaking-waves {
  position: absolute;
  bottom: -16px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 3px;
  align-items: flex-end;
}

.wave {
  width: 3px;
  height: 8px;
  background: #00ff88;
  border-radius: 2px;
  animation: wave-dance .5s ease-in-out infinite;
}

.wave:nth-child(1) { animation-delay: 0s; }
.wave:nth-child(2) { animation-delay: .1s; }
.wave:nth-child(3) { animation-delay: .2s; }
.wave:nth-child(4) { animation-delay: .3s; }

@keyframes wave-dance {
  0%, 100% { height: 8px; }
  50% { height: 16px; }
}

/* 响应式 */
@media (max-width: 768px) {
  .cyber-player-seat {
    min-width: 70px;
    padding: 10px 6px;
  }
  
  .avatar {
    width: 38px;
    height: 38px;
  }
  
  .player-name {
    font-size: 10px;
    max-width: 55px;
  }
  
  .seat-number-holo {
    padding: 2px 6px;
  }
  
  .seat-number-holo .number {
    font-size: 10px;
  }
}

/* 发言气泡样式 */
.speech-bubble {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 500px;
  z-index: 100;
  pointer-events: none;
}

.speech-bubble.bubble-left {
  left: calc(100% + 15px);
}

.speech-bubble.bubble-right {
  right: calc(100% + 15px);
}

.bubble-content {
  background: linear-gradient(135deg, rgba(15, 15, 30, 0.95), rgba(25, 25, 50, 0.95));
  border: 1px solid rgba(0, 240, 255, 0.4);
  border-radius: 12px;
  padding: 12px 16px;
  color: rgba(255, 255, 255, 0.95);
  font-size: 13px;
  line-height: 1.6;
  word-break: break-word;
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.4),
    0 0 20px rgba(0, 240, 255, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  position: relative;
  max-height: 200px;
  overflow-y: auto;
}

.speech-bubble.is-streaming .bubble-content {
  border-color: rgba(0, 255, 136, 0.5);
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.4),
    0 0 25px rgba(0, 255, 136, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.bubble-arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 0;
  height: 0;
  border: 8px solid transparent;
}

.bubble-left .bubble-arrow {
  left: -8px;
  border-right-color: rgba(0, 240, 255, 0.4);
}

.bubble-left .bubble-arrow::after {
  content: '';
  position: absolute;
  left: -6px;
  top: -7px;
  border: 7px solid transparent;
  border-right-color: rgba(15, 15, 30, 0.95);
}

.bubble-right .bubble-arrow {
  right: -8px;
  border-left-color: rgba(0, 240, 255, 0.4);
}

.bubble-right .bubble-arrow::after {
  content: '';
  position: absolute;
  right: -6px;
  top: -7px;
  border: 7px solid transparent;
  border-left-color: rgba(15, 15, 30, 0.95);
}

.typing-cursor {
  display: inline-block;
  font-weight: bold;
  color: #00ff88;
  text-shadow: 0 0 10px #00ff88;
  animation: cursorBlink 0.8s infinite;
  margin-left: 2px;
}

@keyframes cursorBlink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* 气泡动画 */
.bubble-fade-enter-active {
  animation: bubble-in 0.3s ease-out;
}

.bubble-fade-leave-active {
  animation: bubble-out 0.3s ease-in;
}

@keyframes bubble-in {
  from {
    opacity: 0;
    transform: translateY(-50%) scale(0.8);
  }
  to {
    opacity: 1;
    transform: translateY(-50%) scale(1);
  }
}

@keyframes bubble-out {
  from {
    opacity: 1;
    transform: translateY(-50%) scale(1);
  }
  to {
    opacity: 0;
    transform: translateY(-50%) scale(0.8);
  }
}

/* 气泡内滚动条样式 */
.bubble-content::-webkit-scrollbar {
  width: 4px;
}

.bubble-content::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 2px;
}

.bubble-content::-webkit-scrollbar-thumb {
  background: rgba(0, 240, 255, 0.3);
  border-radius: 2px;
}
</style>
