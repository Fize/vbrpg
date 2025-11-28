<template>
  <div class="werewolf-game-view" :class="{ 'is-night': isNightPhase }">
    <!-- 顶部状态栏 -->
    <div class="top-bar">
      <div class="room-info">
        <span class="room-code">房间: {{ roomCode }}</span>
        <el-tag v-if="isSpectator" type="info">观战中</el-tag>
      </div>
      <div class="game-controls" v-if="isHost">
        <el-button size="small" text @click="handlePauseGame" v-if="!isPaused">
          <el-icon><VideoPause /></el-icon>
        </el-button>
        <el-button size="small" text @click="handleResumeGame" v-else>
          <el-icon><VideoPlay /></el-icon>
        </el-button>
      </div>
    </div>
    
    <!-- 主游戏区域 -->
    <div class="game-main" v-loading="loading">
      <!-- 左侧面板 -->
      <div class="left-panel">
        <!-- 游戏阶段指示器 -->
        <GamePhaseIndicator
          :day-number="dayNumber"
          :phase="currentPhase"
          :sub-phase="subPhase"
          :countdown="countdown"
        />
        
        <!-- 我的角色卡 -->
        <div v-if="myRole && !isSpectator" class="my-role-card">
          <h4 class="card-title">我的角色</h4>
          <div class="role-info" :class="`team-${myRole.team}`">
            <span class="role-name">{{ myRole.name }}</span>
            <span class="role-team">{{ getTeamName(myRole.team) }}</span>
          </div>
          <p class="role-desc">{{ myRole.description }}</p>
        </div>
        
        <!-- 行动面板 -->
        <div class="action-panel" v-if="showActionPanel">
          <NightActionPanel
            v-if="isNightPhase && canUseSkill"
            :role="myRole"
            :targets="availableTargets"
            :disabled="skillUsed"
            @use-skill="handleUseSkill"
          />
          <VotePanel
            v-else-if="currentPhase === 'vote' && canVote"
            :candidates="voteablePlayers"
            :my-vote="myVote"
            :has-voted="hasVoted"
            @vote="handleVote"
            @abstain="handleAbstain"
          />
        </div>
      </div>
      
      <!-- 中央座位圆环 -->
      <div class="center-area">
        <SeatCircle
          :players="playersWithState"
          :current-player-id="myPlayerId"
          :selected-player-id="selectedPlayerId"
          :speaking-player-id="speakingPlayerId"
          :selectable="canSelectPlayer"
          :show-roles="showRoles"
          :votes="voteResults"
          @select="handleSelectPlayer"
        >
          <template #center>
            <div class="center-status">
              <div v-if="isAiThinking" class="ai-thinking">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>AI 思考中...</span>
              </div>
              <div v-else-if="gameEnded" class="game-result">
                <span class="result-text">{{ winnerText }}</span>
              </div>
              <div v-else class="alive-info">
                <span class="alive-count">{{ aliveCount }}</span>
                <span class="alive-label">存活</span>
              </div>
            </div>
          </template>
        </SeatCircle>
      </div>
      
      <!-- 右侧日志面板 -->
      <div class="right-panel">
        <GameLog :logs="gameLogs" />
      </div>
    </div>
    
    <!-- 游戏结束弹窗 -->
    <el-dialog
      v-model="showResultDialog"
      :title="winnerText"
      width="400px"
      :close-on-click-modal="false"
    >
      <div class="result-content">
        <div class="winner-team" :class="`team-${winner}`">
          {{ winnerText }}
        </div>
        <div class="winner-players">
          <span v-for="player in winnerTeam" :key="player.id" class="winner-player">
            {{ player.name }}
          </span>
        </div>
      </div>
      <template #footer>
        <el-button @click="handleBackToLobby">返回大厅</el-button>
        <el-button type="primary" @click="showResultDialog = false">查看复盘</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { VideoPause, VideoPlay, Loading } from '@element-plus/icons-vue'
