<template>
  <div class="crime-scene-board" ref="boardRef">
    <h3 class="board-title">犯罪现场</h3>

    <!-- Locations Grid -->
    <div class="locations-section">
      <h4>地点</h4>
      <div class="locations-grid">
        <div
          v-for="location in locations"
          :key="location"
          class="location-card"
          :class="{ investigated: isLocationInvestigated(location) }"
          @click="handleLocationClick(location)"
        >
          <div class="location-icon">📍</div>
          <div class="location-name">{{ location }}</div>
          <div v-if="isLocationInvestigated(location)" class="investigated-badge">
            <el-icon><Check /></el-icon>
            已调查
          </div>
        </div>
      </div>
    </div>

    <!-- Revealed Clues -->
    <div class="clues-section">
      <h4>已揭示线索 ({{ revealedClues.length }})</h4>
      <div v-if="revealedClues.length > 0" class="clues-grid">
        <div
          v-for="(clue, index) in revealedClues"
          :key="index"
          class="clue-card"
        >
          <div class="clue-type">{{ getClueTypeLabel(clue) }}</div>
          <div class="clue-content">{{ getClueContent(clue) }}</div>
          <div class="clue-revealer">
            {{ getPlayerName(clue.player_id) }} 揭示
          </div>
        </div>
      </div>
      <EmptyState
        v-else
        icon="Collection"
        title="暂无线索"
        description="等待玩家揭示线索"
        size="small"
      />
    </div>

    <!-- Accusations History -->
    <div class="accusations-section">
      <h4>指控记录 ({{ accusations.length }})</h4>
      <div v-if="accusations.length > 0" class="accusations-list">
        <div
          v-for="(accusation, index) in accusations"
          :key="index"
          class="accusation-item"
        >
          <div class="accusation-player">
            {{ getPlayerName(accusation.player_id) }}
          </div>
          <div class="accusation-details">
            <el-tag size="small" type="warning">{{ accusation.accusation.murderer }}</el-tag>
            <el-tag size="small" type="danger">{{ accusation.accusation.weapon }}</el-tag>
            <el-tag size="small" type="info">{{ accusation.accusation.location }}</el-tag>
          </div>
        </div>
      </div>
      <EmptyState
        v-else
        icon="Document"
        title="暂无指控"
        description="等待玩家进行指控"
        size="small"
      />
    </div>

    <!-- Player Hands Summary (for transparency) -->
    <div class="hands-section">
      <h4>手牌数量</h4>
      <div class="hands-grid">
        <div
          v-for="participant in participants"
          :key="participant.id"
          class="hand-summary"
          :class="{ 'is-current': isCurrentPlayer(participant) }"
        >
          <div class="player-avatar">
            {{ getPlayerInitial(participant) }}
          </div>
          <div class="player-info">
            <div class="player-name">{{ getParticipantName(participant) }}</div>
            <div class="card-count">
              {{ getHandCount(participant) }} 张卡
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Check } from '@element-plus/icons-vue'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  gameState: {
    type: Object,
    required: true
  },
  participants: {
    type: Array,
    default: () => []
  }
})

// Parse game data
const gameData = computed(() => {
  if (typeof props.gameState.game_data === 'string') {
    return JSON.parse(props.gameState.game_data)
  }
  return props.gameState.game_data || {}
})

const locations = computed(() => gameData.value.locations || [])
const revealedClues = computed(() => gameData.value.revealed_clues || [])
const accusations = computed(() => gameData.value.accusations || [])
const playerHands = computed(() => gameData.value.player_hands || {})
const currentPlayers = computed(() => gameData.value.players || [])

// Methods
const isLocationInvestigated = (location) => {
  return revealedClues.value.some(
    clue => clue.type === 'investigation' && clue.location === location
  )
}

const getClueTypeLabel = (clue) => {
  if (clue.type === 'investigation') return '🔍 调查'
  if (clue.type === 'card') return '🃏 卡牌'
  return '❓ 未知'
}

const getClueContent = (clue) => {
  if (clue.type === 'investigation') {
    return `在 ${clue.location} 发现线索`
  }
  if (clue.type === 'card' && clue.card) {
    return `${clue.card.name} (${clue.card.type})`
  }
  return '线索内容'
}

const getPlayerName = (playerId) => {
  const participant = props.participants.find(
    p => p.player_id === playerId || `AI_${p.id}` === playerId
  )
  if (!participant) return playerId
  
  if (participant.is_ai_agent) {
    return `AI-${participant.ai_personality}`
  }
  return participant.player?.username || '未知玩家'
}

const getParticipantName = (participant) => {
  if (participant.is_ai_agent) {
    return `AI-${participant.ai_personality}`
  }
  return participant.player?.username || '未知玩家'
}

const getPlayerInitial = (participant) => {
  const name = getParticipantName(participant)
  return name.charAt(0).toUpperCase()
}

const getHandCount = (participant) => {
  const playerId = participant.player_id || `AI_${participant.id}`
  const hand = playerHands.value[playerId]
  return hand ? hand.length : 0
}

const isCurrentPlayer = (participant) => {
  const playerId = participant.player_id || `AI_${participant.id}`
  return playerId === props.gameState.current_turn_player_id
}
</script>

