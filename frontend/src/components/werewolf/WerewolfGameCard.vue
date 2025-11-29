<template>
  <div class="werewolf-game-card">
    <!-- 卡片边框动画 -->
    <div class="card-border-anim"></div>
    
    <!-- 卡片内容 -->
    <div class="card-inner">
      <!-- 游戏封面图 -->
      <div class="game-card__cover">
        <img
          :src="coverImage"
          :alt="game.name"
          class="game-card__image"
        />
        <div class="cover-overlay">
          <div class="cover-gradient"></div>
          <div class="cover-scanline"></div>
        </div>
        <div class="game-card__badge">
          <span v-if="game.is_available" class="badge badge--available">
            <span class="badge-dot"></span>
            AVAILABLE
          </span>
          <span v-else class="badge badge--coming">
            COMING SOON
          </span>
        </div>
      </div>

      <!-- 游戏信息 -->
      <div class="game-card__content">
        <div class="content-header">
          <h2 class="game-card__title">{{ game.name }}</h2>
          <p class="game-card__subtitle">
            <span class="cyber-bracket">[</span>
            {{ gameSubtitle }}
            <span class="cyber-bracket">]</span>
          </p>
        </div>

        <!-- 角色配置（狼人杀） -->
        <div v-if="game.slug === 'werewolf'" class="game-card__roles">
          <div class="roles-grid">
            <div class="role-item role-item--werewolf">
              <span class="role-icon">🐺</span>
              <span class="role-name">狼人</span>
              <span class="role-count">×3</span>
            </div>
            <div class="role-item role-item--villager">
              <span class="role-icon">👤</span>
              <span class="role-name">村民</span>
              <span class="role-count">×4</span>
            </div>
            <div class="role-item role-item--seer">
              <span class="role-icon">🔮</span>
              <span class="role-name">预言家</span>
              <span class="role-count">×1</span>
            </div>
            <div class="role-item role-item--witch">
              <span class="role-icon">🧪</span>
              <span class="role-name">女巫</span>
              <span class="role-count">×1</span>
            </div>
            <div class="role-item role-item--hunter">
              <span class="role-icon">🏹</span>
              <span class="role-name">猎人</span>
              <span class="role-count">×1</span>
            </div>
          </div>
        </div>

        <!-- 游戏描述（其他游戏） -->
        <div v-else class="game-card__description">
          <p>{{ game.description }}</p>
        </div>

        <!-- 操作按钮 -->
        <div class="game-card__actions">
          <button
            v-if="game.is_available"
            class="cyber-btn cyber-btn--primary"
            @click="handleStartGame"
          >
            <span class="btn-bg"></span>
            <span class="btn-content">
              <span class="btn-icon">▶</span>
              <span class="btn-text">开始游戏</span>
            </span>
            <span class="btn-glitch"></span>
          </button>
          <button v-else class="cyber-btn cyber-btn--disabled" disabled>
            <span class="btn-content">即将推出</span>
          </button>
        </div>
      </div>
    </div>
    
    <!-- 角落装饰 -->
    <div class="corner-deco corner-tl"></div>
    <div class="corner-deco corner-tr"></div>
    <div class="corner-deco corner-bl"></div>
    <div class="corner-deco corner-br"></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  game: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['start-game'])

const router = useRouter()

// 封面图片 - 根据游戏类型选择
const coverImage = computed(() => {
  const covers = {
    'werewolf': new URL('@/assets/images/werewolf/werewolf-across.jpeg', import.meta.url).href,
    'crime-scene': new URL('@/assets/images/crimeScene/crime_scene.jpeg', import.meta.url).href
  }
  return covers[props.game.slug] || covers['werewolf']
})

// 游戏副标题
const gameSubtitle = computed(() => {
  if (props.game.slug === 'werewolf') {
    return `标准10人局 · 约${props.game.avg_duration_minutes}分钟`
  }
  return `${props.game.min_players}-${props.game.max_players}人 · 约${props.game.avg_duration_minutes}分钟`
})

