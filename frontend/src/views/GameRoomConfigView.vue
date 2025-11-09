<template>
  <div class="room-config-view">
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>创建游戏房间</span>
          <el-button 
            text 
            @click="goBack"
            class="back-button"
          >
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
        </div>
      </template>

      <div v-if="loading" class="loading-container">
        <el-icon class="is-loading"><Loading /></el-icon>
        <p>加载中...</p>
      </div>

      <div v-else-if="game" class="config-content">
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="100px"
          label-position="left"
        >
          <el-form-item label="游戏">
            <el-input :value="game.name" disabled />
          </el-form-item>

          <el-form-item label="玩家人数" prop="playerCount">
            <el-select
              v-model="form.playerCount"
              placeholder="选择玩家人数"
              style="width: 100%"
            >
              <el-option
                v-for="count in playerCountOptions"
                :key="count"
                :label="`${count} 人`"
                :value="count"
              />
            </el-select>
          </el-form-item>

          <el-alert
            type="info"
            :closable="false"
            show-icon
            style="margin-bottom: 20px"
          >
            <template #title>
              <p style="margin: 0; font-size: 14px;">
                如果真实玩家不足，AI 将自动填补空位
              </p>
            </template>
          </el-alert>
        </el-form>

        <div class="form-footer">
          <el-button @click="goBack">取消</el-button>
          <el-button
            type="primary"
            :loading="creating"
            @click="handleCreate"
          >
            创建房间
          </el-button>
        </div>
      </div>

      <el-empty v-else description="游戏信息加载失败" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Loading } from '@element-plus/icons-vue'
import { gamesApi, roomsApi } from '@/services/api'
import { useGameStore } from '@/stores/game'

const route = useRoute()
const router = useRouter()
const gameStore = useGameStore()

const formRef = ref(null)
const creating = ref(false)
const loading = ref(true)
const game = ref(null)

// Form data
const form = ref({
  playerCount: null
})

// Computed
const playerCountOptions = computed(() => {
  if (!game.value) return []
  const options = []
  for (let i = game.value.min_players; i <= game.value.max_players; i++) {
    options.push(i)
  }
  return options
})

// Form rules
const rules = {
  playerCount: [
    { required: true, message: '请选择玩家人数', trigger: 'change' }
  ]
}

// Methods
const goBack = () => {
  router.back()
}

const loadGame = async () => {
  const gameType = route.query.gameType
  
  if (!gameType) {
    ElMessage.error('缺少游戏类型参数')
    goBack()
    return
  }

  try {
    loading.value = true
    const response = await gamesApi.getGameDetails(gameType)
    game.value = response
    
    // Set default player count
    if (game.value) {
      form.value.playerCount = game.value.min_players
    }
  } catch (error) {
    console.error('Failed to load game:', error)
    ElMessage.error('加载游戏信息失败')
    goBack()
  } finally {
    loading.value = false
  }
}

const handleCreate = async () => {
  try {
    await formRef.value?.validate()
    
    creating.value = true
    gameStore.setLoading(true)
    gameStore.clearError()

    const roomData = await roomsApi.createRoom({
      game_type_slug: game.value.slug,
      max_players: form.value.playerCount,
      min_players: game.value.min_players
    })

    ElMessage.success('房间创建成功！')
    gameStore.setCurrentRoom(roomData)
    
    // Navigate to room lobby
    router.push({
      name: 'GameRoomLobby',
      params: { code: roomData.code }
    })
  } catch (error) {
    console.error('Failed to create room:', error)
    const errorMessage = error.response?.data?.detail || '创建房间失败，请重试'
    ElMessage.error(errorMessage)
    gameStore.setError(errorMessage)
  } finally {
    creating.value = false
    gameStore.setLoading(false)
  }
}

onMounted(() => {
  loadGame()
})
</script>

<style scoped>
.room-config-view {
  max-width: 600px;
  margin: 40px auto;
  padding: 0 20px;
}

.config-card {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 500;
  font-size: 16px;
}

.back-button {
  display: flex;
  align-items: center;
  gap: 4px;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--el-text-color-secondary);
}

.loading-container .el-icon {
  font-size: 32px;
  margin-bottom: 12px;
}

.config-content {
  padding: 20px 0;
}

.form-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid var(--el-border-color-light);
}
</style>
