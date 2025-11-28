<template>
  <el-card class="werewolf-game-card" shadow="hover">
    <!-- 游戏封面图 -->
    <div class="game-card__cover">
      <img
        :src="coverImage"
        :alt="game.name"
        class="game-card__image"
      />
      <div class="game-card__overlay">
        <el-tag v-if="game.is_available" type="success" size="large">
          可游玩
        </el-tag>
        <el-tag v-else type="info" size="large">
          即将推出
        </el-tag>
      </div>
    </div>

    <!-- 游戏信息 -->
    <div class="game-card__content">
      <h2 class="game-card__title">{{ game.name }}</h2>
      <p class="game-card__subtitle">标准10人局</p>

      <!-- 角色配置 -->
      <div class="game-card__roles">
        <span class="role-tag role-tag--werewolf">3狼人</span>
        <span class="role-tag role-tag--villager">4村民</span>
        <span class="role-tag role-tag--seer">预言家</span>
        <span class="role-tag role-tag--witch">女巫</span>
        <span class="role-tag role-tag--hunter">猎人</span>
      </div>

      <!-- 游戏描述 -->
      <p class="game-card__description">{{ game.description }}</p>

      <!-- 游戏信息 -->
      <div class="game-card__meta">
        <div class="meta-item">
          <el-icon><User /></el-icon>
          <span>{{ game.min_players }}-{{ game.max_players }}人</span>
        </div>
        <div class="meta-item">
          <el-icon><Clock /></el-icon>
          <span>约{{ game.avg_duration_minutes }}分钟</span>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="game-card__actions">
        <el-button
          v-if="game.is_available"
          type="primary"
          size="large"
          @click="handleCreateRoom"
        >
          创建房间
        </el-button>
        <el-button
          v-if="game.is_available"
          size="large"
          @click="handleViewRules"
        >
          查看规则
        </el-button>
        <el-button v-else disabled size="large">
          即将推出
        </el-button>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { User, Clock } from '@element-plus/icons-vue'

const props = defineProps({
  game: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['create-room', 'view-rules'])

const router = useRouter()

// 封面图片
const coverImage = computed(() => {
  return new URL('@/assets/images/werewolf/werewolf-across.jpeg', import.meta.url).href
})

// 创建房间
const handleCreateRoom = () => {
  emit('create-room', props.game)
  router.push('/room/create')
}

// 查看规则
const handleViewRules = () => {
  emit('view-rules', props.game)
  router.push(`/games/${props.game.slug}`)
}
</script>

<style scoped>
.werewolf-game-card {
  max-width: 600px;
  margin: 0 auto;
  border-radius: 16px;
  overflow: hidden;
}

.game-card__cover {
  position: relative;
  width: 100%;
  height: 300px;
  overflow: hidden;
}

.game-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.game-card__overlay {
  position: absolute;
  top: 16px;
  right: 16px;
}

.game-card__content {
  padding: 24px;
  text-align: center;
}

.game-card__title {
  font-size: 32px;
  font-weight: bold;
  margin: 0 0 8px 0;
  color: #303133;
}

.game-card__subtitle {
  font-size: 18px;
  color: #909399;
  margin: 0 0 20px 0;
}

.game-card__roles {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin-bottom: 20px;
}

.role-tag {
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 14px;
  font-weight: 500;
}

.role-tag--werewolf {
  background-color: #f56c6c;
  color: #fff;
}

.role-tag--villager {
  background-color: #67c23a;
  color: #fff;
}

.role-tag--seer {
  background-color: #409eff;
  color: #fff;
}

.role-tag--witch {
  background-color: #9b59b6;
  color: #fff;
}

.role-tag--hunter {
  background-color: #e67e22;
  color: #fff;
}

.game-card__description {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
  margin-bottom: 20px;
}

.game-card__meta {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-bottom: 24px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #909399;
  font-size: 14px;
}

.game-card__actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.game-card__actions .el-button {
  min-width: 120px;
}
</style>
