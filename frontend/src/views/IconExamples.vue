<!--
使用动画图标示例
展示如何在不同场景下使用图标库
-->

<template>
  <div class="icon-examples">
    <h1>动画图标使用示例</h1>
    
    <!-- 1. 基础用法 -->
    <section class="example-section">
      <h2>1. 基础用法</h2>
      <div class="icon-grid">
        <div class="icon-item">
          <DetectiveIcon :size="64" />
          <p>DetectiveIcon</p>
        </div>
        <div class="icon-item">
          <DiceIcon :size="64" />
          <p>DiceIcon</p>
        </div>
        <div class="icon-item">
          <ThinkingIcon :size="64" />
          <p>ThinkingIcon</p>
        </div>
        <div class="icon-item">
          <TrophyIcon :size="64" />
          <p>TrophyIcon</p>
        </div>
        <div class="icon-item">
          <ClueIcon :size="64" />
          <p>ClueIcon</p>
        </div>
        <div class="icon-item">
          <LocationIcon :size="64" />
          <p>LocationIcon</p>
        </div>
      </div>
    </section>
    
    <!-- 2. 自定义颜色 -->
    <section class="example-section">
      <h2>2. 自定义颜色</h2>
      <div class="icon-grid">
        <DetectiveIcon :size="72" color="#e74c3c" />
        <DiceIcon :size="72" color="#9b59b6" />
        <ThinkingIcon :size="72" color="#f39c12" dotColor="#e74c3c" />
        <TrophyIcon :size="72" color="#e74c3c" starColor="#3498db" />
        <ClueIcon :size="72" color="#2ecc71" sparkleColor="#e74c3c" />
        <LocationIcon :size="72" color="#9b59b6" />
      </div>
    </section>
    
    <!-- 3. 不同尺寸 -->
    <section class="example-section">
      <h2>3. 不同尺寸</h2>
      <div class="size-demo">
        <DetectiveIcon :size="24" />
        <DetectiveIcon :size="48" />
        <DetectiveIcon :size="72" />
        <DetectiveIcon :size="120" />
        <DetectiveIcon :size="200" />
      </div>
    </section>
    
    <!-- 4. 禁用动画 -->
    <section class="example-section">
      <h2>4. 禁用动画 (性能优化)</h2>
      <div class="icon-grid">
        <div class="icon-item">
          <ThinkingIcon :size="64" :animate="false" />
          <p>静态图标</p>
        </div>
        <div class="icon-item">
          <ThinkingIcon :size="64" :animate="true" />
          <p>动画图标</p>
        </div>
      </div>
    </section>
    
    <!-- 5. 实际应用场景 -->
    <section class="example-section">
      <h2>5. 实际应用场景</h2>
      
      <!-- 加载状态 -->
      <div class="use-case">
        <h3>AI思考加载</h3>
        <div class="loading-demo">
          <ThinkingIcon :size="48" color="#667eea" />
          <p>AI正在分析线索...</p>
        </div>
      </div>
      
      <!-- 成功提示 -->
      <div class="use-case">
        <h3>胜利庆祝</h3>
        <div class="success-demo">
          <TrophyIcon :size="120" />
          <h3>恭喜破案!</h3>
          <p>你成功找出了真凶</p>
        </div>
      </div>
      
      <!-- 按钮图标 -->
      <div class="use-case">
        <h3>按钮集成</h3>
        <div class="button-demo">
          <button class="icon-button">
            <DiceIcon :size="24" />
            投掷骰子
          </button>
          <button class="icon-button">
            <ClueIcon :size="24" />
            查找线索
          </button>
          <button class="icon-button">
            <LocationIcon :size="24" />
            选择位置
          </button>
        </div>
      </div>
      
      <!-- 卡片装饰 -->
      <div class="use-case">
        <h3>卡片装饰</h3>
        <div class="card-demo">
          <div class="game-card">
            <DetectiveIcon :size="80" color="#667eea" class="card-icon" />
            <h3>福尔摩斯案件</h3>
            <p>经典推理解谜游戏</p>
            <div class="card-footer">
              <span><ClueIcon :size="16" /> 12 条线索</span>
              <span><LocationIcon :size="16" /> 5 个地点</span>
            </div>
          </div>
        </div>
      </div>
    </section>
    
    <!-- 6. 主题系统 -->
    <section class="example-section">
      <h2>6. 主题颜色</h2>
      <div class="theme-demo">
        <div v-for="theme in themes" :key="theme.name" class="theme-row">
          <h4>{{ theme.name }}</h4>
          <div class="icon-grid">
            <DetectiveIcon :size="48" :color="theme.colors.detective" />
            <DiceIcon :size="48" :color="theme.colors.dice" />
            <ThinkingIcon :size="48" :color="theme.colors.thinking" />
            <TrophyIcon :size="48" :color="theme.colors.trophy" />
            <ClueIcon :size="48" :color="theme.colors.clue" />
            <LocationIcon :size="48" :color="theme.colors.location" />
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import {
  DetectiveIcon,
  DiceIcon,
  ThinkingIcon,
  TrophyIcon,
  ClueIcon,
  LocationIcon,
  IconThemes
} from '@/components/icons'

