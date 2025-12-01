<template>
  <div class="werewolf-game-view" :class="{ 'is-night': isNightPhase }">
    <!-- 顶部状态栏 -->
    <div class="top-bar">
      <div class="room-info">
        <span class="room-code">房间: {{ roomCode }}</span>
        <el-tag v-if="isSpectator" type="info">观战中</el-tag>
        <el-tag v-if="mode" :type="mode === 'player' ? 'success' : 'warning'" size="small">
          {{ mode === 'player' ? '玩家模式' : '观战模式' }}
        </el-tag>
      </div>
      <div class="game-controls">
        <!-- 日志级别切换 -->
        <LogLevelSwitch :show-label="true" />
        
        <!-- 游戏控制栏（房主可见） -->
        <GameControlBar
          v-if="isHost"
          :is-started="gameStore.isStarted"
          :is-paused="gameStore.isPaused"
          :show-start="!gameStore.isStarted"
          :show-pause="gameStore.isStarted && !gameStore.isPaused"
          :show-resume="gameStore.isStarted && gameStore.isPaused"
          @start="handleStartGame"
          @pause="handlePauseGame"
          @resume="handleResumeGame"
        />
        
        <el-button size="small" text @click="handleShowSettings">
          <el-icon><Setting /></el-icon>
        </el-button>
      </div>
    </div>
    
    <!-- 主持人发言悬浮层（保留原有组件） -->
    <div class="host-announcement-overlay" v-if="showHostAnnouncement">
      <HostAnnouncement
        :content="hostAnnouncementContent"
        :is-streaming="isHostStreaming"
        :announcement-type="hostAnnouncementType"
        :visible="showHostAnnouncement"
        :closable="!isHostStreaming"
        @close="handleCloseAnnouncement"
      />
    </div>
    
    <!-- 新增：持久主持人发言面板 -->
    <div class="host-panel-container">
      <HostAnnouncementPanel
        :current-announcement="gameStore.hostAnnouncement?.content || ''"
        :is-streaming="gameStore.hostAnnouncement?.isStreaming || false"
        :announcement-history="gameStore.announcementHistory"
        :visible="!!gameStore.hostAnnouncement?.content || gameStore.announcementHistory.length > 0"
      />
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
            @empty-kill="handleEmptyKill"
            @self-save="handleSelfSave"
          />
          <VotePanel
            v-else-if="currentPhase === 'vote' && canVote"
            :candidates="voteablePlayers"
            :my-vote="myVote"
            :has-voted="hasVoted"
            :countdown="voteCountdown"
            :disabled="voteDisabled"
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
        
        <!-- 新增：玩家发言气泡 -->
        <SpeechBubble
          v-for="bubble in gameStore.activeSpeechBubbles"
          :key="bubble.seatNumber"
          :seat-number="bubble.seatNumber"
          :player-name="bubble.playerName"
          :content="bubble.content"
          :is-streaming="bubble.isStreaming"
          :is-human="bubble.isHuman"
          :visible="bubble.visible"
          :position="calculateBubblePosition(bubble.seatNumber)"
        />
      </div>
      
      <!-- 右侧日志面板 -->
      <div class="right-panel">
        <GameLog :logs="gameLogs" />
        
        <!-- 新增：玩家发言输入面板 -->
        <PlayerInputPanel
          v-if="!isSpectator"
          :visible="showPlayerInput"
          :is-my-turn="isMyTurnToSpeak"
          :is-submitting="isSubmittingSpeech"
          :allow-skip="false"
          :max-length="500"
          @submit="handleSubmitSpeech"
          @skip="handleSkipSpeech"
        />
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
import { VideoPause, VideoPlay, Loading, Setting } from '@element-plus/icons-vue'
import { useGameStore } from '@/stores/game'
import { useSocketStore } from '@/stores/socket'
import { roomsApi, gamesApi } from '@/services/api'
import GamePhaseIndicator from '@/components/werewolf/GamePhaseIndicator.vue'
import SeatCircle from '@/components/werewolf/SeatCircle.vue'
import GameLog from '@/components/werewolf/GameLog.vue'
import NightActionPanel from '@/components/werewolf/NightActionPanel.vue'
import VotePanel from '@/components/werewolf/VotePanel.vue'
import HostAnnouncement from '@/components/werewolf/HostAnnouncement.vue'
// 新增组件
import GameControlBar from '@/components/werewolf/GameControlBar.vue'
import HostAnnouncementPanel from '@/components/werewolf/HostAnnouncementPanel.vue'
import SpeechBubble from '@/components/werewolf/SpeechBubble.vue'
import PlayerInputPanel from '@/components/werewolf/PlayerInputPanel.vue'
import LogLevelSwitch from '@/components/werewolf/LogLevelSwitch.vue'

