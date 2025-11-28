<template>
  <div class="game-details">
    <!-- Loading State -->
    <LoadingIndicator 
      v-if="loading" 
      text="加载游戏详情中..." 
      variant="primary"
      size="large"
    />

    <!-- Content -->
    <el-container v-else>
      <!-- Header -->
      <el-header class="details-header">
        <el-button 
          circle 
          @click="goBack"
          class="back-button"
        >
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <h1>{{ game?.name || '未知游戏' }}</h1>
      </el-header>

      <!-- Main Content -->
      <el-main class="details-main">
        <el-row :gutter="24" v-if="game">
          <!-- Left Column: Game Info -->
          <el-col :xs="24" :md="16">
            <el-card class="info-card">
              <template #header>
                <div class="card-header">
                  <h2>游戏简介</h2>
                  <el-tag 
                    :type="game.is_available ? 'success' : 'info'"
                    size="large"
                  >
                    {{ game.is_available ? '可游玩' : '即将推出' }}
                  </el-tag>
                </div>
              </template>

              <p class="description">{{ game.description }}</p>

              <el-divider />

              <div class="meta-info">
                <div class="meta-item">
                  <el-icon class="meta-icon"><User /></el-icon>
                  <div>
                    <div class="meta-label">玩家人数</div>
                    <div class="meta-value">{{ game.min_players }}-{{ game.max_players }} 人</div>
                  </div>
                </div>

                <div class="meta-item">
                  <el-icon class="meta-icon"><Clock /></el-icon>
                  <div>
                    <div class="meta-label">游戏时长</div>
                    <div class="meta-value">约 {{ game.avg_duration_minutes }} 分钟</div>
                  </div>
                </div>
              </div>

              <el-divider />

              <div class="rules-section">
                <h3>游戏规则</h3>
                <div class="rules-content" v-html="formattedRules"></div>
              </div>
            </el-card>
          </el-col>

          <!-- Right Column: Actions & Stats -->
          <el-col :xs="24" :md="8">
            <!-- Play Now Card -->
            <el-card class="action-card">
              <template #header>
                <h3>开始游戏</h3>
              </template>

              <el-button 
                type="primary" 
                size="large"
                :disabled="!game.is_available"
                @click="handlePlayNow"
                class="play-button"
              >
                <el-icon><VideoPlay /></el-icon>
                {{ game.is_available ? '立即开始' : '即将推出' }}
              </el-button>

              <p v-if="!game.is_available" class="coming-soon-text">
                这个游戏正在开发中，敬请期待！
              </p>
            </el-card>

            <!-- Game Stats Card (if available) -->
            <el-card v-if="game.is_available" class="stats-card">
              <template #header>
                <h3>游戏统计</h3>
              </template>

              <div class="stat-item">
                <span class="stat-label">总游戏场次</span>
                <span class="stat-value">-</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">在线玩家</span>
                <span class="stat-value">-</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">平均评分</span>
                <span class="stat-value">-</span>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  ArrowLeft, 
  User, 
  Clock, 
  VideoPlay,
  TrophyBase,
  Star
} from '@element-plus/icons-vue'
import { gamesApi } from '@/services/api'
import LoadingIndicator from '@/components/common/LoadingIndicator.vue'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const game = ref(null)

const formattedRules = computed(() => {
  if (!game.value?.rules_summary) return ''
  // Convert line breaks to paragraphs
  return game.value.rules_summary
    .split('\n')
    .filter(line => line.trim())
    .map(line => `<p>${line}</p>`)
    .join('')
})

const loadGameDetails = async () => {
  loading.value = true
  try {
    const slug = route.params.slug
    game.value = await gamesApi.getGameDetails(slug)
  } catch (error) {
    console.error('Failed to load game details:', error)
    ElMessage.error('加载游戏详情失败')
    router.push({ name: 'GameLibrary' })
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push({ name: 'GameLibrary' })
}

const handlePlayNow = () => {
  if (game.value?.is_available) {
    router.push({ 
      name: 'GameRoomConfig', 
      query: { gameType: game.value.slug } 
    })
  }
}

onMounted(async () => {
  await loadGameDetails()
})
</script>

<style scoped>
.game-details {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.details-header {
  position: relative;
  text-align: center;
  color: white;
  padding: 40px 20px;
  height: auto;
}

.back-button {
  position: absolute;
  left: 20px;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  transition: all 0.3s;
}

.back-button:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-50%) scale(1.1);
}

.details-header h1 {
  font-size: 42px;
  margin: 0;
  font-weight: bold;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
}

.details-main {
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  padding: 30px 20px 60px;
}

.info-card,
.action-card,
.stats-card {
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  font-size: 24px;
}

.description {
  font-size: 16px;
  line-height: 1.8;
  color: #606266;
  margin: 0;
}

.meta-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.meta-icon {
  font-size: 32px;
  color: #409eff;
}

.meta-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 4px;
}

.meta-value {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.rules-section h3 {
  font-size: 20px;
  margin-bottom: 16px;
  color: #303133;
}

.rules-content {
  font-size: 15px;
  line-height: 1.8;
  color: #606266;
}

.rules-content :deep(p) {
  margin: 12px 0;
}

.action-card h3,
.stats-card h3 {
  margin: 0;
  font-size: 18px;
}

.play-button {
  width: 100%;
  height: 50px;
  font-size: 18px;
  margin-bottom: 16px;
}

.coming-soon-text {
  text-align: center;
  color: #909399;
  font-size: 14px;
  margin: 0;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #ebeef5;
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-label {
  color: #606266;
  font-size: 14px;
}

.stat-value {
  color: #303133;
  font-weight: 600;
  font-size: 16px;
}

@media (max-width: 768px) {
  .details-header h1 {
    font-size: 32px;
  }

  .back-button {
    left: 10px;
  }

  .meta-info {
    grid-template-columns: 1fr;
  }
}
</style>
