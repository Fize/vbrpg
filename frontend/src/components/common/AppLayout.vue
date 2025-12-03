<template>
  <div class="app-layout" :class="{ 'is-mobile': isMobile, 'hide-chrome': shouldHideChrome }">
    <!-- Cyber Background -->
    <div class="cyber-bg">
      <div class="grid-lines"></div>
      <div class="scan-line"></div>
    </div>
    
    <!-- Header -->
    <header class="app-header" v-if="!shouldHideChrome">
      <div class="header-content">
        <!-- Logo -->
        <router-link to="/" class="logo">
          <div class="logo-icon">
            <span class="logo-bracket">[</span>
            <span class="logo-text">AI</span>
            <span class="logo-bracket">]</span>
          </div>
          <h1>游戏平台</h1>
          <div class="logo-glow"></div>
        </router-link>
        
        <!-- Desktop Navigation -->
        <nav class="desktop-nav hidden-mobile">
          <router-link v-if="isAuthenticated" to="/profile" class="nav-link">
            <el-icon><User /></el-icon>
            <span>个人资料</span>
            <div class="nav-indicator"></div>
          </router-link>
        </nav>
        
        <!-- User Section -->
        <div class="user-section">
          <div v-if="isAuthenticated" class="user-badge">
            <div class="user-avatar">
              <span>{{ username.charAt(0).toUpperCase() }}</span>
            </div>
            <span class="username">{{ username }}</span>
            <el-tag v-if="isGuest" class="guest-tag" size="small">访客</el-tag>
          </div>
          
          <!-- Mobile Menu Toggle -->
          <button 
            class="mobile-menu-toggle hidden-tablet"
            @click="mobileMenuOpen = !mobileMenuOpen"
          >
            <span class="hamburger-line"></span>
            <span class="hamburger-line"></span>
            <span class="hamburger-line"></span>
          </button>
        </div>
      </div>
      <div class="header-border"></div>
    </header>
    
    <!-- Mobile Navigation Drawer -->
    <el-drawer
      v-model="mobileMenuOpen"
      direction="rtl"
      :size="300"
      class="mobile-nav-drawer cyber-drawer"
    >
      <template #header>
        <div class="drawer-header">
          <div class="user-avatar large">
            <span>{{ username.charAt(0).toUpperCase() }}</span>
          </div>
          <div class="drawer-user-info">
            <span class="username">{{ username }}</span>
            <el-tag v-if="isGuest" class="guest-tag" size="small">访客</el-tag>
          </div>
        </div>
      </template>
      
      <nav class="mobile-nav">
        <router-link 
          v-if="isAuthenticated" 
          to="/profile" 
          class="mobile-nav-link"
          @click="mobileMenuOpen = false"
        >
          <el-icon><User /></el-icon>
          <span>个人资料</span>
          <div class="link-arrow">→</div>
        </router-link>
      </nav>
    </el-drawer>
    
    <!-- Main Content -->
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="cyber-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    
    <!-- Footer -->
    <footer class="app-footer" v-if="!shouldHideChrome">
      <div class="footer-content">
        <div class="footer-brand">
          <span class="footer-logo">[AI]</span>
          <p>&copy; 2025 AI游戏平台</p>
        </div>
        <div class="footer-links">
          <a href="#" class="footer-link">关于我们</a>
          <span class="footer-divider">|</span>
          <a href="#" class="footer-link">隐私政策</a>
          <span class="footer-divider">|</span>
          <a href="#" class="footer-link">使用条款</a>
        </div>
        <div class="footer-status">
          <span class="status-dot"></span>
          <span>系统在线</span>
        </div>
      </div>
      <div class="footer-border"></div>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Menu, User } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const mobileMenuOpen = ref(false)
const isMobile = ref(false)

const isAuthenticated = computed(() => authStore.isAuthenticated)
const isGuest = computed(() => authStore.isGuest)
const username = computed(() => authStore.username || '游客')