const route = useRoute()
const router = useRouter()
const gameStore = useGameStore()
const socketStore = useSocketStore()

// 状态
const loading = ref(true)
const selectedPlayerId = ref(null)
const showResultDialog = ref(false)

// 主持人发言状态
const showHostAnnouncement = ref(false)
const hostAnnouncementContent = ref('')
const hostAnnouncementType = ref('')
const isHostStreaming = ref(false)

// 投票状态
const voteCountdown = ref(0)
const voteDisabled = ref(false)
let voteCountdownTimer = null

// 新增：发言状态
const isSubmittingSpeech = ref(false)
const showPlayerInput = ref(true)

// 游戏模式
const mode = computed(() => route.query.mode || 'player')

// 计算属性 - 来自 store
const roomCode = computed(() => route.params.code)
const myPlayerId = computed(() => gameStore.myPlayerId)
const myRole = computed(() => gameStore.myRole)
const isSpectator = computed(() => gameStore.isSpectator || mode.value === 'spectator')
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

// 是否显示角色（单人模式始终显示，因为用户是观战者）
const showRoles = computed(() => true)

// 新增：是否轮到当前玩家发言
const isMyTurnToSpeak = computed(() => {
  // activeSpeechBubbles 是对象格式: { [seatNumber]: { content, isStreaming, ... } }
  // 检查当前发言者是否是自己（真人玩家）
  return gameStore.currentSpeaker?.isHuman && 
         gameStore.currentSpeaker?.seatNumber === gameStore.user_seat_number &&
         gameStore.waitingForInput
})

// 获取阵营名称
function getTeamName(team) {
  switch (team) {
    case 'werewolf': return '狼人阵营'
    case 'villager': return '村民阵营'
    case 'god': return '神职阵营'
    default: return ''
  }
}

// 新增：计算发言气泡位置（基于座位号）
function calculateBubblePosition(seatNumber) {
  // 10人局：座位1-10均匀分布在圆环上
  const totalSeats = 10
  const anglePerSeat = 360 / totalSeats
  // 座位1在顶部，顺时针排列
  const angle = (seatNumber - 1) * anglePerSeat - 90 // -90度使座位1在顶部
  const radians = (angle * Math.PI) / 180
  
  // 气泡偏移量（相对于圆心）
  const radius = 200 // 根据实际圆环大小调整
  const bubbleOffset = 120 // 气泡距离座位的偏移
  
  const x = Math.cos(radians) * (radius + bubbleOffset)
  const y = Math.sin(radians) * (radius + bubbleOffset)
  
  // 返回CSS位置
  return {
    top: `calc(50% + ${y}px)`,
    left: `calc(50% + ${x}px)`,
    transform: 'translate(-50%, -50%)'
  }
}

