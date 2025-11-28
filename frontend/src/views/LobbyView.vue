<template>
  <div class="lobby-view">
    <!-- 页面头部 -->
    <div class="lobby-header">
      <h1 class="lobby-title">VBRPG 游戏大厅</h1>
      <p class="lobby-subtitle">选择一个游戏开始你的冒险</p>
    </div>

    <!-- 加载状态 -->
    <LoadingIndicator
      v-if="isLoading"
      text="加载游戏列表..."
      variant="primary"
      size="large"
    />

    <!-- 主要内容 -->
    <div v-else class="lobby-content">
      <!-- 狼人杀游戏卡片 -->
      <div class="main-game-section">
        <WerewolfGameCard
          v-if="werewolfGame"
          :game="werewolfGame"
          @create-room="handleCreateRoom"
          @view-rules="handleViewRules"
        />
      </div>

      <!-- 其他游戏区域 -->
      <div class="other-games-section">
        <h3 class="section-title">其他游戏</h3>
        <div class="other-games-grid">
          <el-card
            v-for="game in otherGames"
            :key="game.slug"
            class="other-game-card"
            :class="{ 'other-game-card--disabled': !game.is_available }"
            shadow="hover"
          >
            <div class="other-game-content">
              <img
                v-if="getGameCover(game.slug)"
                :src="getGameCover(game.slug)"
                :alt="game.name"
                class="other-game-image"
              />
              <div v-else class="other-game-placeholder">
                <el-icon size="32"><Picture /></el-icon>
              </div>
              <div class="other-game-info">
                <h4 class="other-game-title">{{ game.name }}</h4>
                <el-tag v-if="!game.is_available" type="info" size="small">
                  即将推出
                </el-tag>
              </div>
            </div>
          </el-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Picture } from '@element-plus/icons-vue'
import { gamesApi } from '@/services/api'
import WerewolfGameCard from '@/components/werewolf/WerewolfGameCard.vue'
import LoadingIndicator from '@/components/common/LoadingIndicator.vue'

const router = useRouter()

// 状态
const isLoading = ref(false)
const games = ref([])

// 计算属性 - 狼人杀游戏
const werewolfGame = computed(() => {
  return games.value.find(game => game.slug === 'werewolf')
})

// 计算属性 - 其他游戏
const otherGames = computed(() => {
  return games.value.filter(game => game.slug !== 'werewolf')
})

// 获取游戏封面图
const getGameCover = (slug) => {
  const covers = {
    'crime-scene': new URL('@/assets/images/crimeScene/crime_scene.jpeg', import.meta.url).href
  }
  return covers[slug] || null
}

// 加载游戏列表
const loadGames = async () => {
  isLoading.value = true
  try {
    games.value = await gamesApi.getGames()
  } catch (error) {
    console.error('Failed to load games:', error)
    ElMessage.error('加载游戏列表失败')
  } finally {
    isLoading.value = false
  }
}

// 创建房间
const handleCreateRoom = (game) => {
  router.push('/room/create')
}

// 查看规则
const handleViewRules = (game) => {
  router.push(`/games/${game.slug}`)
}

// 生命周期
onMounted(() => {
  loadGames()
})
</script>

<style scoped>
.lobby-view {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  padding: 40px 20px;
}

.lobby-header {
  text-align: center;
  margin-bottom: 40px;
}

.lobby-title {
  font-size: 48px;
  font-weight: bold;
  color: #fff;
  margin: 0 0 12px 0;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, .5);
}

.lobby-subtitle {
  font-size: 18px;
  color: rgba(255, 255, 255, .7);
  margin: 0;
}

.lobby-content {
  max-width: 800px;
  margin: 0 auto;
}

.main-game-section {
  margin-bottom: 60px;
}

.other-games-section {
  padding: 0 20px;
}

.section-title {
  font-size: 20px;
  color: rgba(255, 255, 255, .8);
  margin: 0 0 20px 0;
  text-align: center;
}

.other-games-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.other-game-card {
  cursor: pointer;
  transition: transform .2s, opacity .2s;
}

.other-game-card--disabled {
  opacity: .6;
  cursor: not-allowed;
}

.other-game-card:not(.other-game-card--disabled):hover {
  transform: translateY(-4px);
}

.other-game-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.other-game-image {
  width: 100%;
  height: 120px;
  object-fit: cover;
  border-radius: 8px;
  margin-bottom: 12px;
}

.other-game-placeholder {
  width: 100%;
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f5f5f5;
  border-radius: 8px;
  margin-bottom: 12px;
  color: #909399;
}

.other-game-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.other-game-title {
  font-size: 16px;
  font-weight: 500;
  margin: 0;
  color: #303133;
}

@media (max-width: 768px) {
  .lobby-view {
    padding: 24px 16px;
  }

  .lobby-title {
    font-size: 32px;
  }

  .lobby-subtitle {
    font-size: 16px;
  }

  .other-games-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .lobby-title {
    font-size: 28px;
  }

  .other-games-grid {
    grid-template-columns: 1fr;
  }
}
</style>
