/**
 * Animated Icons Library
 * Centralized export for all animated SVG icon components
 */

// Game-themed icons
export { default as DetectiveIcon } from './DetectiveIcon.vue'
export { default as DiceIcon } from './DiceIcon.vue'
export { default as ThinkingIcon } from './ThinkingIcon.vue'
export { default as TrophyIcon } from './TrophyIcon.vue'
export { default as ClueIcon } from './ClueIcon.vue'
export { default as LocationIcon } from './LocationIcon.vue'

// Import for internal use
import DetectiveIcon from './DetectiveIcon.vue'
import DiceIcon from './DiceIcon.vue'
import ThinkingIcon from './ThinkingIcon.vue'
import TrophyIcon from './TrophyIcon.vue'
import ClueIcon from './ClueIcon.vue'
import LocationIcon from './LocationIcon.vue'

/**
 * Icon Usage Guide:
 * 
 * 1. Basic Import:
 *    import { DetectiveIcon, DiceIcon } from '@/components/icons'
 * 
 * 2. Component Usage:
 *    <DetectiveIcon :size="64" color="#667eea" :animate="true" />
 * 
 * 3. Common Props (all icons):
 *    - size: Number | String (default: 100) - Width and height in pixels
 *    - color: String (default varies) - Primary color
 *    - animate: Boolean (default: true) - Enable/disable animations
 *    - className: String (default: '') - Additional CSS classes
 * 
 * 4. Icon-Specific Props:
 * 
 *    DetectiveIcon:
 *      - color: '#667eea' (detective outfit color)
 * 
 *    DiceIcon:
 *      - color: '#2ecc71' (dice body color)
 *      - rollSpeed: 100 (ms between number changes)
 * 
 *    ThinkingIcon:
 *      - color: '#9b59b6' (brain color)
 *      - dotColor: 'white' (thinking dots color)
 * 
 *    TrophyIcon:
 *      - color: '#f39c12' (trophy color)
 *      - baseColor: '#95a5a6' (base color)
 *      - starColor: '#ffd700' (star decoration color)
 * 
 *    ClueIcon:
 *      - color: '#3498db' (lens ring color)
 *      - handleColor: '#8b4513' (handle color)
 *      - sparkleColor: '#ffd700' (sparkle color)
 * 
 *    LocationIcon:
 *      - color: '#e74c3c' (pin color)
 * 
 * 5. Performance Tips:
 *    - Set animate={false} for static displays
 *    - Use smaller sizes for lists/grids
 *    - Icons use requestAnimationFrame for smooth 60fps
 *    - All animations cleanup on unmount
 * 
 * 6. Accessibility:
 *    - Icons are decorative SVGs
 *    - Add aria-label to parent element if icon conveys meaning
 *    - Example: <div aria-label="Detective investigating">
 *                 <DetectiveIcon />
 *               </div>
 * 
 * 7. Customization:
 *    - All icons accept className prop for custom styling
 *    - Colors can be overridden via props
 *    - Animations can be customized in component files
 * 
 * 8. Example Implementations:
 * 
 *    // Victory screen
 *    <TrophyIcon :size="120" :animate="true" />
 * 
 *    // Game loading state
 *    <ThinkingIcon :size="48" color="#667eea" />
 * 
 *    // Dice roll button
 *    <DiceIcon :size="32" :rollSpeed="50" />
 * 
 *    // Location selector
 *    <LocationIcon :size="40" color="#e74c3c" />
 * 
 *    // Clue discovery notification
 *    <ClueIcon :size="56" :animate="true" />
 */

// Icon categories for easy reference
export const GameIcons = {
  Detective: 'DetectiveIcon',
  Dice: 'DiceIcon',
  Thinking: 'ThinkingIcon',
  Trophy: 'TrophyIcon',
  Clue: 'ClueIcon',
  Location: 'LocationIcon'
}

// Default sizes for different use cases
export const IconSizes = {
  SMALL: 24,      // Inline text, buttons
  MEDIUM: 48,     // Cards, list items
  LARGE: 72,      // Headers, feature displays
  XLARGE: 120,    // Hero sections, celebration screens
  XXLARGE: 200    // Full-screen effects
}

// Predefined color themes
export const IconThemes = {
  primary: {
    detective: '#667eea',
    dice: '#2ecc71',
    thinking: '#9b59b6',
    trophy: '#f39c12',
    clue: '#3498db',
    location: '#e74c3c'
  },
  dark: {
    detective: '#4c5fd7',
    dice: '#27ae60',
    thinking: '#8e44ad',
    trophy: '#d68910',
    clue: '#2980b9',
    location: '#c0392b'
  },
  light: {
    detective: '#8093f1',
    dice: '#55d98d',
    thinking: '#b07cc6',
    trophy: '#f5ab35',
    clue: '#5dade2',
    location: '#ec7063'
  },
  grayscale: {
    detective: '#7f8c8d',
    dice: '#95a5a6',
    thinking: '#7f8c8d',
    trophy: '#95a5a6',
    clue: '#7f8c8d',
    location: '#95a5a6'
  }
}

/**
 * Helper function to get icon component by name
 * @param {string} name - Icon name (e.g., 'detective', 'dice')
 * @returns {Component} Vue component
 */
export function getIconComponent(name) {
  if (!name) return null
  
  const iconMap = {
    detective: DetectiveIcon,
    dice: DiceIcon,
    thinking: ThinkingIcon,
    trophy: TrophyIcon,
    clue: ClueIcon,
    location: LocationIcon
  }
  
  return iconMap[name.toLowerCase()] || null
}

/**
 * Helper function to get icon color from theme
 * @param {string} iconName - Icon name
 * @param {string} theme - Theme name (default: 'primary')
 * @returns {string} Color hex code
 */
export function getIconColor(iconName, theme = 'primary') {
  return IconThemes[theme]?.[iconName.toLowerCase()] || IconThemes.primary[iconName.toLowerCase()]
}
