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
    <!-- 霓虹边框 -->
    <div class="neon-border"></div>
    
    <!-- 座位号全息标签 -->
    <div class="seat-number-holo">
      <span class="number">{{ seatNumber }}</span>
    </div>
    
    <!-- 玩家头像区域 -->
    <div class="avatar-container">
      <div class="avatar-ring"></div>
      <div class="avatar" :class="{ 'has-image': roleImage }">
        <!-- 角色图片 -->
        <img 
          v-if="roleImage" 
          :src="roleImage" 
          :alt="player.role_name || '角色'"
          class="role-image"
        />
        <!-- 默认图标 -->
        <template v-else>
          <el-icon v-if="player.is_ai" :size="28"><Monitor /></el-icon>
          <el-icon v-else :size="28"><User /></el-icon>
        </template>
      </div>
      
      <!-- 死亡特效 -->
      <div v-if="!player.is_alive" class="death-overlay">
        <div class="death-glitch">
          <el-icon :size="20"><Close /></el-icon>
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
      
      <!-- 阵营标签（显示角色时） -->
      <div v-if="showRole && teamName" class="role-chip" :class="roleTypeClass">
        {{ teamName }}
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
  }
})

const emit = defineEmits(['select'])

// 获取角色图片
const roleImage = computed(() => {
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

// 显示名称 - 优先显示角色名
const displayName = computed(() => {
  // 如果有角色名且允许显示角色，优先显示角色名
  const roleName = props.player.role_name || props.player.role
  if (props.showRole && roleName) {
    return roleName
  }
  
  // 否则显示玩家名或座位号
  const name = props.player.name || props.player.username
  // 如果是 AI 名字（格式如 AI-XXX-1-abc），简化显示
  if (name && name.startsWith('AI-')) {
    return `AI-${props.seatNumber}`
  }
  return name || `玩家${props.seatNumber}`
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
  padding: 12px 10px;
  background: rgba(10, 10, 20, .9);
  border-radius: 12px;
  border: 1px solid rgba(0, 240, 255, .3);
  min-width: 90px;
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
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, rgba(0, 240, 255, .9), rgba(0, 128, 255, .9));
  padding: 2px 10px;
  border-radius: 10px;
  box-shadow: 0 0 15px rgba(0, 240, 255, .5);
}

.seat-number-holo .number {
  font-size: 11px;
  font-weight: 700;
  color: #0a0a12;
  font-family: 'Courier New', monospace;
}

/* 头像区域 */
.avatar-container {
  position: relative;
  margin-bottom: 8px;
}

.avatar-ring {
  position: absolute;
  top: -4px;
  left: -4px;
  right: -4px;
  bottom: -4px;
  border: 1px solid rgba(0, 240, 255, .3);
  border-radius: 50%;
  animation: ring-spin 8s linear infinite;
}

@keyframes ring-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(0, 240, 255, .2), rgba(168, 85, 247, .2));
  border: 2px solid rgba(0, 240, 255, .5);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
  position: relative;
  overflow: hidden;
}

/* 角色图片样式 */
.avatar.has-image {
  background: transparent;
  padding: 0;
}

.role-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

/* 死亡时角色图片变灰 */
.is-dead .role-image {
  filter: grayscale(100%) brightness(0.5);
}

.avatar:before {
  content: '';
  position: absolute;
  top: 0;
  left: -50%;
  width: 50%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, .1), transparent);
  animation: avatar-shine 3s infinite;
}

@keyframes avatar-shine {
  0% { left: -50%; }
  100% { left: 150%; }
}

.cyber-player-seat.is-ai .avatar {
  background: linear-gradient(135deg, rgba(168, 85, 247, .2), rgba(0, 240, 255, .2));
  border-color: rgba(168, 85, 247, .5);
  color: #a855f7;
}

.cyber-player-seat.is-dead .avatar {
  background: rgba(50, 50, 60, .5);
  border-color: rgba(255, 51, 102, .3);
  color: rgba(255, 51, 102, .6);
}

/* 死亡特效 */
.death-overlay {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: rgba(255, 51, 102, .2);
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
  bottom: 0;
  right: 0;
  width: 12px;
  height: 12px;
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
}

.player-name {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 75px;
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
</style>
