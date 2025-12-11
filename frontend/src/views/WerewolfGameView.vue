<template>
  <div class="werewolf-game-view" :class="{ 'is-night': isNightPhase }">
    <!-- 顶部状态栏 -->
    <div class="top-bar">
      <div class="room-info">
        <el-button 
          text
          @click="handleBackToHome"
          class="back-home-btn"
        >
          <el-icon><HomeFilled /></el-icon>
          <span>返回首页</span>
        </el-button>
        <span class="divider">|</span>
        <span class="room-code">房间: {{ roomCode }}</span>
        <el-tag v-if="gameStore.isSpectatorMode" type="danger" effect="dark">已阵亡 - 观战中</el-tag>
        <el-tag v-else-if="isSpectator" type="info">观战中</el-tag>
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
          :is-spectator="isSpectator"
          @start="handleStartGame"
          @pause="handlePauseGame"
          @resume="handleResumeGame"
        />
        
        <el-button size="small" text @click="handleShowSettings">
          <el-icon><Setting /></el-icon>
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
        
        <!-- T54: 观战模式提示卡 -->
        <div v-if="gameStore.isSpectatorMode" class="spectator-card">
          <h4 class="card-title">观战模式</h4>
          <div class="spectator-info">
            <el-icon class="spectator-icon"><View /></el-icon>
            <p class="spectator-text">你已被淘汰</p>
            <p class="spectator-desc">以观战者身份继续观看游戏</p>
          </div>
        </div>
        
        <!-- 行动面板 -->
        <div class="action-panel" v-if="showActionPanel">
          <NightActionPanel
            v-if="isNightPhase && canUseSkill"
            :role="myRole"
            :targets="availableTargets"
            :killed-player="gameStore.killedPlayerInfo"
            :antidote-used="!gameStore.witchPotions.hasAntidote"
            :poison-used="!gameStore.witchPotions.hasPoison"
            :disabled="skillUsed"
            @use-skill="handleUseSkill"
            @empty-kill="handleEmptyKill"
            @use-antidote="handleUseAntidote"
            @use-poison="handleUsePoison"
            @skip="handleSkipNightAction"
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
      
      <!-- 中央区域：主持人面板 + 座位圆环 -->
      <div class="center-area">
        <!-- 主持人发言面板（中上部） -->
        <div class="host-panel-center">
          <HostAnnouncementPanel
            :current-announcement="gameStore.hostAnnouncement || { type: null, content: '', isStreaming: false }"
            :announcement-history="gameStore.announcementHistory"
          />
        </div>
        <SeatCircle
          :players="playersWithState"
          :current-player-id="myPlayerId"
          :selected-player-id="selectedPlayerId"
          :speaking-player-id="speakingPlayerId"
          :selectable="canSelectPlayer"
          :show-roles="showRoles"
          :votes="voteResults"
          :speech-bubbles="activeSpeechBubbles"
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
        
        <!-- 新增：玩家发言输入面板 -->
        <PlayerInputPanel
          v-if="!isSpectator && !gameStore.isSpectatorMode"
          :visible="showPlayerInput"
          :is-my-turn="isMyTurnToSpeak"
          :is-submitting="isSubmittingSpeech"
          :allow-skip="true"
          :max-length="500"
          :show-countdown="speechTimeout > 0"
          :time-remaining="speechTimeout"
          :speech-options="speechOptions"
          @submit="handleSubmitSpeech"
          @skip="handleSkipSpeech"
        />
        
        <!-- T54: 遗言面板 -->
        <LastWordsPanel
          v-if="gameStore.isLastWordsPhase"
          :room-code="roomCode"
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
import { VideoPause, VideoPlay, Loading, Setting, HomeFilled, View } from '@element-plus/icons-vue'
import { useGameStore } from '@/stores/game'
import { useSocketStore } from '@/stores/socket'
import { roomsApi, gamesApi } from '@/services/api'
import GamePhaseIndicator from '@/components/werewolf/GamePhaseIndicator.vue'
import SeatCircle from '@/components/werewolf/SeatCircle.vue'
import GameLog from '@/components/werewolf/GameLog.vue'
import NightActionPanel from '@/components/werewolf/NightActionPanel.vue'
import VotePanel from '@/components/werewolf/VotePanel.vue'
// 新增组件
import GameControlBar from '@/components/werewolf/GameControlBar.vue'
import HostAnnouncementPanel from '@/components/werewolf/HostAnnouncementPanel.vue'
// SpeechBubble 已移除，使用日志面板显示发言
import PlayerInputPanel from '@/components/werewolf/PlayerInputPanel.vue'
import LastWordsPanel from '@/components/werewolf/LastWordsPanel.vue'
import LogLevelSwitch from '@/components/werewolf/LogLevelSwitch.vue'

