<template>
  <el-card 
    class="game-card" 
    :class="{ 'game-card--unavailable': !game.is_available }"
    shadow="hover"
    @click="handleClick"
  >
    <!-- Game Thumbnail -->
    <div class="game-card__thumbnail">
      <img 
        v-if="gameThumbnail" 
        :src="gameThumbnail" 
        :alt="game.name"
        class="game-card__image"
      />
      <div v-else class="game-card__placeholder">
        <el-icon size="48"><Picture /></el-icon>
      </div>
      <div class="game-card__overlay">
        <el-tag 
          v-if="!game.is_available" 
          type="info" 
          size="large"
        >
          即将推出
        </el-tag>
        <el-tag 
          v-else 
          type="success" 
          size="large"
        >
          可游玩
        </el-tag>
      </div>
    </div>

    <template #header>
      <div class="game-card__header">
        <h3 class="game-card__title">{{ game.name }}</h3>
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
import { computed } from 'vue'
import { User, Clock, Picture } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  game: {
    type: Object,
    required: true
  }
})

const router = useRouter()

// Game thumbnail mapping
const gameThumbnails = {
  'crime-scene': new URL('@/assets/images/crimeScene/crime_scene.jpeg', import.meta.url).href
}

const gameThumbnail = computed(() => {
  return gameThumbnails[props.game.slug] || props.game.thumbnail || null
})

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

.game-card__thumbnail {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: #f5f7fa;
  border-radius: 4px 4px 0 0;
}

.game-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

.game-card:hover .game-card__image {
  transform: scale(1.05);
}

.game-card__placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #c0c4cc;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
}

.game-card__overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 8px 12px;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.6), transparent);
  display: flex;
  gap: 8px;
  align-items: flex-end;
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