// 标准10人局角色配置
const ROLE_CONFIG = [
  { role_name: '狼人', role_type: 'werewolf' },
  { role_name: '狼人', role_type: 'werewolf' },
  { role_name: '狼人', role_type: 'werewolf' },
  { role_name: '预言家', role_type: 'god' },
  { role_name: '女巫', role_type: 'god' },
  { role_name: '猎人', role_type: 'god' },
  { role_name: '村民', role_type: 'villager' },
  { role_name: '村民', role_type: 'villager' },
  { role_name: '村民', role_type: 'villager' },
  { role_name: '村民', role_type: 'villager' },
]

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
    
    // 设置观战模式
    if (mode.value === 'spectator') {
      gameStore.setIsSpectator(true)
    }
    
    // 单人模式：为所有玩家分配角色（洗牌后分配）
    const shuffledRoles = [...ROLE_CONFIG].sort(() => Math.random() - 0.5)
    const participants = room.participants || []
    
    // 初始化玩家状态（包含角色信息）
    const playerStates = {}
    participants.forEach((p, index) => {
      const playerId = p.id || p.player_id
      const role = shuffledRoles[index] || { role_name: '村民', role_type: 'villager' }
      playerStates[playerId] = {
        is_alive: true,
        role_name: role.role_name,
        role_type: role.role_type,
        role_revealed: true, // 单人观战模式下显示所有角色
        vote_count: 0
      }
    })
    
    // 更新 store 中的玩家状态
    gameStore.setPlayerStates(playerStates)
    
    // 设置游戏阶段
    gameStore.setCurrentPhase('night')
    gameStore.setTurnNumber(1)
    
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
  // 使用新的统一事件处理器
  socketStore.setupHostHandlers(gameStore)
  socketStore.setupWerewolfHandlers(gameStore)
  
  // 本地主持人发言监听（用于UI展示）
  socketStore.on('host:announcement_start', handleHostAnnouncementStart)
  socketStore.on('host:announcement_chunk', handleHostAnnouncementChunk)
  socketStore.on('host:announcement_end', handleHostAnnouncementEnd)
  
  // 投票倒计时
  socketStore.on('werewolf:vote_countdown', handleVoteCountdown)
  
  // 旧的事件监听（兼容）
  socketStore.on('game_state_update', handleGameStateUpdate)
  socketStore.on('game_ended', handleGameEnded)
  socketStore.on('game_log', handleGameLog)
}

// 主持人发言开始
function handleHostAnnouncementStart(data) {
  showHostAnnouncement.value = true
  hostAnnouncementContent.value = ''
  hostAnnouncementType.value = data.announcement_type || ''
  isHostStreaming.value = true
}

// 主持人发言片段
function handleHostAnnouncementChunk(data) {
  hostAnnouncementContent.value = data.accumulated || ''
}

// 主持人发言结束
function handleHostAnnouncementEnd(data) {
  hostAnnouncementContent.value = data.full_content || ''
  isHostStreaming.value = false
  
  // 3秒后自动关闭（如果不是重要公告）
  if (!['game_end', 'vote_result'].includes(hostAnnouncementType.value)) {
    setTimeout(() => {
      if (!isHostStreaming.value) {
        showHostAnnouncement.value = false
      }
    }, 3000)
  }
}

// 关闭主持人发言
function handleCloseAnnouncement() {
  showHostAnnouncement.value = false
}

// 投票倒计时
function handleVoteCountdown(data) {
  voteCountdown.value = data.remaining
  voteDisabled.value = data.remaining <= 0
  
  // 清除旧的计时器
  if (voteCountdownTimer) {
    clearInterval(voteCountdownTimer)
  }
  
  // 本地倒计时
  if (data.remaining > 0) {
    voteCountdownTimer = setInterval(() => {
      voteCountdown.value--
      if (voteCountdown.value <= 0) {
        clearInterval(voteCountdownTimer)
        voteDisabled.value = true
      }
    }, 1000)
  }
}

function handleGameStateUpdate(data) {
  gameStore.updateGameState(data)
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
  socketStore.emit('werewolf:use_skill', {
    room_code: roomCode.value,
    target_id: target.id
  })
  gameStore.useSkill()
  selectedPlayerId.value = null
}

// 狼人空刀
function handleEmptyKill() {
  socketStore.emit('werewolf:use_skill', {
    room_code: roomCode.value,
    target_id: null,
    action_type: 'empty_kill'
  })
  gameStore.useSkill()
  ElMessage.info('已选择不击杀任何人')
}

// 女巫自救
function handleSelfSave() {
  socketStore.emit('werewolf:use_skill', {
    room_code: roomCode.value,
    target_id: myPlayerId.value,
    action_type: 'self_save'
  })
  gameStore.useSkill()
  ElMessage.info('已使用解药自救')
}

function handleVote(player) {
  socketStore.emit('werewolf:vote', {
    room_code: roomCode.value,
    target_id: player.id
  })
  gameStore.setVote(player.id)
}

function handleAbstain() {
  socketStore.emit('werewolf:vote', {
    room_code: roomCode.value,
    target_id: null // 弃票
  })
  gameStore.setVote(null)
}