// 开始游戏
const handleStartGame = () => {
  emit('start-game', props.game)
  router.push('/room/create')
}
</script>

<style scoped>
.werewolf-game-card {
  position: relative;
  max-width: 700px;
  margin: 0 auto;
  background: rgba(18, 18, 26, 0.95);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

/* ==================== Border Animation ==================== */
.card-border-anim {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border: 2px solid transparent;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent), var(--color-secondary), var(--color-primary)) border-box;
  -webkit-mask: linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0);
  mask: linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
  background-size: 300% 300%;
  animation: borderFlow 6s linear infinite;
}

@keyframes borderFlow {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

/* ==================== Corner Decorations ==================== */
.corner-deco {
  position: absolute;
  width: 20px;
  height: 20px;
  pointer-events: none;
}

.corner-deco::before,
.corner-deco::after {
  content: '';
  position: absolute;
  background: var(--color-primary);
}

.corner-tl { top: 8px; left: 8px; }
.corner-tl::before { top: 0; left: 0; width: 100%; height: 2px; }
.corner-tl::after { top: 0; left: 0; width: 2px; height: 100%; }

.corner-tr { top: 8px; right: 8px; }
.corner-tr::before { top: 0; right: 0; width: 100%; height: 2px; }
.corner-tr::after { top: 0; right: 0; width: 2px; height: 100%; }

.corner-bl { bottom: 8px; left: 8px; }
.corner-bl::before { bottom: 0; left: 0; width: 100%; height: 2px; }
.corner-bl::after { bottom: 0; left: 0; width: 2px; height: 100%; }

.corner-br { bottom: 8px; right: 8px; }
.corner-br::before { bottom: 0; right: 0; width: 100%; height: 2px; }
.corner-br::after { bottom: 0; right: 0; width: 2px; height: 100%; }

/* ==================== Card Inner ==================== */
.card-inner {
  position: relative;
  z-index: 1;
}

/* ==================== Cover ==================== */
.game-card__cover {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
}

.game-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s ease;
}

.werewolf-game-card:hover .game-card__image {
  transform: scale(1.05);
}

.cover-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.cover-gradient {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(180deg, transparent 60%, rgba(10, 10, 15, 0.9) 100%);
}

.cover-scanline {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, 0.1) 2px,
    rgba(0, 0, 0, 0.1) 4px
  );
  opacity: 0.3;
}

.game-card__badge {
  position: absolute;
  top: 20px;
  right: 20px;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.badge--available {
  background: rgba(16, 185, 129, 0.2);
  border: 1px solid var(--color-success);
  color: var(--color-success);
  text-shadow: 0 0 10px var(--color-success);
}

.badge-dot {
  width: 8px;
  height: 8px;
  background: var(--color-success);
  border-radius: 50%;
  animation: pulse 2s infinite;
  box-shadow: 0 0 10px var(--color-success);
}

.badge--coming {
  background: rgba(107, 114, 128, 0.3);
  border: 1px solid var(--color-text-muted);
  color: var(--color-text-secondary);
}

/* ==================== Content ==================== */
.game-card__content {
  padding: 20px;
}

.content-header {
  text-align: center;
  margin-bottom: 16px;
}

.game-tag {
  display: inline-block;
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
  color: var(--color-primary);
  letter-spacing: 0.2em;
  margin-bottom: 8px;
  text-shadow: var(--glow-primary);
}

.game-card__title {
  font-size: 1.8rem;
  font-weight: bold;
  margin: 0 0 8px 0;
  background: linear-gradient(135deg, var(--color-text-primary), var(--color-primary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.game-card__subtitle {
  font-size: 1.1rem;
  color: var(--color-text-secondary);
  margin: 0;
}

.cyber-bracket {
  color: var(--color-accent);
}

/* ==================== Roles ==================== */
.game-card__roles {
  margin-bottom: 16px;
}

.roles-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.roles-label {
  font-size: 0.875rem;
  color: var(--color-text-muted);
  font-family: 'Courier New', monospace;
  letter-spacing: 0.1em;
  white-space: nowrap;
}

.roles-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, var(--color-border-base), transparent);
}

.roles-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
}

.role-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  transition: all 0.3s;
}

