<template>
  <div class="create-room-view">
    <!-- 背景装饰 -->
    <div class="cyber-background">
      <div class="grid-pattern"></div>
    </div>

    <div class="page-header">
      <button class="back-btn" @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        <span>返回</span>
      </button>
      <h1 class="page-title">
        <span class="title-tag">&lt;</span>
        开始游戏
        <span class="title-tag">/&gt;</span>
      </h1>
    </div>
    
    <div class="create-room-container">
      <!-- 卡片边框 -->
      <div class="container-border"></div>
      
      <div class="game-info-section">
        <div class="game-card">
          <div class="game-cover-wrapper">
            <img 
              src="@/assets/images/werewolf/werewolf-across.jpeg" 
              alt="狼人杀"
              class="game-cover"
              @error="handleImageError"
            />
            <div class="cover-overlay"></div>
          </div>
          <div class="game-details">
            <span class="game-badge">WEREWOLF</span>
            <h2 class="game-name">狼人杀</h2>
            <p class="game-desc">
              <span class="desc-item">标准10人局</span>
              <span class="desc-divider">|</span>
              <span class="desc-item">3狼人</span>
              <span class="desc-divider">|</span>
              <span class="desc-item">4村民</span>
              <span class="desc-divider">|</span>
              <span class="desc-item">预言家</span>
              <span class="desc-divider">|</span>
              <span class="desc-item">女巫</span>
              <span class="desc-divider">|</span>
              <span class="desc-item">猎人</span>
            </p>
          </div>
        </div>
      </div>
      
      <div class="cyber-divider">
        <span class="divider-line"></span>
        <span class="divider-dot"></span>
        <span class="divider-line"></span>
      </div>
      
      <!-- 参与方式选择 -->
      <div class="participation-section">
        <h3 class="section-title">
          <span class="section-icon">👤</span>
          选择参与方式
        </h3>
        <div class="participation-options">
          <div 
            class="option-card" 
            :class="{ active: participationType === 'player' }"
            @click="participationType = 'player'"
          >
            <div class="option-glow"></div>
            <el-icon class="option-icon" :size="40"><User /></el-icon>
            <div class="option-info">
              <span class="option-name">玩家模式</span>
              <span class="option-desc">加入游戏，扮演一个角色参与游戏</span>
            </div>
            <div v-if="participationType === 'player'" class="check-indicator">
              <el-icon><Check /></el-icon>
            </div>
          </div>
          <div 
            class="option-card" 
            :class="{ active: participationType === 'spectator' }"
            @click="participationType = 'spectator'"
          >
            <div class="option-glow"></div>
            <el-icon class="option-icon" :size="40"><View /></el-icon>
            <div class="option-info">
              <span class="option-name">观战模式</span>
              <span class="option-desc">作为旁观者观看游戏，不参与投票等操作</span>
            </div>
            <div v-if="participationType === 'spectator'" class="check-indicator">
              <el-icon><Check /></el-icon>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 角色选择（仅玩家模式） -->
      <div v-if="participationType === 'player'" class="role-section">
        <div class="cyber-divider">
          <span class="divider-line"></span>
          <span class="divider-dot"></span>
          <span class="divider-line"></span>
        </div>
        <h3 class="section-title">
          <span class="section-icon">🎭</span>
          角色偏好（可选）
        </h3>
        <p class="section-desc">选择一个你想扮演的角色，系统将优先为你分配。如不选择则随机分配。</p>
        <RoleSelector 
          v-model="selectedRole" 
          game-type="werewolf"
        />
      </div>
      
      <div class="cyber-divider">
        <span class="divider-line"></span>
        <span class="divider-dot"></span>
        <span class="divider-line"></span>
      </div>
      
      <!-- 操作按钮 -->
      <div class="actions-section">
        <button class="cyber-btn cyber-btn--secondary" @click="goBack">
          <span class="btn-content">取消</span>
        </button>
        <button 
          class="cyber-btn cyber-btn--primary"
          :disabled="creating"
          @click="handleCreateRoom"
        >
          <span class="btn-bg"></span>
          <span v-if="creating" class="btn-content">
            <span class="loading-spinner"></span>
            创建中...
          </span>
          <span v-else class="btn-content">
            <span class="btn-icon">▶</span>
            开始游戏
          </span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, User, View, Check } from '@element-plus/icons-vue'
import { roomsApi } from '@/services/api'
import RoleSelector from '@/components/werewolf/RoleSelector.vue'

const router = useRouter()

// 状态
const participationType = ref('spectator') // 'player' | 'spectator'，默认观战模式
const selectedRole = ref(null)
const creating = ref(false)

// 返回大厅
function goBack() {
  router.push('/lobby')
}

// 图片加载失败处理
function handleImageError(e) {
  e.target.style.display = 'none'
}

// 创建房间
async function handleCreateRoom() {
  creating.value = true
  
  try {
    // 创建房间
    const roomData = {
      game_type_slug: 'werewolf',
      max_players: 10,
      min_players: 10
    }
    
    const room = await roomsApi.createRoom(roomData)
    const roomCode = room.code
    
    // 选择角色（如果是玩家模式）
    if (participationType.value === 'player') {
      await roomsApi.selectRole(
        roomCode, 
        selectedRole.value?.id || null,
        false
      )
    } else {
      // 观战模式
      await roomsApi.selectRole(roomCode, null, true)
    }
    
    // 添加 AI 玩家（固定10个，全AI模式）
    for (let i = 0; i < 10; i++) {
      try {
        await roomsApi.addAIAgent(roomCode)
      } catch (err) {
        console.warn(`添加第 ${i + 1} 个 AI 失败:`, err)
      }
    }
    
    ElMessage.success('房间创建成功')
    
    // 跳转到房间等待页面
    router.push(`/room/${roomCode}`)
  } catch (err) {
    console.error('创建房间失败:', err)
    ElMessage.error(err.response?.data?.detail || '创建房间失败，请重试')
  } finally {
    creating.value = false
  }
}
</script>