// 新增：开始游戏
async function handleStartGame() {
  try {
    socketStore.startGame(roomCode.value)
    ElMessage.success('游戏开始')
  } catch (err) {
    ElMessage.error('开始失败')
  }
}

async function handlePauseGame() {
  try {
    socketStore.pauseGame(roomCode.value)
    ElMessage.success('游戏已暂停')
  } catch (err) {
    ElMessage.error('暂停失败')
  }
}

async function handleResumeGame() {
  try {
    socketStore.resumeGame(roomCode.value)
    ElMessage.success('游戏已恢复')
  } catch (err) {
    ElMessage.error('恢复失败')
  }
}

function handleShowSettings() {
  // TODO: 显示设置面板
  ElMessage.info('设置功能开发中')
}

// 新增：提交发言
async function handleSubmitSpeech(content) {
  if (!content || isSubmittingSpeech.value) return
  
  isSubmittingSpeech.value = true
  try {
    socketStore.submitSpeech(roomCode.value, content)
    ElMessage.success('发言已提交')
  } catch (err) {
    ElMessage.error('发言提交失败')
  } finally {
    isSubmittingSpeech.value = false
  }
}

// 新增：跳过发言
function handleSkipSpeech() {
  socketStore.submitSpeech(roomCode.value, '')
  ElMessage.info('已跳过发言')
}

function handleBackToLobby() {
  router.push('/lobby')
}

// ============ F37-F40: 断线重连恢复功能 ============

/**
 * F37: 重连后请求历史日志
 */
async function fetchHistoryLogs() {
  try {
    const response = await gamesApi.getGameLogs(roomCode.value, gameStore.logLevel)
    return response.logs || []
  } catch (err) {
    console.error('获取历史日志失败:', err)
    return []
  }
}

/**
 * F38: 历史日志回放到 store
 */
function replayHistoryLogs(logs) {
  if (!logs || logs.length === 0) return
  
  // 清空当前日志
  gameStore.clearGameLogs()
  
  // 按时间顺序添加历史日志
  logs.forEach(log => {
    gameStore.addGameLog({
      id: log.id,
      type: log.type,
      content: log.content,
      player_id: log.player_id,
      player_name: log.player_name,
      seat_number: log.seat_number,
      day: log.day,
      phase: log.phase,
      time: log.time,
      metadata: log.metadata,
      is_public: log.is_public
    })
  })
}

/**
 * F39: 从历史日志中恢复主持人公告
 */
function restoreHostAnnouncements(logs) {
  if (!logs || logs.length === 0) return
  
  // 清空当前公告历史
  gameStore.clearAnnouncementHistory()
  
  // 筛选主持人公告并恢复
  const hostAnnouncements = logs.filter(log => log.type === 'host_announcement')
  
  hostAnnouncements.forEach(announcement => {
    gameStore.addToAnnouncementHistory({
      type: announcement.metadata?.announcement_type || 'general',
      content: announcement.content,
      time: announcement.time
    })
  })
  
  // 设置最新公告为当前公告（如果有）
  if (hostAnnouncements.length > 0) {
    const latest = hostAnnouncements[hostAnnouncements.length - 1]
    gameStore.setHostAnnouncement({
      type: latest.metadata?.announcement_type || 'general',
      content: latest.content,
      isStreaming: false
    })
  }
}

/**
 * F40: 恢复当前游戏状态
 */
async function restoreCurrentState() {
  try {
    const state = await gamesApi.getCurrentState(roomCode.value)
    
    // 恢复游戏控制状态
    if (state.is_started !== undefined) {
      gameStore.setGameStarted(state.is_started)
    }
    if (state.is_paused !== undefined) {
      gameStore.setGamePaused(state.is_paused)
    }
    
    // 恢复游戏阶段
    if (state.current_phase) {
      gameStore.setCurrentPhase(state.current_phase)
    }
    if (state.day_number !== undefined) {
      gameStore.setTurnNumber(state.day_number)
    }
    
    // 恢复当前发言者
    if (state.current_speaker_seat) {
      gameStore.setCurrentSpeaker(
        state.current_speaker_seat,
        state.current_speaker_name,
        state.waiting_for_human_input
      )
    }
    
    // 恢复玩家状态
    if (state.players) {
      const playerStates = {}
      state.players.forEach(p => {
        playerStates[p.id] = {
          is_alive: p.is_alive,
          role_name: p.role_name,
          role_type: p.role_type,
          role_revealed: p.role_revealed,
          vote_count: p.vote_count || 0
        }
      })
      gameStore.setPlayerStates(playerStates)
    }
    
    return true
  } catch (err) {
    console.error('恢复游戏状态失败:', err)
    return false
  }
}

