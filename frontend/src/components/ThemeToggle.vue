<template>
  <el-switch
    v-model="isDark"
    class="theme-toggle"
    :active-icon="Moon"
    :inactive-icon="Sunny"
    inline-prompt
    @change="toggleTheme"
  />
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Moon, Sunny } from '@element-plus/icons-vue'
import { applyElementPlusDarkTheme, applyElementPlusTheme } from '@/plugins/element-plus'

const isDark = ref(false)

// Get stored theme preference
const getStoredTheme = () => {
  const stored = localStorage.getItem('theme')
  if (stored) {
    return stored === 'dark'
  }
  // Check system preference
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

// Apply theme to document
const applyTheme = (dark) => {
  if (dark) {
    document.documentElement.setAttribute('data-theme', 'dark')
    applyElementPlusDarkTheme()
  } else {
    document.documentElement.removeAttribute('data-theme')
    applyElementPlusTheme()
  }
}

// Toggle theme
const toggleTheme = () => {
  const newTheme = isDark.value ? 'dark' : 'light'
  localStorage.setItem('theme', newTheme)
  applyTheme(isDark.value)
}

// Initialize theme on mount
onMounted(() => {
  isDark.value = getStoredTheme()
  applyTheme(isDark.value)
  
  // Apply base Element Plus theme
  if (!isDark.value) {
    applyElementPlusTheme()
  }
})
</script>

<style scoped>
.theme-toggle {
  --el-switch-on-color: var(--color-primary);
  --el-switch-off-color: var(--color-text-secondary);
}
</style>
