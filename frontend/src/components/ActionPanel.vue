<template>
  <div class="action-panel">
    <div class="panel-header">
      <h3>你的回合 - 选择行动</h3>
      <el-tag type="primary">{{ availableActions.length }} 个可用行动</el-tag>
    </div>

    <div class="actions-container">
      <!-- Investigate Location -->
      <div v-if="canInvestigate" class="action-group">
        <h4>🔍 调查地点</h4>
        <div class="action-buttons">
          <el-button
            v-for="location in uninvestigatedLocations"
            :key="location"
            type="primary"
            plain
            @click="handleInvestigate(location)"
          >
            调查 {{ location }}
          </el-button>
        </div>
      </div>

      <!-- Reveal Clue -->
      <div v-if="canRevealClue" class="action-group">
        <h4>🃏 展示线索</h4>
        <div class="action-buttons">
          <el-button
            type="success"
            plain
            @click="handleRevealClue"
          >
            展示手牌中的线索
          </el-button>
        </div>
        <p class="action-hint">展示一张手牌证明它不是答案</p>
      </div>

      <!-- Make Accusation -->
      <div class="action-group">
        <h4>⚖️ 指控凶手</h4>
        <el-button
          type="warning"
          @click="showAccusationDialog = true"
        >
          进行指控
        </el-button>
        <p class="action-hint">如果你确信答案，可以进行指控</p>
      </div>

      <!-- Pass Turn -->
      <div class="action-group">
        <h4>⏭️ 跳过回合</h4>
        <el-button
          plain
          @click="handlePassTurn"
        >
          跳过本回合
        </el-button>
      </div>
    </div>

    <!-- Accusation Dialog -->
    <el-dialog
      v-model="showAccusationDialog"
      title="指控凶手"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="accusationForm" label-width="80px">
        <el-form-item label="凶手">
          <el-select v-model="accusationForm.murderer" placeholder="选择凶手">
            <el-option
              v-for="suspect in suspects"
              :key="suspect"
              :label="suspect"
              :value="suspect"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="凶器">
          <el-select v-model="accusationForm.weapon" placeholder="选择凶器">
            <el-option
              v-for="weapon in weapons"
              :key="weapon"
              :label="weapon"
              :value="weapon"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="地点">
          <el-select v-model="accusationForm.location" placeholder="选择地点">
            <el-option
              v-for="location in locations"
              :key="location"
              :label="location"
              :value="location"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showAccusationDialog = false">取消</el-button>
        <el-button
          type="warning"
          :disabled="!isAccusationComplete"
          @click="handleAccusation"
        >
          确认指控
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import websocketService from '@/services/websocket'

const props = defineProps({
  gameState: {
    type: Object,
    required: true
  },
  roomCode: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['action-submitted'])

// State
const showAccusationDialog = ref(false)
const accusationForm = ref({
  murderer: '',
  weapon: '',
  location: ''
})

// Game constants
const suspects = ['厨师', '管家', '医生', '园丁', '秘书', '司机']
const weapons = ['刀', '枪', '毒药', '绳子', '烛台', '扳手']
const locations = ['书房', '厨房', '卧室', '餐厅', '花园', '车库']

// Parse game data
const gameData = computed(() => {
  if (typeof props.gameState.game_data === 'string') {
    return JSON.parse(props.gameState.game_data)
  }
  return props.gameState.game_data || {}
})

const revealedClues = computed(() => gameData.value.revealed_clues || [])
const currentPhase = computed(() => props.gameState.current_phase || gameData.value.phase)

// Computed
const uninvestigatedLocations = computed(() => {
  const investigated = revealedClues.value
    .filter(c => c.type === 'investigation')
    .map(c => c.location)
  return locations.filter(loc => !investigated.includes(loc))
})

const canInvestigate = computed(() => {
  return currentPhase.value === 'Investigation' && uninvestigatedLocations.value.length > 0
})

const canRevealClue = computed(() => {
  // Simplified: assume player has cards if game is in progress
  return currentPhase.value === 'Investigation'
})

const availableActions = computed(() => {
  const actions = []
  if (canInvestigate.value) {
    actions.push(...uninvestigatedLocations.value.map(loc => ({ type: 'investigate', location: loc })))
  }
  if (canRevealClue.value) {
    actions.push({ type: 'reveal_clue' })
  }
  actions.push({ type: 'make_accusation' })
  actions.push({ type: 'pass_turn' })
  return actions
})

const isAccusationComplete = computed(() => {
  return accusationForm.value.murderer &&
         accusationForm.value.weapon &&
         accusationForm.value.location
})

// Methods
const submitAction = (action) => {
  const playerId = localStorage.getItem('userId')
  websocketService.sendGameAction(props.roomCode, playerId, action)
  emit('action-submitted')
}

const handleInvestigate = (location) => {
  ElMessageBox.confirm(
    `确定要调查 ${location} 吗？`,
    '调查地点',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    }
  ).then(() => {
    submitAction({
      action_type: 'investigate_location',
      parameters: { location }
    })
  }).catch(() => {
    // User cancelled
  })
}

const handleRevealClue = () => {
  ElMessageBox.confirm(
    '确定要展示手牌中的一张线索吗？',
    '展示线索',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'success'
    }
  ).then(() => {
    submitAction({
      action_type: 'reveal_clue',
      parameters: { card_index: 0 } // Simplified: reveal first card
    })
  }).catch(() => {
    // User cancelled
  })
}

const handleAccusation = () => {
  showAccusationDialog.value = false
  
  ElMessageBox.confirm(
    `你确定要指控吗？\n凶手: ${accusationForm.value.murderer}\n凶器: ${accusationForm.value.weapon}\n地点: ${accusationForm.value.location}`,
    '确认指控',
    {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    submitAction({
      action_type: 'make_accusation',
      parameters: {
        accusation: {
          murderer: accusationForm.value.murderer,
          weapon: accusationForm.value.weapon,
          location: accusationForm.value.location
        }
      }
    })
    
    // Reset form
    accusationForm.value = {
      murderer: '',
      weapon: '',
      location: ''
    }
  }).catch(() => {
    // User cancelled
    showAccusationDialog.value = true
  })
}

const handlePassTurn = () => {
  ElMessageBox.confirm(
    '确定要跳过本回合吗？',
    '跳过回合',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    }
  ).then(() => {
    submitAction({
      action_type: 'pass_turn',
      parameters: {}
    })
  }).catch(() => {
    // User cancelled
  })
}
</script>

<style scoped>
.action-panel {
  background: white;
  border-radius: 12px;
  padding: 25px;
  margin-top: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border: 3px solid #409eff;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 2px solid #DCDFE6;
}

.panel-header h3 {
  margin: 0;
  color: #303133;
  font-size: 20px;
}

.actions-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.action-group {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 15px;
  border: 1px solid #DCDFE6;
}

.action-group h4 {
  margin: 0 0 12px 0;
  color: #606266;
  font-size: 16px;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-buttons .el-button {
  width: 100%;
}

.action-hint {
  margin: 10px 0 0 0;
  font-size: 12px;
  color: #909399;
  font-style: italic;
}

/* Responsive */
@media (max-width: 768px) {
  .action-panel {
    padding: 15px;
  }

  .panel-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .actions-container {
    grid-template-columns: 1fr;
  }
}
</style>
