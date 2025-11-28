<template>
  <div class="create-room-view">
    <div class="page-header">
      <el-button text :icon="ArrowLeft" @click="goBack">返回大厅</el-button>
      <h1 class="page-title">创建房间</h1>
    </div>
    
    <div class="create-room-container">
      <div class="game-info-section">
        <div class="game-card">
          <img 
            src="@/assets/images/werewolf/werewolf-across.jpeg" 
            alt="狼人杀"
            class="game-cover"
            @error="handleImageError"
          />
          <div class="game-details">
            <h2 class="game-name">狼人杀</h2>
            <p class="game-desc">标准10人局 - 3狼人|4村民|预言家|女巫|猎人</p>
          </div>
        </div>
      </div>
      
      <el-divider />
      
      <!-- 参与方式选择 -->
      <div class="participation-section">
        <h3 class="section-title">选择参与方式</h3>
        <div class="participation-options">
          <div 
            class="option-card" 
            :class="{ active: participationType === 'player' }"
            @click="participationType = 'player'"
          >
            <el-icon class="option-icon" :size="40"><User /></el-icon>
            <div class="option-info">
              <span class="option-name">玩家</span>
              <span class="option-desc">加入游戏，扮演一个角色参与游戏</span>
            </div>
            <el-icon v-if="participationType === 'player'" class="check-icon"><Check /></el-icon>
          </div>
          <div 
            class="option-card" 
            :class="{ active: participationType === 'spectator' }"
            @click="participationType = 'spectator'"
          >
            <el-icon class="option-icon" :size="40"><View /></el-icon>
            <div class="option-info">
              <span class="option-name">观战</span>
              <span class="option-desc">作为旁观者观看游戏，不参与投票等操作</span>
            </div>
            <el-icon v-if="participationType === 'spectator'" class="check-icon"><Check /></el-icon>
          </div>
        </div>
      </div>
      
      <!-- 角色选择（仅玩家模式） -->
      <div v-if="participationType === 'player'" class="role-section">
        <el-divider />
        <h3 class="section-title">角色偏好（可选）</h3>
        <p class="section-desc">选择一个你想扮演的角色，系统将优先为你分配。如不选择则随机分配。</p>
        <RoleSelector 
          v-model="selectedRole" 
          game-type="werewolf"
        />
      </div>
      
      <el-divider />
      
      <!-- 房间设置 -->
      <div class="settings-section">
        <h3 class="section-title">房间设置</h3>
        <el-form label-position="top">
          <el-form-item label="AI 玩家数量">
            <el-slider
              v-model="aiPlayerCount"
              :min="0"
              :max="9"
              :marks="aiMarks"
              show-stops
            />
            <p class="setting-hint">选择 AI 玩家数量（0-9），剩余位置由真人玩家填充</p>
          </el-form-item>
        </el-form>
      </div>
      
      <el-divider />
      
      <!-- 操作按钮 -->
      <div class="actions-section">
        <el-button size="large" @click="goBack">取消</el-button>
        <el-button 
          type="primary" 
          size="large"
          :loading="creating"
          @click="handleCreateRoom"
        >
          创建房间
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, User, View, Check } from '@element-plus/icons-vue'
import { roomsApi } from '@/services/api'
import RoleSelector from '@/components/werewolf/RoleSelector.vue'

const router = useRouter()

// 状态
const participationType = ref('player') // 'player' | 'spectator'
const selectedRole = ref(null)
const aiPlayerCount = ref(9) // 默认9个AI（只有创建者一个真人玩家）
const creating = ref(false)

// AI 数量滑块标记
const aiMarks = reactive({
  0: '0',
  3: '3',
  5: '5',
  7: '7',
  9: '全AI'
})

// 返回大厅
function goBack() {
  router.push('/lobby')
}

// 图片加载失败处理
function handleImageError(e) {
  e.target.style.display = 'none'
}

// 创建房间
async function handleCreateRoom() {
  creating.value = true
  
  try {
    // 创建房间
    const roomData = {
      game_type_slug: 'werewolf',
      max_players: 10,
      min_players: 10
    }
    
    const room = await roomsApi.createRoom(roomData)
    const roomCode = room.code
    
    // 选择角色（如果是玩家模式）
    if (participationType.value === 'player') {
      await roomsApi.selectRole(
        roomCode, 
        selectedRole.value?.id || null,
        false
      )
    } else {
      // 观战模式
      await roomsApi.selectRole(roomCode, null, true)
    }
    
    // 添加 AI 玩家
    for (let i = 0; i < aiPlayerCount.value; i++) {
      try {
        await roomsApi.addAIAgent(roomCode)
      } catch (err) {
        console.warn(`添加第 ${i + 1} 个 AI 失败:`, err)
      }
    }
    
    ElMessage.success('房间创建成功')
    
    // 跳转到房间等待页面
    router.push(`/room/${roomCode}`)
  } catch (err) {
    console.error('创建房间失败:', err)
    ElMessage.error(err.response?.data?.detail || '创建房间失败，请重试')
  } finally {
    creating.value = false
  }
}
</script>

<style scoped>
.create-room-view {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.page-header {
  max-width: 800px;
  margin: 0 auto 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-header .el-button {
  color: white;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: white;
  margin: 0;
}

.create-room-container {
  max-width: 800px;
  margin: 0 auto;
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.game-info-section {
  margin-bottom: 8px;
}

.game-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 12px;
}

.game-cover {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 8px;
}

.game-details {
  flex: 1;
}

.game-name {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px;
}

.game-desc {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 12px;
}

.section-desc {
  font-size: 14px;
  color: #909399;
  margin: 0 0 16px;
}

.participation-section {
  margin-bottom: 8px;
}

.participation-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.option-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 16px;
  background: #f5f7fa;
  border: 2px solid transparent;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.option-card:hover {
  background: #ecf5ff;
  border-color: #b3d8ff;
}

.option-card.active {
  background: #ecf5ff;
  border-color: var(--el-color-primary);
}

.option-icon {
  color: #606266;
  margin-bottom: 12px;
}

.option-card.active .option-icon {
  color: var(--el-color-primary);
}

.option-info {
  text-align: center;
}

.option-name {
  display: block;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.option-desc {
  display: block;
  font-size: 12px;
  color: #909399;
}

.check-icon {
  position: absolute;
  top: 12px;
  right: 12px;
  color: var(--el-color-primary);
}

.role-section {
  margin-bottom: 8px;
}

.settings-section {
  margin-bottom: 8px;
}

.setting-hint {
  font-size: 12px;
  color: #909399;
  margin: 8px 0 0;
}

.actions-section {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 8px;
}

/* 响应式 */
@media (max-width: 768px) {
  .create-room-view {
    padding: 12px;
  }
  
  .create-room-container {
    padding: 16px;
  }
  
  .participation-options {
    grid-template-columns: 1fr;
  }
  
  .game-card {
    flex-direction: column;
    text-align: center;
  }
}
</style>
