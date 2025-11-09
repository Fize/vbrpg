<template>
  <el-card 
    class="game-card" 
    :class="{ 'game-card--unavailable': !game.is_available }"
    shadow="hover"
    @click="handleClick"
  >
    <template #header>
      <div class="game-card__header">
        <h3 class="game-card__title">{{ game.name }}</h3>
        <el-tag 
          v-if="!game.is_available" 
          type="info" 
          size="small"
        >
          即将推出
        </el-tag>
        <el-tag 
          v-else 
          type="success" 
          size="small"
        >
          可游玩
        </el-tag>
      </div>
    </template>

    <div class="game-card__body">
      <p class="game-card__description">{{ game.description }}</p>
      
      <div class="game-card__meta">
        <div class="game-card__meta-item">
          <el-icon><User /></el-icon>
          <span>{{ game.min_players }}-{{ game.max_players }} 人</span>
        </div>
        
        <div class="game-card__meta-item">
          <el-icon><Clock /></el-icon>
          <span>约 {{ game.avg_duration_minutes }} 分钟</span>
        </div>
      </div>

      <div v-if="game.is_available" class="game-card__actions">
        <el-button type="primary" @click.stop="handlePlayNow">
          立即开始
        </el-button>
        <el-button @click.stop="handleViewDetails">
          查看详情
        </el-button>
      </div>
      
      <div v-else class="game-card__actions">
        <el-button disabled>即将推出</el-button>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { User, Clock } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  game: {
    type: Object,
    required: true
  }
})

const router = useRouter()

const handleClick = () => {
  if (props.game.is_available) {
    handleViewDetails()
  }
}

const handlePlayNow = () => {
  // Navigate to game configuration
  router.push({ 
    name: 'GameRoomConfig', 
    query: { gameType: props.game.slug } 
  })
}

const handleViewDetails = () => {
  // Navigate to game details page
  router.push({ 
    name: 'GameDetails', 
    params: { slug: props.game.slug } 
  })
}
</script>

<style scoped>
.game-card {
  cursor: pointer;
  transition: transform 0.2s;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.game-card:hover {
  transform: translateY(-4px);
}

.game-card--unavailable {
  opacity: 0.8;
  cursor: default;
}

.game-card--unavailable:hover {
  transform: none;
}

.game-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.game-card__title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  flex: 1;
}

.game-card__body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
}

.game-card__description {
  color: #666;
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
  flex: 1;
}

.game-card__meta {
  display: flex;
  gap: 16px;
  padding: 12px 0;
  border-top: 1px solid #eee;
  border-bottom: 1px solid #eee;
}

.game-card__meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #666;
}

.game-card__meta-item .el-icon {
  font-size: 16px;
}

.game-card__actions {
  display: flex;
  gap: 8px;
}

.game-card__actions .el-button {
  flex: 1;
}
</style>