import { useGameStore } from '@/stores/game'
import { useSocketStore } from '@/stores/socket'
import { roomsApi } from '@/services/api'
import GamePhaseIndicator from '@/components/werewolf/GamePhaseIndicator.vue'
import SeatCircle from '@/components/werewolf/SeatCircle.vue'
import GameLog from '@/components/werewolf/GameLog.vue'
import NightActionPanel from '@/components/werewolf/NightActionPanel.vue'
import VotePanel from '@/components/werewolf/VotePanel.vue'

const route = useRoute()
const router = useRouter()
const gameStore = useGameStore()
const socketStore = useSocketStore()

// 状态
const loading = ref(true)
const isPaused = ref(false)
const selectedPlayerId = ref(null)
const showResultDialog = ref(false)

// 计算属性 - 来自 store
const roomCode = computed(() => route.params.code)
const myPlayerId = computed(() => gameStore.myPlayerId)
const myRole = computed(() => gameStore.myRole)
const isSpectator = computed(() => gameStore.isSpectator)
const isHost = computed(() => gameStore.isHost)
const currentPhase = computed(() => gameStore.currentPhase || 'night')
const subPhase = computed(() => gameStore.subPhase)
const dayNumber = computed(() => gameStore.dayNumber)
const countdown = computed(() => gameStore.countdown)
const gameLogs = computed(() => gameStore.gameLogs)
const isAiThinking = computed(() => gameStore.isAiThinking)
const gameEnded = computed(() => gameStore.gameEnded)
const winner = computed(() => gameStore.winner)
const winnerTeam = computed(() => gameStore.winnerTeam)
const voteResults = computed(() => gameStore.voteResults)
const myVote = computed(() => gameStore.myVote)
const hasVoted = computed(() => gameStore.hasVoted)
const speakingPlayerId = computed(() => gameStore.speakingPlayerId)
const canUseSkill = computed(() => gameStore.canUseSkill)
const canVote = computed(() => gameStore.canVote)
const skillUsed = computed(() => gameStore.mySkillUsed)

// 是否夜晚阶段
const isNightPhase = computed(() => currentPhase.value === 'night')

// 存活人数
const aliveCount = computed(() => gameStore.alivePlayers.length)

// 胜利文本
const winnerText = computed(() => {
  if (!gameEnded.value) return ''
  switch (winner.value) {
    case 'werewolf': return '狼人阵营获胜！'
    case 'villager': return '好人阵营获胜！'
    default: return '游戏结束'
  }
})

// 带状态的玩家列表
const playersWithState = computed(() => {
  return gameStore.players.map(player => ({
    ...player,
    ...gameStore.playerStates[player.id],
    is_online: true // TODO: 从 socket 获取
  }))
})

// 可投票玩家
const voteablePlayers = computed(() => {
  return gameStore.alivePlayers.filter(p => p.id !== myPlayerId.value)
})

// 可用技能目标
const availableTargets = computed(() => {
  return gameStore.mySkillTargets.length > 0 
    ? gameStore.mySkillTargets 
    : gameStore.alivePlayers
})

// 是否显示行动面板
const showActionPanel = computed(() => {
  if (isSpectator.value) return false
  if (gameEnded.value) return false
  return (isNightPhase.value && canUseSkill.value) || 
         (currentPhase.value === 'vote' && canVote.value)
})

// 是否可以选择玩家
const canSelectPlayer = computed(() => {
  if (isSpectator.value) return false
  if (gameEnded.value) return false
  return (isNightPhase.value && canUseSkill.value) || 
         (currentPhase.value === 'vote' && canVote.value)
})

// 是否显示角色（游戏结束后显示）
const showRoles = computed(() => gameEnded.value)

// 获取阵营名称
function getTeamName(team) {
  switch (team) {
    case 'werewolf': return '狼人阵营'
    case 'villager': return '村民阵营'
    case 'god': return '神职阵营'
    default: return ''
  }
}

