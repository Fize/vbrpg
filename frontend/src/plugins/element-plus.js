/**
 * Element Plus Theme Customization
 * 
 * Customizes Element Plus component styles to match the platform's design system.
 */

export const elementPlusTheme = {
  // Primary color (purple gradient theme)
  'color-primary': '#667eea',
  'color-primary-light-3': '#7c8ff4',
  'color-primary-light-5': '#9aa5f7',
  'color-primary-light-7': '#b8bdfa',
  'color-primary-light-9': '#e5e7fe',
  'color-primary-dark-2': '#5568d3',
  
  // Success color
  'color-success': '#67c23a',
  'color-success-light-3': '#85ce61',
  'color-success-light-5': '#95d475',
  'color-success-light-7': '#b3e19d',
  'color-success-light-9': '#e1f3d8',
  
  // Warning color
  'color-warning': '#e6a23c',
  'color-warning-light-3': '#ebb563',
  'color-warning-light-5': '#efc78f',
  'color-warning-light-7': '#f3d19e',
  'color-warning-light-9': '#faecd8',
  
  // Danger color
  'color-danger': '#f56c6c',
  'color-danger-light-3': '#f78989',
  'color-danger-light-5': '#f9a7a7',
  'color-danger-light-7': '#fbc4c4',
  'color-danger-light-9': '#fde2e2',
  
  // Info color
  'color-info': '#409eff',
  'color-info-light-3': '#66b1ff',
  'color-info-light-5': '#79bbff',
  'color-info-light-7': '#a0cfff',
  'color-info-light-9': '#d9ecff',
  
  // Text colors
  'text-color-primary': '#303133',
  'text-color-regular': '#606266',
  'text-color-secondary': '#909399',
  'text-color-placeholder': '#c0c4cc',
  
  // Border colors
  'border-color-base': '#dcdfe6',
  'border-color-light': '#e4e7ed',
  'border-color-lighter': '#ebeef5',
  'border-color-extra-light': '#f2f6fc',
  
  // Background colors
  'background-color-base': '#f5f7fa',
  'fill-color-blank': '#ffffff',
  'fill-color-light': '#f5f7fa',
  'fill-color-lighter': '#fafafa',
  'fill-color-extra-light': '#fafcff',
  'fill-color-dark': '#ebedf0',
  'fill-color-darker': '#e6e8eb',
  'fill-color-blank': '#ffffff',
  
  // Border radius
  'border-radius-base': '8px',
  'border-radius-small': '4px',
  'border-radius-round': '16px',
  'border-radius-circle': '100%',
  
  // Component specific
  'card-border-radius': '12px',
  'button-border-radius': '8px',
  'input-border-radius': '8px',
  
  // Shadows
  'box-shadow-base': '0 2px 4px rgba(0, 0, 0, 0.1)',
  'box-shadow-light': '0 2px 12px rgba(0, 0, 0, 0.1)',
  'box-shadow-dark': '0 4px 16px rgba(0, 0, 0, 0.15)',
  
  // Transitions
  'transition-duration': '0.25s',
  'transition-duration-fast': '0.15s',
  
  // Typography
  'font-size-extra-large': '20px',
  'font-size-large': '18px',
  'font-size-medium': '16px',
  'font-size-base': '14px',
  'font-size-small': '13px',
  'font-size-extra-small': '12px',
}

/**
 * Apply theme to Element Plus
 * This can be used with Element Plus's ConfigProvider or via CSS variables
 */
export function applyElementPlusTheme() {
  const root = document.documentElement
  
  Object.entries(elementPlusTheme).forEach(([key, value]) => {
    // Convert camelCase to kebab-case for CSS variables
    const cssVarName = `--el-${key.replace(/([A-Z])/g, '-$1').toLowerCase()}`
    root.style.setProperty(cssVarName, value)
  })
}

/**
 * Dark mode theme overrides for Element Plus
 */
export const elementPlusDarkTheme = {
  'text-color-primary': '#e4e7ed',
  'text-color-regular': '#c0c4cc',
  'text-color-secondary': '#909399',
  'text-color-placeholder': '#606266',
  
  'border-color-base': '#4c4d4f',
  'border-color-light': '#414243',
  'border-color-lighter': '#363637',
  'border-color-extra-light': '#2b2b2c',
  
  'fill-color-blank': '#1a1a1a',
  'fill-color-light': '#262727',
  'fill-color-lighter': '#1d1e1f',
  'fill-color-extra-light': '#191a1b',
  'fill-color-dark': '#212122',
  'fill-color-darker': '#1b1c1d',
  
  'background-color-base': '#141414',
  
  'box-shadow-base': '0 2px 4px rgba(0, 0, 0, 0.3)',
  'box-shadow-light': '0 2px 12px rgba(0, 0, 0, 0.3)',
  'box-shadow-dark': '0 4px 16px rgba(0, 0, 0, 0.4)',
}

/**
 * Apply dark theme to Element Plus
 */
export function applyElementPlusDarkTheme() {
  const root = document.documentElement
  
  Object.entries(elementPlusDarkTheme).forEach(([key, value]) => {
    const cssVarName = `--el-${key.replace(/([A-Z])/g, '-$1').toLowerCase()}`
    root.style.setProperty(cssVarName, value)
  })
}