const themes = ref([
  { name: 'Primary (默认)', colors: IconThemes.primary },
  { name: 'Dark (暗色)', colors: IconThemes.dark },
  { name: 'Light (亮色)', colors: IconThemes.light },
  { name: 'Grayscale (灰度)', colors: IconThemes.grayscale }
])
</script>

<style scoped>
.icon-examples {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 20px;
}

h1 {
  font-size: 2.5rem;
  margin-bottom: 40px;
  text-align: center;
  color: #2c3e50;
}

.example-section {
  margin-bottom: 60px;
  padding: 30px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.example-section h2 {
  font-size: 1.8rem;
  margin-bottom: 24px;
  color: #34495e;
  border-bottom: 2px solid #3498db;
  padding-bottom: 8px;
}

.icon-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 30px;
  justify-items: center;
}

.icon-item {
  text-align: center;
}

.icon-item p {
  margin-top: 12px;
  font-size: 0.9rem;
  color: #7f8c8d;
}

.size-demo {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  gap: 20px;
  padding: 20px;
}

.use-case {
  margin-bottom: 40px;
}

.use-case h3 {
  font-size: 1.3rem;
  margin-bottom: 16px;
  color: #2c3e50;
}

.loading-demo {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

.loading-demo p {
  font-size: 1.1rem;
  color: #667eea;
}

.success-demo {
  text-align: center;
  padding: 40px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  color: white;
}

.success-demo h3 {
  font-size: 2rem;
  margin: 16px 0 8px;
  color: white;
}

.success-demo p {
  font-size: 1.1rem;
  opacity: 0.9;
}

.button-demo {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.icon-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s;
}

.icon-button:hover {
  background: #2980b9;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
}

.card-demo {
  display: flex;
  justify-content: center;
}

.game-card {
  width: 320px;
  padding: 30px;
  background: white;
  border: 2px solid #ecf0f1;
  border-radius: 12px;
  text-align: center;
  transition: all 0.3s;
}

.game-card:hover {
  border-color: #3498db;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  transform: translateY(-4px);
}

.card-icon {
  margin-bottom: 16px;
}

.game-card h3 {
  font-size: 1.5rem;
  margin: 16px 0 8px;
  color: #2c3e50;
}

.game-card p {
  color: #7f8c8d;
  margin-bottom: 20px;
}

.card-footer {
  display: flex;
  justify-content: space-around;
  padding-top: 16px;
  border-top: 1px solid #ecf0f1;
  font-size: 0.9rem;
  color: #95a5a6;
}

.card-footer span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.theme-demo {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.theme-row h4 {
  font-size: 1.2rem;
  margin-bottom: 12px;
  color: #34495e;
}

@media (max-width: 768px) {
  .icon-grid {
    grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
    gap: 20px;
  }
  
  .size-demo {
    flex-direction: column;
    align-items: center;
  }
  
  .button-demo {
    flex-direction: column;
  }
  
  .icon-button {
    width: 100%;
    justify-content: center;
  }
}
</style>