// 加载游戏状态
async function loadGameState() {
  loading.value = true
  try {
    const room = await roomsApi.getRoom(roomCode.value)
    gameStore.setCurrentRoom(room)
    
    // 检查游戏状态
    if (room.status !== 'In Progress') {
      ElMessage.warning('游戏尚未开始或已结束')
      router.push(`/room/${roomCode.value}`)
      return
    }
    
    // TODO: 从后端获取当前玩家的角色信息
    // const playerInfo = await roomsApi.getMyInfo(roomCode.value)
    // gameStore.setMyRole(playerInfo.role)
    // gameStore.setIsSpectator(playerInfo.is_spectator)
    
  } catch (err) {
    console.error('加载游戏状态失败:', err)
    ElMessage.error('加载游戏失败')
    router.push('/lobby')
  } finally {
    loading.value = false
  }
}

// WebSocket 事件处理
function setupSocketListeners() {
  socketStore.on('game_state_update', handleGameStateUpdate)
  socketStore.on('turn_changed', handleTurnChanged)
  socketStore.on('phase_changed', handlePhaseChanged)
  socketStore.on('player_died', handlePlayerDied)
  socketStore.on('vote_update', handleVoteUpdate)
  socketStore.on('ai_thinking', handleAiThinking)
  socketStore.on('ai_action', handleAiAction)
  socketStore.on('game_ended', handleGameEnded)
  socketStore.on('game_log', handleGameLog)
}

function handleGameStateUpdate(data) {
  gameStore.updateGameState(data)
}

function handleTurnChanged(data) {
  gameStore.setCurrentTurn(data.player_id, data.turn_number)
}

function handlePhaseChanged(data) {
  gameStore.setPhase(data.phase, data.sub_phase)
  if (data.day_number) {
    gameStore.dayNumber = data.day_number
  }
  
  // 添加日志
  gameStore.addGameLog({
    type: 'system',
    is_system: true,
    message: `进入${getPhaseText(data.phase)}`
  })
}

function getPhaseText(phase) {
  switch (phase) {
    case 'night': return '夜晚'
    case 'day': return '白天'
    case 'discussion': return '讨论阶段'
    case 'vote': return '投票阶段'
    default: return phase
  }
}

function handlePlayerDied(data) {
  gameStore.setPlayerDead(data.player_id, data.role_name)
  gameStore.addGameLog({
    type: 'death',
    player_name: data.player_name,
    message: `${data.player_name} 死亡，身份是 ${data.role_name}`
  })
}

function handleVoteUpdate(data) {
  gameStore.updateVoteResults(data.results)
}

function handleAiThinking(data) {
  gameStore.setAiThinking(true, data.player_id)
}

function handleAiAction(data) {
  gameStore.setAiThinking(false)
  if (data.action_log) {
    gameStore.addGameLog(data.action_log)
  }
}

function handleGameEnded(data) {
  gameStore.setGameEnded(true, data.winner, data.winner_players)
  showResultDialog.value = true
}

function handleGameLog(data) {
  gameStore.addGameLog(data)
}

// 用户操作
function handleSelectPlayer(player) {
  selectedPlayerId.value = player.id
}

function handleUseSkill(target) {
  // TODO: 发送技能使用请求
  socketStore.emit('use_skill', {
    room_code: roomCode.value,
    target_id: target.id
  })
  gameStore.useSkill()
  selectedPlayerId.value = null
}

function handleVote(player) {
  socketStore.emit('vote', {
    room_code: roomCode.value,
    target_id: player.id
  })
  gameStore.setVote(player.id)
}

function handleAbstain() {
  socketStore.emit('vote', {
    room_code: roomCode.value,
    target_id: null // 弃票
  })
  gameStore.setVote(null)
}