.role-item:hover {
  transform: translateY(-2px);
}

.role-item--werewolf { border-color: rgba(239, 68, 68, 0.5); }
.role-item--werewolf:hover { background: rgba(239, 68, 68, 0.1); box-shadow: 0 0 15px rgba(239, 68, 68, 0.3); }

.role-item--villager { border-color: rgba(34, 197, 94, 0.5); }
.role-item--villager:hover { background: rgba(34, 197, 94, 0.1); box-shadow: 0 0 15px rgba(34, 197, 94, 0.3); }

.role-item--seer { border-color: rgba(59, 130, 246, 0.5); }
.role-item--seer:hover { background: rgba(59, 130, 246, 0.1); box-shadow: 0 0 15px rgba(59, 130, 246, 0.3); }

.role-item--witch { border-color: rgba(168, 85, 247, 0.5); }
.role-item--witch:hover { background: rgba(168, 85, 247, 0.1); box-shadow: 0 0 15px rgba(168, 85, 247, 0.3); }

.role-item--hunter { border-color: rgba(249, 115, 22, 0.5); }
.role-item--hunter:hover { background: rgba(249, 115, 22, 0.1); box-shadow: 0 0 15px rgba(249, 115, 22, 0.3); }

.role-icon {
  font-size: 1.25rem;
}

.role-name {
  font-size: 0.9rem;
  color: var(--color-text-primary);
}

.role-count {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  font-family: 'Courier New', monospace;
}

/* ==================== Description ==================== */
.game-card__description {
  margin-bottom: 16px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: var(--radius-md);
  border: 1px solid rgba(0, 240, 255, 0.1);
}

.game-card__description p {
  margin: 0;
  font-size: 0.95rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
  text-align: center;
}

/* ==================== Actions ==================== */
.game-card__actions {
  display: flex;
  justify-content: center;
  gap: 16px;
}

.cyber-btn {
  position: relative;
  padding: 14px 32px;
  font-size: 1rem;
  font-weight: 600;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  overflow: hidden;
  transition: all 0.3s;
}

.cyber-btn .btn-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  transition: all 0.3s;
}

.cyber-btn .btn-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.cyber-btn .btn-icon {
  font-size: 0.9rem;
}

/* Primary Button */
.cyber-btn--primary {
  background: transparent;
  color: var(--color-bg-primary);
}

.cyber-btn--primary .btn-bg {
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
}

.cyber-btn--primary:hover {
  transform: translateY(-2px);
  box-shadow: var(--neon-box-primary);
}

.cyber-btn--primary:hover .btn-bg {
  filter: brightness(1.2);
}

/* Secondary Button */
.cyber-btn--secondary {
  background: transparent;
  color: var(--color-primary);
  border: 1px solid var(--color-primary);
}

.cyber-btn--secondary .btn-bg {
  background: rgba(0, 240, 255, 0.05);
}

.cyber-btn--secondary:hover {
  transform: translateY(-2px);
  box-shadow: var(--neon-box-primary);
  color: var(--color-text-primary);
}

.cyber-btn--secondary:hover .btn-bg {
  background: rgba(0, 240, 255, 0.15);
}

/* Disabled Button */
.cyber-btn--disabled {
  background: rgba(107, 114, 128, 0.2);
  color: var(--color-text-muted);
  border: 1px solid var(--color-border-base);
  cursor: not-allowed;
}

/* ==================== Responsive ==================== */
@media (max-width: 640px) {
  .game-card__cover {
    height: 140px;
  }

  .game-card__content {
    padding: 16px;
  }

  .game-card__title {
    font-size: 1.5rem;
  }

  .roles-grid {
    gap: 6px;
  }

  .role-item {
    padding: 6px 10px;
    font-size: 0.8rem;
  }

  .cyber-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