// 检查是否应该隐藏 header/footer (游戏页面)
const shouldHideChrome = computed(() => {
  return route.path.startsWith('/game/') || route.path.startsWith('/werewolf/')
})

// Check if mobile
const checkMobile = () => {
  isMobile.value = window.innerWidth < 768
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--color-bg-primary);
  position: relative;
  overflow-x: hidden;
}

/* 游戏模式：隐藏 header/footer */
.app-layout.hide-chrome {
  background: transparent;
}

.app-layout.hide-chrome .app-main {
  padding: 0;
  margin: 0;
}

/* ==================== Cyber Background ==================== */
.cyber-bg {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 0;
}

.grid-lines {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    linear-gradient(rgba(0, 240, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 240, 255, 0.03) 1px, transparent 1px);
  background-size: 50px 50px;
}

.scan-line {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--color-primary), transparent);
  opacity: 0.5;
  animation: scanLine 8s linear infinite;
}

@keyframes scanLine {
  0% { top: 0; }
  100% { top: 100%; }
}

/* ==================== Header ==================== */
.app-header {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  background: rgba(10, 10, 15, 0.95);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 70px;
  padding: 0 var(--space-xl);
  max-width: 1600px;
  margin: 0 auto;
}

.header-border {
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-primary), var(--color-accent), var(--color-primary), transparent);
  opacity: 0.6;
}

/* ==================== Logo ==================== */
.logo {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  text-decoration: none;
  position: relative;
}

.logo-icon {
  display: flex;
  align-items: center;
  font-family: 'Courier New', monospace;
  font-size: 1.5rem;
  font-weight: bold;
}

.logo-bracket {
  color: var(--color-primary);
  text-shadow: var(--glow-primary);
}

.logo-text {
  color: var(--color-accent);
  text-shadow: var(--glow-accent);
  margin: 0 2px;
}

.logo h1 {
  margin: 0;
  font-size: 1.3rem;
  font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: 0.05em;
}

.logo-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
  background: radial-gradient(ellipse, rgba(0, 240, 255, 0.2), transparent 70%);
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.3s;
}

.logo:hover .logo-glow {
  opacity: 1;
}

.logo:hover h1 {
  color: var(--color-primary);
  text-shadow: var(--glow-primary);
}

/* ==================== Desktop Navigation ==================== */
.desktop-nav {
  display: flex;
  gap: var(--space-sm);
  align-items: center;
  flex: 1;
  justify-content: center;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-sm) var(--space-lg);
  color: var(--color-text-secondary);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.95rem;
  position: relative;
  transition: all 0.3s ease;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
}

.nav-link .el-icon {
  font-size: 1.1rem;
}

.nav-indicator {
  position: absolute;
  bottom: -1px;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 2px;
  background: var(--color-primary);
  box-shadow: var(--glow-primary);
  transition: width 0.3s ease;
}

.nav-link:hover {
  color: var(--color-primary);
  border-color: rgba(0, 240, 255, 0.3);
  background: rgba(0, 240, 255, 0.05);
}

.nav-link:hover .nav-indicator {
  width: 80%;
}

.nav-link.router-link-active {
  color: var(--color-primary);
  background: rgba(0, 240, 255, 0.1);
  border-color: rgba(0, 240, 255, 0.4);
}

.nav-link.router-link-active .nav-indicator {
  width: 100%;
}

/* ==================== User Section ==================== */
.user-section {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.user-badge {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-xs) var(--space-md);
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: var(--radius-full);
}

.user-avatar {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary-gradient);
  border-radius: 50%;
  font-weight: bold;
  font-size: 0.9rem;
  color: var(--color-bg-primary);
}

.user-avatar.large {
  width: 48px;
  height: 48px;
  font-size: 1.2rem;
}

.username {
  font-weight: 500;
  color: var(--color-text-primary);
}

.guest-tag {
  background: rgba(245, 158, 11, 0.2) !important;
  border-color: rgba(245, 158, 11, 0.4) !important;
  color: #f59e0b !important;
}

.mobile-menu-toggle {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: var(--space-sm);
  background: transparent;
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.3s;
}