async function handlePauseGame() {
  try {
    await roomsApi.pauseGame(roomCode.value)
    isPaused.value = true
    ElMessage.success('游戏已暂停')
  } catch (err) {
    ElMessage.error('暂停失败')
  }
}

async function handleResumeGame() {
  try {
    await roomsApi.resumeGame(roomCode.value)
    isPaused.value = false
    ElMessage.success('游戏已恢复')
  } catch (err) {
    ElMessage.error('恢复失败')
  }
}

function handleBackToLobby() {
  router.push('/lobby')
}

// 监听游戏结束
watch(gameEnded, (ended) => {
  if (ended) {
    showResultDialog.value = true
  }
})

onMounted(() => {
  loadGameState()
  setupSocketListeners()
  
  if (!socketStore.isConnected) {
    socketStore.connect()
  }
})

onUnmounted(() => {
  socketStore.off('game_state_update', handleGameStateUpdate)
  socketStore.off('turn_changed', handleTurnChanged)
  socketStore.off('phase_changed', handlePhaseChanged)
  socketStore.off('player_died', handlePlayerDied)
  socketStore.off('vote_update', handleVoteUpdate)
  socketStore.off('ai_thinking', handleAiThinking)
  socketStore.off('ai_action', handleAiAction)
  socketStore.off('game_ended', handleGameEnded)
  socketStore.off('game_log', handleGameLog)
})
</script>

<style scoped>
.werewolf-game-view {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  flex-direction: column;
  transition: background 0.5s ease;
}

.werewolf-game-view.is-night {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: rgba(0, 0, 0, 0.2);
}

.room-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.room-code {
  color: white;
  font-size: 14px;
  font-family: monospace;
}

.game-controls .el-button {
  color: white;
}

.game-main {
  flex: 1;
  display: grid;
  grid-template-columns: 280px 1fr 300px;
  gap: 20px;
  padding: 20px;
  overflow: hidden;
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.my-role-card {
  background: white;
  border-radius: 12px;
  padding: 16px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 12px;
}

.role-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 12px;
}

.role-info.team-werewolf {
  background: linear-gradient(135deg, #f56c6c 0%, #c45656 100%);
  color: white;
}

.role-info.team-villager {
  background: linear-gradient(135deg, #67c23a 0%, #529b2e 100%);
  color: white;
}

.role-info.team-god {
  background: linear-gradient(135deg, #409eff 0%, #337ecc 100%);
  color: white;
}

.role-name {
  font-size: 20px;
  font-weight: 700;
}

.role-team {
  font-size: 12px;
  opacity: 0.9;
  margin-top: 4px;
}

.role-desc {
  font-size: 12px;
  color: #909399;
  margin: 0;
  line-height: 1.6;
}

.action-panel {
  background: white;
  border-radius: 12px;
  padding: 16px;
}

.center-area {
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 16px;
}

.center-status {
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

.ai-thinking {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.game-result {
  text-align: center;
}

.result-text {
  font-size: 14px;
  font-weight: 600;
}

.alive-info {
  display: flex;
  flex-direction: column;
  align-items: center;
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

.right-panel {
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 140px);
}

/* 游戏结果弹窗 */
.result-content {
  text-align: center;
  padding: 20px 0;
}

.winner-team {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 16px;
}

.winner-team.team-werewolf {
  color: #f56c6c;
}

.winner-team.team-villager {
  color: #67c23a;
}

.winner-players {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

.winner-player {
  padding: 4px 12px;
  background: #f5f7fa;
  border-radius: 12px;
  font-size: 14px;
}

/* 响应式 */
@media (max-width: 1200px) {
  .game-main {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr auto;
  }
  
  .left-panel {
    flex-direction: row;
    flex-wrap: wrap;
  }
  
  .right-panel {
    max-height: 300px;
  }
}

@media (max-width: 768px) {
  .game-main {
    padding: 12px;
    gap: 12px;
  }
}
</style>