/**
 * 处理重连事件
 */
async function handleReconnect() {
  console.log('检测到重连，正在恢复游戏状态...')
  
  loading.value = true
  try {
    // F40: 先恢复当前状态
    await restoreCurrentState()
    
    // F37: 获取历史日志
    const logs = await fetchHistoryLogs()
    
    // F38: 回放历史日志
    replayHistoryLogs(logs)
    
    // F39: 恢复主持人公告
    restoreHostAnnouncements(logs)
    
    ElMessage.success('游戏状态已恢复')
  } catch (err) {
    console.error('重连恢复失败:', err)
    ElMessage.warning('部分游戏状态恢复失败，请刷新页面')
  } finally {
    loading.value = false
  }
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
  
  // F37-F40: 监听重连事件
  socketStore.on('reconnect', handleReconnect)
})

onUnmounted(() => {
  // 清理事件监听
  socketStore.off('host:announcement_start', handleHostAnnouncementStart)
  socketStore.off('host:announcement_chunk', handleHostAnnouncementChunk)
  socketStore.off('host:announcement_end', handleHostAnnouncementEnd)
  socketStore.off('werewolf:vote_countdown', handleVoteCountdown)
  socketStore.off('game_state_update', handleGameStateUpdate)
  socketStore.off('game_ended', handleGameEnded)
  socketStore.off('game_log', handleGameLog)
  socketStore.off('reconnect', handleReconnect)
  
  // 清理倒计时
  if (voteCountdownTimer) {
    clearInterval(voteCountdownTimer)
  }
})
</script>

<style scoped>
.werewolf-game-view {
  min-height: 100vh;
  background: var(--color-bg-primary);
  display: flex;
  flex-direction: column;
  transition: background .5s ease;
  position: relative;
}

/* 科幻背景效果 */
.werewolf-game-view:before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    linear-gradient(rgba(0, 240, 255, .02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 240, 255, .02) 1px, transparent 1px);
  background-size: 60px 60px;
  pointer-events: none;
  z-index: 0;
}

.werewolf-game-view.is-night {
  background: linear-gradient(135deg, #0a0a15 0%, #10102a 50%, #0a1525 100%);
}

.werewolf-game-view.is-night:before {
  background-image: 
    linear-gradient(rgba(168, 85, 247, .02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(168, 85, 247, .02) 1px, transparent 1px);
}

/* 顶部状态栏 */
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 24px;
  background: rgba(10, 10, 20, .8);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(0, 240, 255, .2);
  position: relative;
  z-index: 100;
}

.top-bar:after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-primary), transparent);
  opacity: .5;
}

.room-info {
  display: flex;
  align-items: center;
  gap: 14px;
}

.room-code {
  color: var(--color-primary);
  font-size: 13px;
  font-family: 'Courier New', monospace;
  padding: 6px 14px;
  background: rgba(0, 240, 255, .1);
  border: 1px solid rgba(0, 240, 255, .3);
  border-radius: 6px;
  text-shadow: 0 0 10px var(--color-primary);
}

.game-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.game-controls .el-button {
  color: var(--color-text-secondary);
  border: 1px solid rgba(0, 240, 255, .3);
  background: rgba(0, 240, 255, .05);
  border-radius: 6px;
}

.game-controls .el-button:hover {
  color: var(--color-primary);
  border-color: var(--color-primary);
  background: rgba(0, 240, 255, .1);
}

