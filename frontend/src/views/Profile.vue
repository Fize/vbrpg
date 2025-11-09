<template>
  <div class="profile-view">
    <el-page-header @back="handleBack" class="page-header">
      <template #content>
        <span class="page-title">个人资料</span>
      </template>
    </el-page-header>

    <div class="profile-content">
      <!-- 玩家信息卡片 -->
      <el-card class="player-info-card">
        <div class="player-info">
          <el-avatar :size="80" class="player-avatar">
            {{ playerInitial }}
          </el-avatar>
          <div class="player-details">
            <h2>{{ username }}</h2>
            <el-tag v-if="isGuest" type="warning" size="small">访客模式</el-tag>
            <el-tag v-else type="success" size="small">永久账户</el-tag>
            <p class="last-active">
              最后活跃: {{ lastActiveText }}
            </p>
          </div>
        </div>
      </el-card>

      <!-- 访客账户升级提示 -->
      <el-card v-if="isGuest && !showUpgradeForm" class="upgrade-prompt">
        <div class="prompt-content">
          <el-icon :size="48" color="#e6a23c"><Warning /></el-icon>
          <div class="prompt-text">
            <h3>升级您的账户</h3>
            <p>访客账户将在 30 天后过期，升级为永久账户以保存您的游戏数据。</p>
          </div>
          <el-button type="primary" @click="showUpgradeForm = true">
            立即升级
          </el-button>
        </div>
      </el-card>

      <!-- 账户升级表单 -->
      <AccountUpgrade
        v-if="isGuest && showUpgradeForm"
        :current-username="username"
        :loading="upgrading"
        @upgrade="handleUpgrade"
        @cancel="showUpgradeForm = false"
      />

      <!-- 游戏统计 -->
      <div class="stats-section">
        <h3>游戏统计</h3>
        
        <!-- Loading State -->
        <LoadingIndicator 
          v-if="statsLoading" 
          text="加载统计数据中..." 
          size="medium"
        />
        
        <!-- Stats Display -->
        <StatsDisplay v-else :stats="stats" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Warning } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { playersApi } from '@/services/api'
import AccountUpgrade from '@/components/AccountUpgrade.vue'
import StatsDisplay from '@/components/StatsDisplay.vue'
import LoadingIndicator from '@/components/LoadingIndicator.vue'

const router = useRouter()
const authStore = useAuthStore()

const showUpgradeForm = ref(false)
const upgrading = ref(false)
const stats = ref(null)
const statsLoading = ref(false)

const isGuest = computed(() => authStore.isGuest)
const username = computed(() => authStore.username)
const playerId = computed(() => authStore.playerId)

const playerInitial = computed(() => {
  const name = username.value || '?'
  return name.charAt(0).toUpperCase()
})

const lastActiveText = computed(() => {
  if (!authStore.currentPlayer?.last_active_at) {
    return '从未'
  }
  const lastActive = new Date(authStore.currentPlayer.last_active_at)
  const now = new Date()
  const diff = now - lastActive
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  if (hours < 24) return `${hours} 小时前`
  return `${days} 天前`
})

const handleBack = () => {
  router.back()
}

const handleUpgrade = async (newUsername) => {
  upgrading.value = true
  try {
    await playersApi.upgradeAccount(newUsername)
    
    // 更新本地状态
    authStore.updateUsername(newUsername)
    
    // 重新加载玩家信息
    const player = await playersApi.getCurrentPlayer()
    authStore.setPlayer(player)
    
    ElMessage.success('账户升级成功！')
    showUpgradeForm.value = false
  } catch (error) {
    console.error('Upgrade failed:', error)
    ElMessage.error(error.response?.data?.detail || '升级失败，请稍后重试')
  } finally {
    upgrading.value = false
  }
}

const loadStats = async () => {
  statsLoading.value = true
  try {
    const data = await playersApi.getStats()
    stats.value = data
  } catch (error) {
    console.error('Failed to load stats:', error)
    ElMessage.error('加载统计数据失败')
  } finally {
    statsLoading.value = false
  }
}

onMounted(() => {
  loadStats()
})
</script>

<style scoped>
.profile-view {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: bold;
}

.profile-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.player-info-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.player-info-card :deep(.el-card__body) {
  padding: 32px;
}

.player-info {
  display: flex;
  align-items: center;
  gap: 24px;
}

.player-avatar {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  font-size: 32px;
  font-weight: bold;
  backdrop-filter: blur(10px);
}

.player-details h2 {
  margin: 0 0 8px 0;
  font-size: 28px;
  font-weight: bold;
}

.player-details .el-tag {
  margin-right: 8px;
}

.last-active {
  margin: 8px 0 0 0;
  opacity: 0.9;
  font-size: 14px;
}

.upgrade-prompt {
  border-left: 4px solid #e6a23c;
}

.prompt-content {
  display: flex;
  align-items: center;
  gap: 24px;
}

.prompt-text {
  flex: 1;
}

.prompt-text h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
  color: #303133;
}

.prompt-text p {
  margin: 0;
  color: #606266;
  font-size: 14px;
}

.stats-section h3 {
  margin: 0 0 16px 0;
  font-size: 20px;
  color: #303133;
}

@media (max-width: 768px) {
  .profile-view {
    padding: 12px;
  }

  .player-info {
    flex-direction: column;
    text-align: center;
  }

  .prompt-content {
    flex-direction: column;
    text-align: center;
  }
}
</style>
