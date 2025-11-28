<template>
  <div class="app-layout" :class="{ 'is-mobile': isMobile }">
    <!-- Header -->
    <header class="app-header">
      <div class="container-xl">
        <div class="header-content">
          <!-- Logo -->
          <router-link to="/" class="logo">
            <h1>AI桌游平台</h1>
          </router-link>
          
          <!-- Desktop Navigation -->
          <nav class="desktop-nav hidden-mobile">
            <router-link to="/games" class="nav-link">
              <el-icon><Menu /></el-icon>
              游戏大厅
            </router-link>
            <router-link v-if="isAuthenticated" to="/profile" class="nav-link">
              <el-icon><User /></el-icon>
              个人资料
            </router-link>
          </nav>
          
          <!-- User Section -->
          <div class="user-section">
            <span v-if="isAuthenticated" class="username">
              {{ username }}
              <el-tag v-if="isGuest" type="warning" size="small">访客</el-tag>
            </span>
            
            <!-- Mobile Menu Toggle -->
            <el-button 
              class="mobile-menu-toggle hidden-tablet"
              text
              @click="mobileMenuOpen = !mobileMenuOpen"
            >
              <el-icon :size="24"><Menu /></el-icon>
            </el-button>
          </div>
        </div>
      </div>
    </header>
    
    <!-- Mobile Navigation Drawer -->
    <el-drawer
      v-model="mobileMenuOpen"
      direction="rtl"
      :size="280"
      class="mobile-nav-drawer"
    >
      <template #header>
        <div class="drawer-header">
          <span class="username">{{ username }}</span>
          <el-tag v-if="isGuest" type="warning" size="small">访客</el-tag>
        </div>
      </template>
      
      <nav class="mobile-nav">
        <router-link 
          to="/games" 
          class="mobile-nav-link"
          @click="mobileMenuOpen = false"
        >
          <el-icon><Menu /></el-icon>
          <span>游戏大厅</span>
        </router-link>
        
        <router-link 
          v-if="isAuthenticated" 
          to="/profile" 
          class="mobile-nav-link"
          @click="mobileMenuOpen = false"
        >
          <el-icon><User /></el-icon>
          <span>个人资料</span>
        </router-link>
      </nav>
    </el-drawer>
    
    <!-- Main Content -->
    <main class="app-main">
      <div class="content-wrapper">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
    
    <!-- Footer -->
    <footer class="app-footer">
      <div class="container-xl">
        <div class="footer-content">
          <p>&copy; 2025 AI桌游平台. All rights reserved.</p>
          <div class="footer-links">
            <a href="#" class="footer-link">关于我们</a>
            <a href="#" class="footer-link">隐私政策</a>
            <a href="#" class="footer-link">使用条款</a>
          </div>
        </div>
      </div>
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
}

/* ==================== Header ==================== */
.app-header {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  background: var(--color-bg-primary);
  border-bottom: 1px solid var(--color-border-base);
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-base);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  gap: var(--space-lg);
}

.logo {
  text-decoration: none;
  color: var(--color-text-primary);
  font-weight: 600;
  font-size: 1.25rem;
  transition: color var(--transition-fast);
}

.logo:hover {
  color: var(--color-primary);
}

.logo h1 {
  margin: 0;
  font-size: 1.25rem;
  background: var(--color-primary-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* ==================== Desktop Navigation ==================== */
.desktop-nav {
  display: flex;
  gap: var(--space-md);
  align-items: center;
  flex: 1;
  margin-left: var(--space-xl);
}

.nav-link {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-sm) var(--space-md);
  color: var(--color-text-regular);
  text-decoration: none;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  font-weight: 500;
}

.nav-link:hover {
  color: var(--color-primary);
  background: var(--color-bg-secondary);
}

.nav-link.router-link-active {
  color: var(--color-primary);
  background: var(--color-primary-light-9);
}

/* ==================== User Section ==================== */
.user-section {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.username {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  font-weight: 500;
  color: var(--color-text-primary);
}

.mobile-menu-toggle {
  padding: var(--space-sm);
}

/* ==================== Mobile Navigation ==================== */
.mobile-nav-drawer :deep(.el-drawer__header) {
  margin-bottom: 0;
  padding-bottom: var(--space-md);
  border-bottom: 1px solid var(--color-border-base);
}

.drawer-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.mobile-nav {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  padding: var(--space-md) 0;
}

.mobile-nav-link {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md);
  color: var(--color-text-primary);
  text-decoration: none;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  font-size: 1rem;
}

.mobile-nav-link:hover {
  background: var(--color-bg-secondary);
  color: var(--color-primary);
}

.mobile-nav-link.router-link-active {
  background: var(--color-primary-light-9);
  color: var(--color-primary);
}

.mobile-nav-link .el-icon {
  font-size: 1.25rem;
}

/* ==================== Main Content ==================== */
.app-main {
  flex: 1;
  padding: var(--space-lg) 0;
}

.content-wrapper {
  min-height: calc(100vh - 200px);
}

/* Page Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-base);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ==================== Footer ==================== */
.app-footer {
  margin-top: auto;
  padding: var(--space-xl) 0;
  background: var(--color-bg-secondary);
  border-top: 1px solid var(--color-border-base);
}

.footer-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
  text-align: center;
}

.footer-content p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}

.footer-links {
  display: flex;
  gap: var(--space-lg);
  flex-wrap: wrap;
  justify-content: center;
}

.footer-link {
  color: var(--color-text-regular);
  text-decoration: none;
  font-size: 0.875rem;
  transition: color var(--transition-fast);
}

.footer-link:hover {
  color: var(--color-primary);
}

/* ==================== Responsive ==================== */
@media (min-width: 768px) {
  .footer-content {
    flex-direction: row;
    justify-content: space-between;
  }
}

@media (max-width: 767px) {
  .header-content {
    height: 56px;
  }
  
  .logo h1 {
    font-size: 1.1rem;
  }
  
  .app-main {
    padding: var(--space-md) 0;
  }
}
</style>
