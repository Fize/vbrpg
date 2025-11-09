<template>
  <div class="game-board">
    <!-- Game Header -->
    <div class="game-header">
      <div class="room-info">
        <h2>房间: {{ gameStore.roomCode }}</h2>
        <el-tag :type="getPhaseType(gameStore.currentPhase)">
          {{ gameStore.currentPhase || '准备中' }}
        </el-tag>
      </div>
      
      <TurnIndicator
        :current-player-id="gameStore.currentTurn"
        :turn-number="gameStore.turnNumber"
        :is-ai-thinking="gameStore.isAiThinking"
        :participants="gameStore.activeParticipants"
      />
      
      <div class="game-actions">
        <el-button size="small" @click="showRules">规则说明</el-button>
        <el-button size="small" type="danger" @click="handleLeaveGame">离开游戏</el-button>
      </div>
    </div>

    <!-- AI Thinking Indicator -->
    <AIThinkingIndicator
      v-if="gameStore.isAiThinking"
      :ai-player-id="gameStore.aiThinkingPlayer"
      :participants="gameStore.activeParticipants"
    />

    <!-- Main Game Area -->
    <div class="game-content">
      <!-- Loading State -->
      <LoadingIndicator
        v-if="!gameStore.gameState"
        text="游戏加载中..."
        variant="primary"
        size="large"
      />
      
      <!-- Crime Scene Board -->
      <CrimeSceneBoard
        v-else
        :game-state="gameStore.gameState"
        :participants="gameStore.activeParticipants"
      />
    </div>

    <!-- Action Panel -->
    <ActionPanel
      v-if="gameStore.isMyTurn && !gameStore.gameEnded"
      :game-state="gameStore.gameState"
      :room-code="gameStore.roomCode"
      @action-submitted="handleActionSubmitted"
    />

    <!-- Game Ended Dialog -->
    <el-dialog
      v-model="showEndDialog"
      title="游戏结束"
      width="400px"
      :close-on-click-modal="false"
    >
      <div class="game-ended">
        <el-result
          :icon="isWinner ? 'success' : 'info'"
          :title="winnerMessage"
          :sub-title="getWinnerName()"
        >
          <template #extra>
            <el-button type="primary" @click="returnToLobby">返回大厅</el-button>
            <el-button @click="showEndDialog = false">查看结果</el-button>
          </template>
        </el-result>
      </div>
    </el-dialog>

    <!-- Rules Dialog -->
    <el-dialog v-model="showRulesDialog" title="游戏规则" width="600px">
      <div class="game-rules">
        <h3>犯罪现场 - 游戏规则</h3>
        <ol>
          <li>游戏开始时，系统随机选择凶手、凶器和犯罪地点</li>
          <li>每位玩家获得5张证据卡，这些卡片不是答案</li>
          <li>轮流进行调查：
            <ul>
              <li>调查地点：查看该地点的线索</li>
              <li>展示线索：从手牌中展示一张卡片</li>
              <li>指控：如果确信答案，可以进行指控</li>
            </ul>
          </li>
          <li>正确指控出凶手、凶器和地点的玩家获胜</li>
          <li>错误指控不会被淘汰，但会浪费一个回合</li>
        </ol>
      </div>
    </el-dialog>

    <!-- Reconnection Dialog -->
    <ReconnectionDialog
      v-model:visible="showReconnectionDialog"
      :status="reconnectionStatus"
      :grace-period-seconds="300"
      :disconnect-duration="disconnectDuration"
      :failure-message="reconnectionFailureMessage"
      @close="showReconnectionDialog = false"
      @retry="handleReconnectRetry"
      @return-to-lobby="returnToLobby"
      @spectate="handleSpectate"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { useGameStore } from '@/stores/game'
import websocketService from '@/services/websocket'
import CrimeSceneBoard from '@/components/CrimeSceneBoard.vue'
import TurnIndicator from '@/components/TurnIndicator.vue'
import ActionPanel from '@/components/ActionPanel.vue'
import AIThinkingIndicator from '@/components/AIThinkingIndicator.vue'
import LoadingIndicator from '@/components/LoadingIndicator.vue'
import ReconnectionDialog from '@/components/ReconnectionDialog.vue'

const router = useRouter()
const route = useRoute()
const gameStore = useGameStore()

const showEndDialog = ref(false)
const showRulesDialog = ref(false)
const isWinner = ref(false)
const winnerMessage = ref('')

// Reconnection state
const showReconnectionDialog = ref(false)
const reconnectionStatus = ref('disconnected') // 'disconnected', 'reconnected', 'failed', 'replaced'
const disconnectDuration = ref('')
const reconnectionFailureMessage = ref('')

// Computed
const getPhaseType = (phase) => {
  const types = {
    'Setup': 'info',
    'Investigation': 'primary',
    'Accusation': 'warning',
    'Resolution': 'success'
  }
  return types[phase] || 'info'
}

const getWinnerName = () => {
  if (!gameStore.winner) return ''
  const winner = gameStore.activeParticipants.find(p => 
    p.player_id === gameStore.winner || `AI_${p.id}` === gameStore.winner
  )
  return winner ? (winner.player?.username || winner.ai_personality || '未知') : ''
}

// Methods
const showRules = () => {
  showRulesDialog.value = true
}

const handleLeaveGame = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要离开游戏吗？如果游戏进行中，你将被AI替代。',
      '离开游戏',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const playerId = localStorage.getItem('userId')
    websocketService.leaveRoom(gameStore.roomCode, playerId)
    gameStore.leaveRoom()
    router.push('/games')
  } catch {
    // User cancelled
  }
}

const handleActionSubmitted = () => {
  ElMessage.success('行动已提交')
}