const route = useRoute()
const router = useRouter()
const gameStore = useGameStore()
const socketStore = useSocketStore()

// 状态
const loading = ref(true)
const selectedPlayerId = ref(null)
const showResultDialog = ref(false)

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
// 单人模式下，用户始终有控制权限
const isHost = computed(() => gameStore.isHost)
const currentPhase = computed(() => gameStore.phaseCategory || 'night')
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
const activeSpeechBubbles = computed(() => gameStore.activeSpeechBubbles)
const canUseSkill = computed(() => gameStore.canUseSkill)
const canVote = computed(() => gameStore.canVote)
const skillUsed = computed(() => gameStore.mySkillUsed)

// 是否夜晚阶段
const isNightPhase = computed(() => currentPhase.value === 'night')

// 带状态的玩家列表
const playersWithState = computed(() => {
  const players = gameStore.players.map((player, index) => {
    const state = gameStore.playerStates[player.id] || {}
    const seatNumber = state.seat_number || player.seat_number || index + 1
    return {
      ...player,
      ...state,
      seat_number: seatNumber,
      display_name: state.display_name || player.name || player.username,
      is_online: true // TODO: 从 socket 获取
    }
  })
  return players.sort((a, b) => (a.seat_number || 0) - (b.seat_number || 0))
})

// 存活人数
const aliveCount = computed(() => playersWithState.value.filter(p => p.is_alive !== false).length)

// 胜利文本
const winnerText = computed(() => {
  if (!gameEnded.value) return ''
  switch (winner.value) {
    case 'werewolf': return '狼人阵营获胜！'
    case 'villager': return '好人阵营获胜！'
    default: return '游戏结束'
  }
})