<style scoped>
.create-room-view {
  min-height: 100vh;
  background: var(--color-bg-primary);
  padding: 20px;
  position: relative;
}

/* ==================== Background ==================== */
.cyber-background {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 0;
}

.grid-pattern {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    linear-gradient(rgba(0, 240, 255, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 240, 255, 0.02) 1px, transparent 1px);
  background-size: 40px 40px;
}

/* ==================== Header ==================== */
.page-header {
  max-width: 800px;
  margin: 0 auto 24px;
  display: flex;
  align-items: center;
  gap: 20px;
  position: relative;
  z-index: 1;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: var(--radius-sm);
  color: var(--color-primary);
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.3s;
}

.back-btn:hover {
  background: rgba(0, 240, 255, 0.1);
  border-color: var(--color-primary);
  box-shadow: var(--neon-box-primary);
}

.page-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.title-tag {
  color: var(--color-primary);
  font-family: 'Courier New', monospace;
}

/* ==================== Container ==================== */
.create-room-container {
  max-width: 800px;
  margin: 0 auto;
  background: rgba(18, 18, 26, 0.95);
  border-radius: var(--radius-lg);
  padding: 32px;
  position: relative;
  z-index: 1;
}

.container-border {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: var(--radius-lg);
  pointer-events: none;
}

/* ==================== Cyber Divider ==================== */
.cyber-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 24px 0;
}

.divider-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-border-base), transparent);
}

.divider-dot {
  width: 6px;
  height: 6px;
  background: var(--color-primary);
  border-radius: 50%;
  box-shadow: 0 0 10px var(--color-primary);
}

/* ==================== Game Info ==================== */
.game-card {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 240, 255, 0.15);
  border-radius: var(--radius-md);
}

.game-cover-wrapper {
  position: relative;
  width: 100px;
  height: 100px;
  border-radius: var(--radius-md);
  overflow: hidden;
}

.game-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(0, 240, 255, 0.1), transparent);
}

.game-details {
  flex: 1;
}

.game-badge {
  display: inline-block;
  padding: 4px 12px;
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-sm);
  color: var(--color-primary);
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  margin-bottom: 8px;
  text-shadow: var(--glow-primary);
}

.game-name {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 8px;
}

.game-desc {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.desc-divider {
  color: var(--color-text-muted);
}

/* ==================== Sections ==================== */
.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 16px;
}

.section-icon {
  font-size: 1.25rem;
}

.section-desc {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin: 0 0 20px;
}

/* ==================== Participation Options ==================== */
.participation-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.option-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 16px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 240, 255, 0.15);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.3s;
  overflow: hidden;
}

.option-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
  background: radial-gradient(ellipse, rgba(0, 240, 255, 0.1), transparent 70%);
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}

.option-card:hover {
  border-color: rgba(0, 240, 255, 0.4);
  transform: translateY(-2px);
}

.option-card:hover .option-glow {
  opacity: 1;
}

.option-card.active {
  border-color: var(--color-primary);
  background: rgba(0, 240, 255, 0.05);
  box-shadow: var(--neon-box-primary);
}

.option-icon {
  color: var(--color-text-muted);
  margin-bottom: 16px;
  transition: color 0.3s;
}

.option-card.active .option-icon {
  color: var(--color-primary);
}

.option-info {
  text-align: center;
  position: relative;
  z-index: 1;
}

.option-name {
  display: block;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 8px;
}

.option-desc {
  display: block;
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.check-indicator {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  border-radius: 50%;
  color: var(--color-bg-primary);
}

/* ==================== Settings ==================== */
.setting-item {
  padding: 16px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: var(--radius-md);
}

.setting-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.label-text {
  font-size: 0.95rem;
  color: var(--color-text-primary);
}

.label-value {
  font-family: 'Courier New', monospace;
  color: var(--color-primary);
  text-shadow: var(--glow-primary);
}

.cyber-slider :deep(.el-slider__runway) {
  background: rgba(0, 240, 255, 0.1);
}

.cyber-slider :deep(.el-slider__bar) {
  background: linear-gradient(90deg, var(--color-primary), var(--color-accent));
}

.cyber-slider :deep(.el-slider__button) {
  border-color: var(--color-primary);
  background: var(--color-bg-primary);
}

.setting-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin: 16px 0 0;
}

.hint-icon {
  font-size: 1rem;
}

/* ==================== Actions ==================== */
.actions-section {
  display: flex;
  justify-content: flex-end;
  gap: 16px;
}

.cyber-btn {
  position: relative;
  padding: 14px 28px;
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

.cyber-btn--primary {
  background: transparent;
  color: var(--color-bg-primary);
}

.cyber-btn--primary .btn-bg {
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
}

.cyber-btn--primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: var(--neon-box-primary);
}

.cyber-btn--primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.cyber-btn--secondary {
  background: rgba(0, 240, 255, 0.05);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border-base);
}

.cyber-btn--secondary:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ==================== Responsive ==================== */
@media (max-width: 768px) {
  .create-room-view {
    padding: 12px;
  }
  
  .create-room-container {
    padding: 20px;
  }
  
  .participation-options {
    grid-template-columns: 1fr;
  }
  
  .game-card {
    flex-direction: column;
    text-align: center;
  }
  
  .game-desc {
    justify-content: center;
  }

  .actions-section {
    flex-direction: column;
  }

  .cyber-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