.mobile-menu-toggle:hover {
  background: rgba(0, 240, 255, 0.1);
  border-color: var(--color-primary);
}

.hamburger-line {
  width: 20px;
  height: 2px;
  background: var(--color-primary);
  transition: all 0.3s;
}

/* ==================== Mobile Navigation ==================== */
.cyber-drawer :deep(.el-drawer) {
  background: var(--color-bg-primary) !important;
}

.cyber-drawer :deep(.el-drawer__header) {
  margin-bottom: 0;
  padding: var(--space-lg);
  background: rgba(0, 240, 255, 0.05);
  border-bottom: 1px solid rgba(0, 240, 255, 0.2);
}

.drawer-header {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.drawer-user-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.mobile-nav {
  display: flex;
  flex-direction: column;
  padding: var(--space-md);
}

.mobile-nav-link {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md) var(--space-lg);
  color: var(--color-text-primary);
  text-decoration: none;
  border-radius: var(--radius-md);
  transition: all 0.3s;
  border: 1px solid transparent;
  margin-bottom: var(--space-sm);
}

.mobile-nav-link:hover {
  background: rgba(0, 240, 255, 0.1);
  border-color: rgba(0, 240, 255, 0.3);
  color: var(--color-primary);
}

.mobile-nav-link.router-link-active {
  background: rgba(0, 240, 255, 0.15);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.mobile-nav-link .el-icon {
  font-size: 1.25rem;
  color: var(--color-primary);
}

.link-arrow {
  margin-left: auto;
  color: var(--color-text-muted);
  font-family: monospace;
  transition: all 0.3s;
}

.mobile-nav-link:hover .link-arrow {
  color: var(--color-primary);
  transform: translateX(4px);
}

/* ==================== Main Content ==================== */
.app-main {
  flex: 1;
  position: relative;
  z-index: 1;
}

/* Page Transitions */
.cyber-fade-enter-active,
.cyber-fade-leave-active {
  transition: all 0.3s ease;
}

.cyber-fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.cyber-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* ==================== Footer ==================== */
.app-footer {
  margin-top: auto;
  background: rgba(10, 10, 15, 0.95);
  position: relative;
  z-index: 1;
}

.footer-border {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-primary), var(--color-accent), var(--color-primary), transparent);
  opacity: 0.4;
}

.footer-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-lg) var(--space-xl);
  max-width: 1600px;
  margin: 0 auto;
}

.footer-brand {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.footer-logo {
  font-family: 'Courier New', monospace;
  font-weight: bold;
  color: var(--color-primary);
  text-shadow: var(--glow-primary);
}

.footer-brand p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 0.875rem;
}

.footer-links {
  display: flex;
  gap: var(--space-sm);
  align-items: center;
}

.footer-link {
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: 0.875rem;
  transition: color 0.3s;
  padding: var(--space-xs) var(--space-sm);
}

.footer-link:hover {
  color: var(--color-primary);
  text-shadow: var(--glow-primary);
}

.footer-divider {
  color: var(--color-text-muted);
  opacity: 0.5;
}

.footer-status {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  color: var(--color-text-muted);
  font-size: 0.875rem;
}

.status-dot {
  width: 8px;
  height: 8px;
  background: var(--color-success);
  border-radius: 50%;
  animation: pulse 2s infinite;
  box-shadow: 0 0 10px var(--color-success);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* ==================== Responsive ==================== */
@media (max-width: 767px) {
  .header-content {
    height: 60px;
    padding: 0 var(--space-md);
  }
  
  .logo-icon {
    font-size: 1.2rem;
  }
  
  .logo h1 {
    font-size: 1.1rem;
  }
  
  .footer-content {
    flex-direction: column;
    gap: var(--space-md);
    text-align: center;
    padding: var(--space-lg) var(--space-md);
  }
  
  .footer-links {
    flex-wrap: wrap;
    justify-content: center;
  }
  
  .footer-status {
    justify-content: center;
  }
}
</style>