// 可投票玩家
const voteablePlayers = computed(() => {
  return playersWithState.value.filter(p => p.is_alive !== false && p.id !== myPlayerId.value)
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

// 是否显示角色（只在游戏结束后揭晓身份）
const showRoles = computed(() => gameEnded.value)

// 新增：是否轮到当前玩家发言
const isMyTurnToSpeak = computed(() => {
  // activeSpeechBubbles 是对象格式: { [seatNumber]: { content, isStreaming, ... } }
  // 检查当前发言者是否是自己（真人玩家）
  return gameStore.currentSpeaker?.isHuman && 
         gameStore.currentSpeaker?.seatNumber === gameStore.user_seat_number &&
         gameStore.waitingForInput
})

// T20: 发言选项和超时
const speechOptions = computed(() => gameStore.speechOptions)
const speechTimeout = computed(() => gameStore.speechTimeout)

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
    // 检查是否是新游戏（从首页跳转来的）
    const isNewGame = route.query.newGame === 'true'
    
    // 如果是新游戏，清理上一局的历史数据
    if (isNewGame) {
      console.log('新游戏开始，清理历史数据')
      resetGameState()
      // 清除 URL 中的 newGame 参数，避免刷新后再次清理
      router.replace({ path: route.path, query: {} })
    } else {
      console.log('页面刷新或重连，尝试恢复游戏状态')
      // 恢复历史日志
      try {
        const logs = await fetchHistoryLogs()
        if (logs && logs.length > 0) {
          replayHistoryLogs(logs)
          restoreHostAnnouncements(logs)
          console.log('历史日志恢复成功，共', logs.length, '条')
        }
      } catch (err) {
        console.warn('恢复历史日志失败:', err)
      }
      
      // 恢复游戏状态
      try {
        const gameState = await gamesApi.getWerewolfState(roomCode.value, myPlayerId.value || 'player_1')
        if (gameState) {
          gameStore.setGameState(gameState)
          console.log('游戏状态恢复成功:', gameState)
        }
      } catch (err) {
        console.warn('恢复游戏状态失败:', err)
      }
    }
    
    const room = await roomsApi.getRoom(roomCode.value)
    const participantsWithSeats = (room.participants || []).map((participant, index) => {
      const seatNumber = participant.seat_number ?? index + 1
      return {
        ...participant,
        seat_number: seatNumber,
        name: participant.name || participant.player?.username || `玩家${seatNumber}`,
        is_alive: participant.is_alive ?? true
      }
    })
    const normalizedRoom = { ...room, participants: participantsWithSeats }
    gameStore.setCurrentRoom(normalizedRoom)
    
    // 检查游戏状态 - 允许 Waiting 和 In Progress 状态
    if (room.status === 'Completed' || room.status === 'Dissolved') {
      ElMessage.warning('游戏已结束')
      router.push(`/room/${roomCode.value}`)
      return
    }
    
    // 如果游戏尚未开始，设置初始状态但不跳转
    if (room.status === 'Waiting') {
      gameStore.setGameStarted(false)
      // 继续加载，允许用户在此页面开始游戏
    }
    
    // 设置观战模式
    if (mode.value === 'spectator') {
      gameStore.setIsSpectator(true)
    }
    
    // 初始化玩家状态（不分配角色，等待后端发送角色信息）
    const participants = participantsWithSeats
    const playerStates = {}
    participants.forEach((p) => {
      const playerId = p.id || p.player_id || `seat_${p.seat_number}`
      playerStates[playerId] = {
        seat_number: p.seat_number,
        display_name: p.name || p.player?.username || `玩家${p.seat_number}`,
        is_alive: true,
        role_name: null,  // 等待后端发送
        role_type: null,  // 等待后端发送
        role_revealed: true, // 单人观战模式下显示所有角色
        vote_count: 0
      }
    })
    
    // 更新 store 中的玩家状态
    gameStore.setPlayerStates(playerStates)
    
    // 设置游戏阶段
    gameStore.setCurrentPhase('night')
    gameStore.setTurnNumber(1)
    
    // 单人模式：自动开始游戏
    // 无论房间状态是 Waiting 还是 In Progress，都发送开始事件
    // 后端会处理服务器重启后的状态恢复
    setTimeout(() => {
      console.log('发送开始游戏事件...', room.status)
      socketStore.startGame(roomCode.value)
      gameStore.setGameStarted(true)
    }, 500)
    
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
  // 使用统一事件处理器（已包含主持人发言处理）
  socketStore.setupHostHandlers(gameStore)
  socketStore.setupWerewolfHandlers(gameStore)
  socketStore.setupGameControlHandlers(gameStore)  // 游戏控制事件（暂停/继续）
  
  // 角色选择确认事件
  socketStore.on('werewolf:role_selected', handleRoleSelected)
  
  // 投票倒计时
  socketStore.on('werewolf:vote_countdown', handleVoteCountdown)
  
  // T20: 人类玩家发言相关事件
  socketStore.on('werewolf:waiting_for_human', handleWaitingForHuman)
  socketStore.on('werewolf:speech_options', handleSpeechOptions)
  socketStore.on('werewolf:human_speech_complete', handleHumanSpeechComplete)
  socketStore.on('werewolf:speech_submitted', handleSpeechSubmitted)
  socketStore.on('werewolf:ai_takeover', handleAiTakeover)
  
  // T28: 人类玩家投票相关事件
  socketStore.on('werewolf:vote_options', handleVoteOptions)
  socketStore.on('werewolf:human_vote_complete', handleHumanVoteComplete)
  
  // T37: 人类玩家夜间行动相关事件
  socketStore.on('werewolf:human_night_action_complete', handleHumanNightActionComplete)
  socketStore.on('werewolf:night_action_result', handleNightActionResult)
  
  // T54: 观战模式事件
  socketStore.on('werewolf:spectator_mode', handleSpectatorMode)
  socketStore.on('werewolf:last_words_options', handleLastWordsOptions)
  
  // 旧的事件监听（兼容）
  socketStore.on('game_state_update', handleGameStateUpdate)
  socketStore.on('game_ended', handleGameEnded)
  socketStore.on('game_log', handleGameLog)
}

/**
 * T20: 处理等待人类玩家行动事件
 */
function handleWaitingForHuman(data) {
  console.log('收到等待人类玩家事件:', data)
  
  if (data.action_type === 'speech' && data.seat_number === gameStore.mySeatNumber) {
    // 设置等待输入状态
    gameStore.setWaitingForInput(true)
    gameStore.setSpeechTimeout(data.timeout_seconds)
    
    ElMessage.info({
      message: '轮到你发言了！',
      duration: 3000
    })
  } else if (data.action_type === 'vote' && data.seat_number === gameStore.mySeatNumber) {
    // T28: 设置投票等待状态
    gameStore.setWaitingForInput(true)
    gameStore.setVoteTimeout(data.timeout_seconds)
    
    ElMessage.info({
      message: '轮到你投票了！',
      duration: 3000
    })
  } else if (['werewolf_kill', 'seer_check', 'witch_action', 'hunter_shoot'].includes(data.action_type)) {
    // T37: 夜间行动
    if (data.seat_number === gameStore.mySeatNumber) {
      gameStore.setWaitingForInput(true)
      gameStore.setNightActionType(data.action_type)
      gameStore.setNightActionTimeout(data.timeout_seconds)
      
      // 解析夜间行动选项
      if (data.metadata?.options) {
        gameStore.setNightActionOptions(data.metadata.options)
      }
      
      // 女巫专用信息
      if (data.action_type === 'witch_action' && data.metadata) {
        gameStore.updateWitchPotions({
          hasAntidote: data.metadata.has_antidote,
          hasPoison: data.metadata.has_poison
        })
        if (data.metadata.killed_seat) {
          gameStore.setKilledPlayerInfo({
            seat_number: data.metadata.killed_seat,
            can_self_save: data.metadata.can_self_save
          })
        } else {
          gameStore.setKilledPlayerInfo(null)
        }
      }
      
      const actionMessages = {
        'werewolf_kill': '狼人行动时间，请选择击杀目标！',
        'seer_check': '预言家行动时间，请选择查验目标！',
        'witch_action': '女巫行动时间，请选择是否使用药水！',
        'hunter_shoot': '猎人技能触发，请选择是否开枪！'
      }
      
      ElMessage.info({
        message: actionMessages[data.action_type] || '轮到你行动了！',
        duration: 3000
      })
    }
  }
}

// T62: 处理 AI 代打事件
function handleAiTakeover(data) {
  const actionLabels = {
    speech: '发言',
    vote: '投票',
    werewolf_kill: '狼人行动',
    seer_check: '预言家查验',
    witch_action: '女巫行动',
    hunter_shoot: '猎人开枪'
  }
  const actionText = actionLabels[data.action_type] || '行动'
  const isMe = data.seat_number === gameStore.mySeatNumber
  const logText = `${data.seat_number}号玩家超时，AI 代打${actionText}`

  if (isMe) {
    gameStore.setWaitingForInput(false)

    if (data.action_type === 'speech') {
      gameStore.clearSpeechState()
    } else if (data.action_type === 'vote') {
      gameStore.setVote(null)
      gameStore.clearVoteState()
    } else if (['werewolf_kill', 'seer_check', 'witch_action', 'hunter_shoot'].includes(data.action_type)) {
      gameStore.clearNightActionState()
    }

    ElMessage.warning({
      message: `你已超时，AI 已代打${actionText}`,
      duration: 4000
    })
  }

  gameStore.addGameLog({
    type: 'system',
    content: logText,
    seat_number: data.seat_number
  })
}

/**
 * T20: 处理发言选项事件
 */
function handleSpeechOptions(data) {
  console.log('收到发言选项:', data)
  
  if (data.seat_number === gameStore.mySeatNumber) {
    gameStore.setSpeechOptions(data.options || [])
  }
}

/**
 * T20: 处理人类玩家发言完成事件
 */
function handleHumanSpeechComplete(data) {
  console.log('人类玩家发言完成:', data)
  
  // 添加发言到日志
  gameStore.addGameLog({
    type: 'speech',
    content: data.content,
    player_id: null,
    player_name: `${data.seat_number}号玩家`,
    seat_number: data.seat_number
  })
}

/**
 * T20: 处理发言提交确认事件
 */
function handleSpeechSubmitted(data) {
  if (data.success) {
    console.log('发言提交成功')
  }
}

/**
 * T28: 处理投票选项事件
 */
function handleVoteOptions(data) {
  console.log('收到投票选项:', data)
  
  if (data.seat_number === gameStore.mySeatNumber) {
    // 转换选项格式为 VotePanel 需要的格式
    const formattedOptions = (data.options || []).map(opt => ({
      id: opt.player_id || `seat_${opt.seat_number}`,
      name: opt.player_name,
      seat_number: opt.seat_number,
      vote_count: 0
    }))
    gameStore.setVoteOptions(formattedOptions)
    if (data.timeout_seconds) {
      gameStore.setVoteTimeout(data.timeout_seconds)
    }
  }
}

/**
 * T28: 处理人类玩家投票完成事件
 */
function handleHumanVoteComplete(data) {
  console.log('人类玩家投票完成:', data)
  
  // 添加投票日志
  const voteText = data.is_abstain 
    ? `${data.voter_seat}号玩家弃票`
    : `${data.voter_seat}号玩家投给了${data.target_seat}号`
  
  gameStore.addGameLog({
    type: 'vote',
    content: voteText,
    player_id: null,
    player_name: data.voter_name,
    seat_number: data.voter_seat
  })
}

/**
 * T37: 处理人类玩家夜间行动完成事件
 */
function handleHumanNightActionComplete(data) {
  console.log('人类玩家夜间行动完成:', data)
  
  // 清除夜间行动状态
  gameStore.clearNightActionState()
  gameStore.setWaitingForInput(false)
  
  // 根据行动类型添加日志
  const { action_type, result, seat_number } = data
  let logContent = ''
  
  switch (action_type) {
    case 'werewolf_kill':
      logContent = result.target_seat 
        ? `你选择击杀${result.target_seat}号玩家`
        : '你选择空刀'
      break
    case 'seer_check':
      if (result.target_seat && result.check_result) {
        logContent = `你查验了${result.target_seat}号玩家，结果是${result.check_result}`
        // 保存查验结果供界面显示
        gameStore.setNightActionResult({
          target_seat: result.target_seat,
          is_werewolf: result.is_werewolf,
          result_text: result.check_result
        })
      } else {
        logContent = '你没有查验任何人'
      }
      break
    case 'witch_action':
      if (result.save_target) {
        logContent = `你使用解药救了${result.save_target}号玩家`
      } else if (result.poison_target) {
        logContent = `你使用毒药毒杀了${result.poison_target}号玩家`
      } else {
        logContent = '你选择不使用任何药水'
      }
      break
    case 'hunter_shoot':
      logContent = result.target_seat
        ? `你开枪带走了${result.target_seat}号玩家`
        : '你选择不开枪'
      break
  }
  
  if (logContent) {
    gameStore.addGameLog({
      type: 'night_action',
      content: logContent,
      player_id: null,
      player_name: `${seat_number}号玩家`,
      seat_number: seat_number
    })
  }
}

/**
 * T37: 处理夜间行动结果（发送给行动者的确认）
 */
function handleNightActionResult(data) {
  console.log('夜间行动结果:', data)
  
  if (data.success) {
    ElMessage.success('行动成功！')
  } else if (data.error) {
    ElMessage.error(data.error)
  }
}

/**
 * T54: 处理观战模式切换事件
 */
function handleSpectatorMode(data) {
  console.log('切换到观战模式:', data)
  
  // 设置观战模式
  gameStore.setSpectatorMode(true)
  gameStore.setIsAlive(false)
  
  // 清除所有等待状态
  gameStore.clearSpeechState()
  gameStore.clearVoteState()
  gameStore.clearNightActionState()
  gameStore.clearLastWordsState()
  
  // 显示提示
  ElNotification({
    title: '已进入观战模式',
    message: '你已被淘汰，现在以观战者身份观看游戏',
    type: 'info',
    duration: 5000,
    position: 'top-right'
  })
  
  // 添加日志
  gameStore.addGameLog({
    type: 'system',
    content: '你已进入观战模式',
    player_id: null,
    player_name: '系统',
    seat_number: data.seat_number
  })
}

/**
 * T54: 处理遗言选项事件
 */
function handleLastWordsOptions(data) {
  console.log('收到遗言选项:', data)
  
  // 设置遗言阶段状态
  gameStore.setLastWordsPhase(true, {
    seat_number: data.seat_number,
    options: data.options || [],
    death_reason: data.death_reason,
    timeout_seconds: data.timeout_seconds || 60
  })
  
  // 如果是自己的遗言回合，显示提示
  if (data.seat_number === gameStore.mySeatNumber) {
    ElNotification({
      title: '发表遗言',
      message: '你已被淘汰，现在可以发表遗言',
      type: 'warning',
      duration: 3000,
      position: 'top-right'
    })
  }
}

/**
 * 处理角色选择确认事件
 * @param {Object} data - 角色选择结果
 * @param {string} data.role - 分配的角色名称
 * @param {number} data.seat_number - 分配的座位号
 * @param {Array} data.werewolf_teammates - 狼人队友列表（仅狼人角色）
 * @param {string} data.role_description - 角色描述
 */
function handleRoleSelected(data) {
  console.log('收到角色选择确认:', data)
  
  // 更新当前玩家角色信息
  gameStore.setMyRole({
    name: data.role,
    type: getRoleType(data.role),
    team: getRoleTeam(data.role),
    description: data.role_description || ''
  })
  
  // 更新当前玩家座位号
  gameStore.setMySeatNumber(data.seat_number)
  
  // 更新玩家存活状态
  gameStore.setIsAlive(true)
  
  // 如果是狼人，更新狼人队友列表
  if (data.werewolf_teammates && data.werewolf_teammates.length > 0) {
    gameStore.setWerewolfTeammates(data.werewolf_teammates)
  }
  
  // 添加游戏日志
  gameStore.addGameLog({
    type: 'role_assigned',
    content: `你的角色是 ${data.role}，座位号 ${data.seat_number}`,
    player_id: gameStore.myPlayerId,
    player_name: '系统'
  })
  
  ElMessage.success(`角色分配成功：${data.role}，座位号 ${data.seat_number}`)
}

/**
 * 获取角色类型
 */
function getRoleType(roleName) {
  const roleTypes = {
    '狼人': 'werewolf',
    '预言家': 'god',
    '女巫': 'god',
    '猎人': 'god',
    '村民': 'villager'
  }
  return roleTypes[roleName] || 'villager'
}

/**
 * 获取角色阵营
 */
function getRoleTeam(roleName) {
  const roleTeams = {
    '狼人': 'werewolf',
    '预言家': 'villager',
    '女巫': 'villager',
    '猎人': 'villager',
    '村民': 'villager'
  }
  return roleTeams[roleName] || 'villager'
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
  // T37: 使用新的人类玩家夜间行动方法
  const targetSeat = target?.seat_number || null
  const role = gameStore.myRole?.name
  
  // 根据角色确定行动类型
  let actionType = null
  let witchAction = null
  
  switch (role) {
    case '狼人':
      actionType = 'werewolf_kill'
      break
    case '预言家':
      actionType = 'seer_check'
      break
    case '猎人':
      actionType = 'hunter_shoot'
      break
    case '女巫':
      // 女巫的技能使用通过 use-antidote 和 use-poison 事件处理
      // 这里不应该被调用
      console.warn('女巫技能应通过专用事件处理')
      return
    default:
      console.error('未知角色:', role)
      return
  }
  
  try {
    socketStore.submitHumanNightAction(
      roomCode.value,
      gameStore.gameId,
      actionType,
      targetSeat,
      witchAction
    )
    gameStore.useSkill()
    gameStore.clearNightActionState()
    selectedPlayerId.value = null
  } catch (err) {
    ElMessage.error('行动提交失败: ' + err.message)
  }
}

// 狼人空刀
function handleEmptyKill() {
  try {
    socketStore.submitHumanNightAction(
      roomCode.value,
      gameStore.gameId,
      'werewolf_kill',
      null,  // 空刀，不选择目标
      null
    )
    gameStore.useSkill()
    gameStore.clearNightActionState()
    ElMessage.info('已选择不击杀任何人')
  } catch (err) {
    ElMessage.error('行动提交失败: ' + err.message)
  }
}

// 女巫自救（使用解药救自己）
function handleSelfSave() {
  try {
    socketStore.submitHumanNightAction(
      roomCode.value,
      gameStore.gameId,
      'witch_action',
      gameStore.mySeatNumber,
      'save'
    )
    gameStore.useSkill()
    gameStore.clearNightActionState()
    gameStore.updateWitchPotions({ hasAntidote: false })
    ElMessage.info('已使用解药自救')
  } catch (err) {
    ElMessage.error('行动提交失败: ' + err.message)
  }
}

// T37: 女巫使用解药救人
function handleUseAntidote(target) {
  try {
    socketStore.submitHumanNightAction(
      roomCode.value,
      gameStore.gameId,
      'witch_action',
      target?.seat_number || gameStore.killedPlayerInfo?.seat_number,
      'save'
    )
    gameStore.useSkill()
    gameStore.clearNightActionState()
    gameStore.updateWitchPotions({ hasAntidote: false })
    ElMessage.info('已使用解药救人')
  } catch (err) {
    ElMessage.error('行动提交失败: ' + err.message)
  }
}

// T37: 女巫使用毒药
function handleUsePoison(target) {
  try {
    socketStore.submitHumanNightAction(
      roomCode.value,
      gameStore.gameId,
      'witch_action',
      target?.seat_number,
      'poison'
    )
    gameStore.useSkill()
    gameStore.clearNightActionState()
    gameStore.updateWitchPotions({ hasPoison: false })
    ElMessage.info('已使用毒药毒杀')
  } catch (err) {
    ElMessage.error('行动提交失败: ' + err.message)
  }
}

// T37: 跳过夜间行动（女巫不使用药水、猎人不开枪等）
function handleSkipNightAction() {
  const role = gameStore.myRole?.name
  let actionType = null
  
  switch (role) {
    case '女巫':
      actionType = 'witch_action'
      break
    case '猎人':
      actionType = 'hunter_shoot'
      break
    default:
      console.warn('当前角色不支持跳过行动:', role)
      return
  }
  
  try {
    socketStore.submitHumanNightAction(
      roomCode.value,
      gameStore.gameId,
      actionType,
      null,
      actionType === 'witch_action' ? 'pass' : null
    )
    gameStore.useSkill()
    gameStore.clearNightActionState()
    ElMessage.info('已跳过行动')
  } catch (err) {
    ElMessage.error('行动提交失败: ' + err.message)
  }
}

function handleVote(player) {
  // T28: 使用新的人类玩家投票方法
  const targetSeat = player.seat_number || null
  
  try {
    socketStore.submitHumanVote(
      roomCode.value,
      gameStore.gameId,
      targetSeat
    )
    gameStore.setVote(player.id)
    gameStore.clearVoteState()
    ElMessage.success('投票已提交')
  } catch (err) {
    ElMessage.error('投票提交失败: ' + err.message)
  }
}

function handleAbstain() {
  // T28: 使用新的人类玩家投票方法（弃票）
  try {
    socketStore.submitHumanVote(
      roomCode.value,
      gameStore.gameId,
      null  // null 表示弃票
    )
    gameStore.setVote(null)
    gameStore.clearVoteState()
    ElMessage.info('已弃票')
  } catch (err) {
    ElMessage.error('弃票提交失败: ' + err.message)
  }
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
async function handleSubmitSpeech(data) {
  // data 可能是对象 { content, optionId } 或字符串（向后兼容）
  const content = typeof data === 'object' ? data.content : data
  const optionId = typeof data === 'object' ? data.optionId : null
  
  if (!content || isSubmittingSpeech.value) return
  
  isSubmittingSpeech.value = true
  try {
    // T20: 使用新的人类玩家发言提交方法
    socketStore.submitHumanSpeech(
      roomCode.value,
      myPlayerId.value,
      content,
      optionId
    )
    ElMessage.success('发言已提交')
    // 清除发言状态
    gameStore.clearSpeechState()
  } catch (err) {
    ElMessage.error('发言提交失败: ' + err.message)
  } finally {
    isSubmittingSpeech.value = false
  }
}

// 新增：跳过发言
function handleSkipSpeech() {
  try {
    socketStore.submitHumanSpeech(
      roomCode.value,
      myPlayerId.value,
      '（跳过发言）',
      'pass'
    )
    ElMessage.info('已跳过发言')
    gameStore.clearSpeechState()
  } catch (err) {
    ElMessage.error('跳过发言失败')
  }
}

function handleBackToLobby() {
  router.push('/lobby')
}

// 返回首页
function handleBackToHome() {
  router.push('/')
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
      state.players.forEach((p, index) => {
        const seatNumber = p.seat_number ?? index + 1
        const playerId = p.id || p.player_id || `seat_${seatNumber}`
        playerStates[playerId] = {
          seat_number: seatNumber,
          display_name: p.display_name || `玩家${seatNumber}`,
          is_alive: p.is_alive,
          role_name: p.role || p.role_name,
          role_type: p.team || p.role_type,
          role_revealed: Boolean(p.role || p.role_name),
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

onMounted(async () => {
  // 先确保 socket 连接，再注册监听器
  if (!socketStore.isConnected) {
    await socketStore.connect()
  }
  
  // 连接后加入房间，确保能收到广播消息
  socketStore.joinRoom(roomCode.value)
  
  // Socket 连接后再注册监听器
  setupSocketListeners()
  
  // F37-F40: 监听重连事件
  socketStore.on('reconnect', handleReconnect)
  
  // 最后加载游戏状态
  loadGameState()
})

onUnmounted(() => {
  // 离开狼人杀房间，停止游戏
  if (roomCode.value) {
    socketStore.leaveWerewolfRoom(roomCode.value, myPlayerId.value)
  }
  
  // 清理事件监听
  socketStore.off('werewolf:role_selected', handleRoleSelected)
  socketStore.off('werewolf:vote_countdown', handleVoteCountdown)
  socketStore.off('game_state_update', handleGameStateUpdate)
  socketStore.off('game_ended', handleGameEnded)
  socketStore.off('game_log', handleGameLog)
  socketStore.off('reconnect', handleReconnect)
  socketStore.off('werewolf:ai_takeover', handleAiTakeover)
  
  // T28: 清理投票相关事件监听
  socketStore.off('werewolf:vote_options', handleVoteOptions)
  socketStore.off('werewolf:human_vote_complete', handleHumanVoteComplete)
  
  // T37: 清理夜间行动相关事件监听
  socketStore.off('werewolf:human_night_action_complete', handleHumanNightActionComplete)
  socketStore.off('werewolf:night_action_result', handleNightActionResult)
  
  // 清理倒计时
  if (voteCountdownTimer) {
    clearInterval(voteCountdownTimer)
  }
})

/**
 * 重置游戏状态，清理上一局的历史数据
 */
function resetGameState() {
  // 使用 store 的 resetForNewGame 方法清理所有游戏相关状态
  gameStore.resetForNewGame()
  console.log('Game state reset completed')
}
</script>

<style scoped>
.werewolf-game-view {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #0a0a14;
  background-image: url('@/assets/images/werewolf/werewolf-backgroud.jpeg');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  color: var(--color-text-primary);
  overflow: hidden;
}

.werewolf-game-view.is-night {
  /* 夜晚模式可以加深背景或叠加遮罩 */
  box-shadow: inset 0 0 100px rgba(0, 0, 0, 0.8);
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

/* 返回首页按钮 */
.back-home-btn {
  color: var(--color-text-secondary);
  font-size: 14px;
  padding: 8px 12px;
  transition: all .3s ease;
  display: flex;
  align-items: center;
  gap: 6px;
  border-radius: 6px;
}

.back-home-btn:hover {
  color: var(--color-primary);
  background: rgba(0, 240, 255, .1);
  text-shadow: 0 0 8px var(--color-primary);
}

.back-home-btn .el-icon {
  font-size: 16px;
}

.divider {
  color: rgba(0, 240, 255, .3);
  margin: 0 4px;
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

/* 主持人面板 - 中央上部位置 */
.host-panel-center {
  width: 100%;
  max-width: 600px;
  margin: 0 auto 20px;
  z-index: 100;
}

.game-main {
  flex: 1;
  display: grid;
  grid-template-columns: 340px 1fr 360px;
  gap: 20px;
  padding: 20px;
  overflow: hidden;
  position: relative;
  z-index: 1;
  min-height: calc(100vh - 100px);
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

/* T54: 观战模式卡片样式 */
.spectator-card {
  background: rgba(10, 10, 20, .9);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  border: 1px solid rgba(150, 150, 150, .3);
  padding: 18px;
  position: relative;
  overflow: hidden;
}

.spectator-card:before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, rgba(150, 150, 150, .5), rgba(100, 100, 100, .5), rgba(150, 150, 150, .5));
}

.spectator-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(100, 100, 100, .15), rgba(80, 80, 80, .15));
  border: 1px solid rgba(150, 150, 150, .3);
  text-align: center;
}

.spectator-icon {
  font-size: 48px;
  color: rgba(150, 150, 150, .8);
  margin-bottom: 12px;
}

.spectator-text {
  font-size: 18px;
  font-weight: 700;
  color: rgba(150, 150, 150, .9);
  margin: 0 0 8px;
}

.spectator-desc {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.7;
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
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  /* 移除背景色和边框，让背景图透出来 */
  background: transparent;
  border: none;
  position: relative;
  padding: 20px;
  overflow: hidden;
  min-height: 650px;
}

.host-panel-center {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  justify-content: center;
  z-index: 20;
  pointer-events: none;
}

.host-panel-center > * {
  pointer-events: auto;
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
  gap: 16px;
  max-height: calc(100vh - 140px);
  overflow: hidden;
}

/* 确保GameLog可以收缩 */
.right-panel > * {
  flex-shrink: 0;
}

.right-panel > :first-child {
  flex: 1;
  min-height: 0;
  overflow: auto;
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

/* 响应式布局 */
@media (max-width: 1600px) {
  .game-main {
    grid-template-columns: 300px 1fr 340px;
  }
}

@media (max-width: 1400px) {
  .game-main {
    grid-template-columns: 280px 1fr 320px;
  }
}

@media (max-width: 1200px) {
  .game-main {
    grid-template-columns: 260px 1fr 300px;
    gap: 16px;
    padding: 16px;
  }
}

@media (max-width: 992px) {
  .game-main {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr auto;
  }
  
  .left-panel {
    flex-direction: row;
    flex-wrap: wrap;
  }
  
  .right-panel {
    max-height: none;
  }
  
  .right-panel > :first-child {
    max-height: 400px;
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