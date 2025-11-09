<template>
  <div class="game-library">
    <el-container>
      <el-header class="library-header">
        <h1>游戏大厅</h1>
        <p class="subtitle">选择一个游戏开始你的冒险</p>
        
        <!-- Filters -->
        <div class="filters">
          <el-radio-group v-model="filterAvailable" @change="loadGames">
            <el-radio-button :label="null">全部游戏</el-radio-button>
            <el-radio-button :label="true">可游玩</el-radio-button>
            <el-radio-button :label="false">即将推出</el-radio-button>
          </el-radio-group>
        </div>
      </el-header>

      <el-main>
        <!-- Loading State -->
        <LoadingIndicator 
          v-if="loading" 
          text="加载游戏列表中..." 
          variant="primary"
          size="large"
        />

        <!-- Game Grid -->
        <el-row v-else-if="filteredGames.length > 0" :gutter="24" class="game-grid">
          <el-col
            v-for="game in filteredGames"
            :key="game.slug"
            :xs="24"
            :sm="12"
            :md="8"
            :lg="6"
            class="game-col"
          >
            <GameCard :game="game" />
          </el-col>
        </el-row>

        <!-- Empty State -->
        <EmptyState
          v-else
          icon="Collection"
          title="暂无游戏"
          description="没有找到符合条件的游戏，请尝试调整筛选条件"
        />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { gamesApi } from '@/services/api'
import GameCard from '@/components/GameCard.vue'
import LoadingIndicator from '@/components/LoadingIndicator.vue'
import EmptyState from '@/components/EmptyState.vue'

const router = useRouter()

// State
const loading = ref(false)
const games = ref([
  {
    slug: 'crime-scene',
    name: '犯罪现场',
    description: '协作推理游戏，找出真相并制服凶手',
    min_players: 4,
    max_players: 6,
    avg_duration_minutes: 45,
    is_available: true,
    thumbnail: null
  }
])
const filterAvailable = ref(null)
const showConfigDialog = ref(false)
const selectedGame = ref(null)

// Computed
const filteredGames = computed(() => {
  if (filterAvailable.value === null) {
    return games.value
  }
  return games.value.filter(game => game.is_available === filterAvailable.value)
})

const loadGames = async () => {
  loading.value = true
  try {
    games.value = await gamesApi.getGames()
  } catch (error) {
    console.error('Failed to load games:', error)
    ElMessage.error('加载游戏列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadGames()
})
</script>

<style scoped>
.game-library {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.library-header {
  text-align: center;
  color: white;
  padding: 40px 20px 30px;
  height: auto;
}

.library-header h1 {
  font-size: 48px;
  margin: 0 0 10px 0;
  font-weight: bold;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
}

.subtitle {
  font-size: 18px;
  margin: 0 0 24px 0;
  opacity: 0.9;
}

.filters {
  margin-top: 20px;
}

.el-main {
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
  padding: 30px 20px;
}

.game-grid {
  display: flex;
  flex-wrap: wrap;
}

.game-col {
  display: flex;
  margin-bottom: 24px;
}

@media (max-width: 768px) {
  .game-library {
    padding: 16px;
  }
  
  .library-header {
    padding: 30px 16px 20px;
  }
  
  .library-header h1 {
    font-size: 36px;
  }
  
  .subtitle {
    font-size: 16px;
  }
}

@media (max-width: 480px) {
  .game-library {
    padding: 12px;
  }
  
  .library-header {
    padding: 24px 12px 16px;
  }
  
  .library-header h1 {
    font-size: 28px;
  }
  
  .subtitle {
    font-size: 14px;
  }
}
</style>
