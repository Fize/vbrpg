<template>
  <AppLayout />
</template>

<script setup>
import AppLayout from '@/components/common/AppLayout.vue'

// 单人模式下无需初始化玩家账户
// 所有玩家都是 AI，用户只是观战
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