const returnToLobby = () => {
  gameStore.leaveRoom()
  router.push('/games')
}

// WebSocket event handlers
const setupWebSocketListeners = () => {
  // Game state updates
  websocketService.onGameStateUpdate((data) => {
    console.log('Game state update:', data)
    if (data.game_state) {
      gameStore.updateGameState(data.game_state)
    }
  })

  // Turn changed
  websocketService.onTurnChanged((data) => {
    console.log('Turn changed:', data)
    gameStore.setCurrentTurn(data.current_player_id, data.turn_number)
    
    const currentUserId = localStorage.getItem('userId')
    if (data.current_player_id === currentUserId) {
      ElMessage.info('轮到你了！')
    }
  })

  // AI thinking
  websocketService.onAiThinking((data) => {
    console.log('AI thinking:', data)
    gameStore.setAiThinking(true, data.ai_player_id)
  })

  // AI action
  websocketService.onAiAction((data) => {
    console.log('AI action:', data)
    gameStore.setAiThinking(false)
    ElMessage.info(`AI ${data.ai_player_id} 执行了行动`)
  })

  // Game ended
  websocketService.onGameEnded((data) => {
    console.log('Game ended:', data)
    gameStore.setGameEnded(true, data.winner_id)
    
    const currentUserId = localStorage.getItem('userId')
    isWinner.value = data.winner_id === currentUserId
    winnerMessage.value = data.winner_id ? 
      (isWinner.value ? '恭喜你赢得了游戏！' : '游戏结束') :
      '游戏平局'
    
    showEndDialog.value = true
  })

  // Error handling
  websocketService.onError((data) => {
    console.error('WebSocket error:', data)
    ElMessage.error(data.message || '发生错误')
  })

  // Reconnection events
  websocketService.onDisconnected((data) => {
    console.log('Disconnected, starting reconnection...')
    showReconnectionDialog.value = true
    reconnectionStatus.value = 'disconnected'
  })

  websocketService.onReconnected((data) => {
    console.log('Reconnected successfully:', data)
    showReconnectionDialog.value = true
    reconnectionStatus.value = 'reconnected'
    
    const seconds = data.disconnect_duration_seconds || 0
    const minutes = Math.floor(seconds / 60)
    const secs = seconds % 60
    disconnectDuration.value = `${minutes}分${secs}秒`
    
    ElMessage.success('重连成功！')
    
    // Auto close after 2 seconds
    setTimeout(() => {
      showReconnectionDialog.value = false
    }, 2000)
  })

  websocketService.onPlayerDisconnected((data) => {
    console.log('Another player disconnected:', data)
    ElMessage.warning(`${data.player_id} 已断线，等待重连中...`)
  })

  websocketService.onPlayerReconnected((data) => {
    console.log('Another player reconnected:', data)
    ElMessage.info(`${data.player_id} 已重新连接`)
  })

  websocketService.onPlayerReplacedByAI((data) => {
    console.log('Player replaced by AI:', data)
    const currentUserId = localStorage.getItem('userId')
    
    if (data.player_id === currentUserId) {
      // Current player was replaced
      showReconnectionDialog.value = true
      reconnectionStatus.value = 'replaced'
      ElMessage.warning('您已被AI替代')
    } else {
      ElMessage.info(`${data.player_id} 已被AI替代`)
    }
  })

  websocketService.onReconnectionFailed((data) => {
    console.error('Reconnection failed:', data)
    showReconnectionDialog.value = true
    reconnectionStatus.value = 'failed'
    reconnectionFailureMessage.value = '无法重新连接到服务器，请检查网络连接'
  })
}

const handleReconnectRetry = () => {
  const playerId = localStorage.getItem('userId')
  if (!websocketService.isConnected()) {
    websocketService.connect(playerId)
  }
  websocketService.joinRoom(gameStore.roomCode, playerId)
}

const handleSpectate = () => {
  showReconnectionDialog.value = false
  ElMessage.info('观战模式暂未实现')
}

const cleanupWebSocketListeners = () => {
  websocketService.offGameEvents()
}

// Lifecycle
onMounted(() => {
  // Verify we're in a game
  if (!gameStore.isInRoom || gameStore.currentRoom?.status !== 'In Progress') {
    ElMessage.warning('游戏未开始或已结束')
    router.push('/games')
    return
  }

  // Setup WebSocket listeners
  setupWebSocketListeners()

  // Join WebSocket room if not already
  const playerId = localStorage.getItem('userId')
  if (!websocketService.isConnected()) {
    websocketService.connect(playerId)
  }
  websocketService.joinRoom(gameStore.roomCode, playerId)
})

onBeforeUnmount(() => {
  cleanupWebSocketListeners()
})
</script>

<style scoped>
.game-board {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.game-header {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.room-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.room-info h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.game-actions {
  display: flex;
  gap: 10px;
}

.game-content {
  background: white;
  border-radius: 12px;
  padding: 30px;
  min-height: 500px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  color: #909399;
}

.loading-state .el-icon {
  font-size: 48px;
  margin-bottom: 20px;
}

.game-ended {
  text-align: center;
  padding: 20px;
}

.game-rules h3 {
  margin-top: 0;
  color: #303133;
}

.game-rules ol {
  text-align: left;
  line-height: 1.8;
}

.game-rules ul {
  margin-top: 10px;
}

/* Responsive */
@media (max-width: 768px) {
  .game-header {
    flex-direction: column;
    gap: 15px;
  }

  .room-info {
    flex-direction: column;
    text-align: center;
  }

  .game-actions {
    width: 100%;
    justify-content: center;
  }

  .game-content {
    padding: 15px;
  }
}
</style>