/* 主持人发言悬浮层 */
.host-announcement-overlay {
  position: fixed;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  max-width: 600px;
  width: 90%;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

/* 新增：持久主持人面板容器 */
.host-panel-container {
  position: fixed;
  top: 80px;
  right: 20px;
  z-index: 900;
  max-width: 360px;
  width: 100%;
}

.game-main {
  flex: 1;
  display: grid;
  grid-template-columns: 280px 1fr 320px;
  gap: 20px;
  padding: 20px;
  overflow: hidden;
  position: relative;
  z-index: 1;
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.my-role-card {
  background: rgba(10, 10, 20, .9);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  border: 1px solid rgba(0, 240, 255, .2);
  padding: 18px;
  position: relative;
  overflow: hidden;
}

.my-role-card:before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--color-primary), var(--color-accent), var(--color-primary));
}

.card-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 2px;
  margin: 0 0 14px;
}

.role-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  border-radius: 12px;
  margin-bottom: 14px;
  border: 1px solid rgba(0, 240, 255, .3);
  position: relative;
  overflow: hidden;
}

.role-info:before {
  content: '';
  position: absolute;
  top: 0;
  left: -50%;
  width: 50%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, .05), transparent);
  animation: shine 3s infinite;
}

@keyframes shine {
  0% { left: -50%; }
  100% { left: 150%; }
}

.role-info.team-werewolf {
  background: linear-gradient(135deg, rgba(255, 51, 102, .15), rgba(255, 0, 85, .15));
  border-color: rgba(255, 51, 102, .4);
}

.role-info.team-villager {
  background: linear-gradient(135deg, rgba(0, 255, 136, .15), rgba(0, 200, 100, .15));
  border-color: rgba(0, 255, 136, .4);
}

.role-info.team-god {
  background: linear-gradient(135deg, rgba(0, 170, 255, .15), rgba(0, 128, 255, .15));
  border-color: rgba(0, 170, 255, .4);
}

.role-name {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  text-shadow: 0 0 15px currentColor;
}

.team-werewolf .role-name { color: #ff3366; }
.team-villager .role-name { color: #00ff88; }
.team-god .role-name { color: #00aaff; }

.role-team {
  font-size: 11px;
  opacity: .8;
  margin-top: 6px;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--color-text-secondary);
}

.role-desc {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.7;
  text-align: center;
}

.action-panel {
  background: rgba(10, 10, 20, .9);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  border: 1px solid rgba(0, 240, 255, .2);
  padding: 18px;
}

.center-area {
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 240, 255, .03);
  border-radius: 20px;
  border: 1px solid rgba(0, 240, 255, .1);
  position: relative;
}

.center-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 110px;
  height: 110px;
  background: linear-gradient(135deg, rgba(0, 240, 255, .1), rgba(168, 85, 247, .1));
  border-radius: 50%;
  border: 2px solid rgba(0, 240, 255, .4);
  color: var(--color-primary);
  box-shadow: 
    0 0 30px rgba(0, 240, 255, .2),
    inset 0 0 30px rgba(0, 240, 255, .1);
}

.ai-thinking {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--color-primary);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.ai-thinking .is-loading {
  font-size: 24px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.game-result {
  text-align: center;
}

.result-text {
  font-size: 14px;
  font-weight: 600;
  text-shadow: 0 0 10px currentColor;
}

.alive-info {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.alive-count {
  font-size: 36px;
  font-weight: 700;
  line-height: 1;
  font-family: 'Courier New', monospace;
  text-shadow: 0 0 20px var(--color-primary);
}

.alive-label {
  font-size: 11px;
  margin-top: 6px;
  opacity: .7;
  text-transform: uppercase;
  letter-spacing: 2px;
}

.right-panel {
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 140px);
}

/* 游戏结果弹窗 */
.result-content {
  text-align: center;
  padding: 24px 0;
  background: rgba(10, 10, 20, .9);
  border-radius: 12px;
}

.winner-team {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 20px;
  text-shadow: 0 0 20px currentColor;
}

.winner-team.team-werewolf {
  color: #ff3366;
}

.winner-team.team-villager {
  color: #00ff88;
}

.winner-players {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
}

.winner-player {
  padding: 6px 14px;
  background: rgba(0, 240, 255, .1);
  border: 1px solid rgba(0, 240, 255, .3);
  border-radius: 20px;
  font-size: 13px;
  color: var(--color-text-primary);
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
  
  .top-bar {
    padding: 10px 16px;
  }
  
  .room-code {
    font-size: 11px;
    padding: 4px 10px;
  }
}
</style>