<style scoped>
.crime-scene-board {
  width: 100%;
}

.board-title {
  text-align: center;
  font-size: 28px;
  margin-bottom: 30px;
  color: #303133;
}

.locations-section,
.clues-section,
.accusations-section,
.hands-section {
  margin-bottom: 30px;
}

h4 {
  font-size: 18px;
  margin-bottom: 15px;
  color: #606266;
  border-bottom: 2px solid #DCDFE6;
  padding-bottom: 8px;
}

/* Locations */
.locations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 15px;
}

.location-card {
  background: #f5f7fa;
  border: 2px solid #DCDFE6;
  border-radius: 8px;
  padding: 15px;
  text-align: center;
  transition: all 0.3s;
  cursor: default;
}

.location-card.investigated {
  background: #e1f3d8;
  border-color: #67c23a;
}

.location-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.location-name {
  font-weight: 600;
  color: #303133;
  margin-bottom: 5px;
}

.investigated-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  color: #67c23a;
  font-size: 12px;
  margin-top: 8px;
}

/* Clues */
.clues-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 15px;
}

.clue-card {
  background: white;
  border: 1px solid #DCDFE6;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.clue-type {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.clue-content {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.clue-revealer {
  font-size: 12px;
  color: #606266;
  font-style: italic;
}

/* Accusations */
.accusations-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.accusation-item {
  background: white;
  border: 1px solid #DCDFE6;
  border-radius: 8px;
  padding: 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.accusation-player {
  font-weight: 600;
  color: #303133;
  min-width: 150px;
}

.accusation-details {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* Hands */
.hands-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 15px;
}

.hand-summary {
  background: white;
  border: 2px solid #DCDFE6;
  border-radius: 8px;
  padding: 15px;
  display: flex;
  align-items: center;
  gap: 15px;
  transition: all 0.3s;
}

.hand-summary.is-current {
  border-color: #409eff;
  background: #ecf5ff;
}

.player-avatar {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: bold;
}

.player-info {
  flex: 1;
}

.player-name {
  font-weight: 600;
  color: #303133;
  margin-bottom: 5px;
}

.card-count {
  font-size: 14px;
  color: #606266;
}

.empty-state {
  padding: 20px;
  text-align: center;
}

/* Responsive - Enhanced Mobile Support */
@media (max-width: 768px) {
  .crime-scene-board {
    padding: 12px;
  }

  .board-title {
    font-size: 20px;
    padding: 12px 0;
  }

  .locations-section h4,
  .clues-section h4,
  .accusations-section h4,
  .hands-section h4 {
    font-size: 16px;
    margin-bottom: 12px;
  }

  .locations-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 12px;
  }

  .location-card {
    padding: 12px;
    min-height: 100px;
  }

  .location-icon {
    font-size: 28px;
  }

  .location-name {
    font-size: 14px;
  }

  .clues-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .clue-card {
    padding: 12px;
  }

  .hands-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .hand-summary {
    padding: 12px;
  }

  .accusation-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
    padding: 12px;
  }

  .accusation-player {
    min-width: auto;
    width: 100%;
  }

  .accusation-details {
    width: 100%;
    justify-content: flex-start;
  }
}

/* Extra Small Devices (< 480px) */
@media (max-width: 480px) {
  .crime-scene-board {
    padding: 8px;
  }

  .board-title {
    font-size: 18px;
  }

  .locations-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }

  .location-card {
    padding: 10px;
    min-height: 90px;
  }

  .location-icon {
    font-size: 24px;
  }

  .location-name {
    font-size: 13px;
  }

  .investigated-badge {
    font-size: 10px;
    padding: 2px 6px;
  }

  .clue-card {
    padding: 10px;
  }

  .clue-type {
    font-size: 12px;
  }

  .clue-content {
    font-size: 14px;
  }

  .clue-revealer {
    font-size: 11px;
  }

  .player-avatar {
    width: 40px;
    height: 40px;
    font-size: 18px;
  }

  .player-name {
    font-size: 14px;
  }

  .card-count {
    font-size: 12px;
  }
}

/* Touch-friendly interactions */
@media (hover: none) and (pointer: coarse) {
  .location-card {
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }

  .location-card:active {
    transform: scale(0.98);
    transition: transform 0.1s ease;
  }

  .hand-summary:active {
    transform: scale(0.98);
    transition: transform 0.1s ease;
  }

  /* Increase touch target size */
  .location-card,
  .hand-summary,
  .accusation-item {
    min-height: 48px; /* Apple's minimum recommended touch target */
  }
}

/* Horizontal scrolling for small screens */
@media (max-width: 640px) {
  .accusations-list {
    max-height: 300px;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch; /* Smooth scrolling on iOS */
  }

  .clues-grid {
    max-height: 400px;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
  }
}

/* Dark mode support (optional enhancement) */
@media (prefers-color-scheme: dark) {
  .crime-scene-board {
    background: rgba(0, 0, 0, 0.3);
  }

  .location-card,
  .clue-card,
  .accusation-item,
  .hand-summary {
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
    border-color: rgba(255, 255, 255, 0.2);
  }

  .board-title,
  .locations-section h4,
  .clues-section h4,
  .accusations-section h4,
  .hands-section h4 {
    color: #fff;
  }
}
</style>
