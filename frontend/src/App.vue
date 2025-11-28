<template>
  <AppLayout />
</template>

<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { playersApi } from '@/services/api'
import AppLayout from '@/components/common/AppLayout.vue'

const authStore = useAuthStore()

// 初始化玩家账户（访客或已有账户）
const initializePlayer = async () => {
  authStore.setLoading(true)
  try {
    // 先尝试获取当前玩家（通过 session cookie）
    const player = await playersApi.getCurrentPlayer()
    authStore.setPlayer(player)
  } catch (error) {
    // 如果没有 session 或 session 过期，创建新的访客账户
    if (error.response?.status === 401) {
      try {
        const newGuest = await playersApi.createGuest()
        authStore.setPlayer(newGuest)
      } catch (createError) {
        console.error('Failed to create guest account:', createError)
      }
    } else {
      console.error('Failed to get current player:', error)
    }
  } finally {
    authStore.setLoading(false)
  }
}

onMounted(() => {
  initializePlayer()
})
</script>

<style>
* {
  box-sizing: border-box;
}

html, body {
  margin: 0;
  padding: 0;
  width: 100%;
  overflow-x: hidden;
}

#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans', sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol',
    'Noto Color Emoji';
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  min-height: 100vh;
  width: 100%;
}

/* 优化 Element Plus 组件在移动端的显示 */
.el-button {
  white-space: nowrap;
}

.el-tag {
  white-space: nowrap;
}

/* 确保卡片在小屏幕上不会太窄 */
.el-card {
  min-width: 0;
}

/* 优化描述列表在移动端的显示 */
@media (max-width: 768px) {
  .el-descriptions__label {
    font-size: 13px !important;
  }
  
  .el-descriptions__content {
    font-size: 13px !important;
  }
}
</style>
