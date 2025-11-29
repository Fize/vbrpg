<template>
  <div class="lobby-view">
    <!-- 赛博朋克背景元素 -->
    <div class="cyber-overlay">
      <div class="hex-grid"></div>
      <div class="glow-orbs">
        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>
      </div>
    </div>

    <!-- 加载状态 -->
    <LoadingIndicator
      v-if="isLoading"
      text="正在连接..."
      variant="primary"
      size="large"
    />

    <!-- 主要内容 -->
    <div v-else class="lobby-content">
      <!-- 游戏卡片列表 -->
      <div class="games-grid">
        <WerewolfGameCard
          v-for="game in sortedGames"
          :key="game.slug"
          :game="game"
          @start-game="handleStartGame"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { gamesApi } from '@/services/api'
import WerewolfGameCard from '@/components/werewolf/WerewolfGameCard.vue'
import LoadingIndicator from '@/components/common/LoadingIndicator.vue'

const router = useRouter()

// 状态
const isLoading = ref(false)
const games = ref([])

// 排序后的游戏列表（狼人杀优先）
const sortedGames = computed(() => {
  return [...games.value].sort((a, b) => {
    if (a.slug === 'werewolf') return -1
    if (b.slug === 'werewolf') return 1
    return 0
  })
})

// 加载游戏列表
const loadGames = async () => {
  isLoading.value = true
  try {
    games.value = await gamesApi.getGames()
  } catch (error) {
    console.error('Failed to load games:', error)
    ElMessage.error('加载游戏失败')
  } finally {
    isLoading.value = false
  }
}

// 开始游戏
const handleStartGame = (game) => {
  router.push('/room/create')
}

// 生命周期
onMounted(() => {
  loadGames()
})
</script>

<style scoped>
.lobby-view {
  min-height: 100vh;
  background: var(--color-bg-primary);
  padding: 0;
  position: relative;
  overflow-x: hidden;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

/* ==================== Cyber Overlay ==================== */
.cyber-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 0;
}

.hex-grid {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    radial-gradient(circle at 25% 25%, rgba(0, 240, 255, 0.03) 0%, transparent 50%),
    radial-gradient(circle at 75% 75%, rgba(168, 85, 247, 0.03) 0%, transparent 50%);
}

.glow-orbs {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.3;
  animation: float 20s ease-in-out infinite;
}

.orb-1 {
  width: 300px;
  height: 300px;
  background: var(--color-primary);
  top: -50px;
  left: -50px;
}

.orb-2 {
  width: 250px;
  height: 250px;
  background: var(--color-accent);
  bottom: -50px;
  right: -50px;
  animation-delay: -10s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(20px, -20px) scale(1.05); }
}

/* ==================== Content ==================== */
.lobby-content {
  flex: 1;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 20px;
  position: relative;
  z-index: 1;
  box-sizing: border-box;
}

.games-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 24px;
  width: 100%;
}

/* ==================== Responsive ==================== */
@media (max-width: 768px) {
  .lobby-content {
    padding: 20px 16px;
  }

  .games-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}
</style>
