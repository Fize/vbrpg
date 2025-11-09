<template>
  <el-card class="stats-display">
    <template #header>
      <div class="card-header">
        <h3>游戏统计</h3>
      </div>
    </template>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="stats" class="stats-grid">
      <div class="stat-item">
        <div class="stat-icon">
          <el-icon><Trophy /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.wins }}</div>
          <div class="stat-label">胜利场次</div>
        </div>
      </div>

      <div class="stat-item">
        <div class="stat-icon">
          <el-icon><Memo /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.total_games }}</div>
          <div class="stat-label">总游戏场次</div>
        </div>
      </div>

      <div class="stat-item">
        <div class="stat-icon">
          <el-icon><TrendCharts /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.win_rate }}%</div>
          <div class="stat-label">胜率</div>
        </div>
      </div>

      <div class="stat-item">
        <div class="stat-icon">
          <el-icon><Timer /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ formatPlayTime(stats.total_play_time_minutes) }}</div>
          <div class="stat-label">游戏时长</div>
        </div>
      </div>

      <div v-if="stats.favorite_game" class="stat-item full-width">
        <div class="stat-icon">
          <el-icon><Star /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.favorite_game }}</div>
          <div class="stat-label">最喜爱的游戏</div>
        </div>
      </div>
    </div>

    <el-empty v-else description="暂无统计数据" />
  </el-card>
</template>

<script setup>
import { Trophy, Memo, TrendCharts, Timer, Star } from '@element-plus/icons-vue'

defineProps({
  stats: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const formatPlayTime = (minutes) => {
  if (minutes < 60) {
    return `${minutes} 分钟`
  }
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return mins > 0 ? `${hours} 小时 ${mins} 分钟` : `${hours} 小时`
}
</script>

<style scoped>
.stats-display {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 20px;
}

.loading-container {
  padding: 20px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 24px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
  transition: transform 0.2s;
}

.stat-item:hover {
  transform: translateY(-2px);
}

.stat-item.full-width {
  grid-column: 1 / -1;
}

.stat-icon {
  font-size: 40px;
  color: #409eff;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 60px;
  background: white;
  border-radius: 50%;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  line-height: 1;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .stat-value {
    font-size: 24px;
  }
  
  .stat-icon {
    font-size: 32px;
    width: 50px;
    height: 50px;
  }
}
</style>
