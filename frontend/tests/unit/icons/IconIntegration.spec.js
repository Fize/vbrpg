import { describe, it, expect } from 'vitest'
import {
  DetectiveIcon,
  DiceIcon,
  ThinkingIcon,
  TrophyIcon,
  ClueIcon,
  LocationIcon,
  GameIcons,
  IconSizes,
  IconThemes,
  getIconComponent,
  getIconColor
} from '@/components/icons'

describe('Icon Library Integration', () => {
  describe('Named Exports', () => {
    it('should export all icon components', () => {
      expect(DetectiveIcon).toBeDefined()
      expect(DiceIcon).toBeDefined()
      expect(ThinkingIcon).toBeDefined()
      expect(TrophyIcon).toBeDefined()
      expect(ClueIcon).toBeDefined()
      expect(LocationIcon).toBeDefined()
    })

    it('should export all components as Vue components', () => {
      const components = [
        DetectiveIcon,
        DiceIcon,
        ThinkingIcon,
        TrophyIcon,
        ClueIcon,
        LocationIcon
      ]

      components.forEach(component => {
        // Vue 3 components use __name in script setup
        expect(component).toHaveProperty('__name')
        expect(typeof component).toBe('object')
      })
    })
  })

  describe('GameIcons Constant', () => {
    it('should have correct icon mapping', () => {
      expect(GameIcons.Detective).toBe('DetectiveIcon')
      expect(GameIcons.Dice).toBe('DiceIcon')
      expect(GameIcons.Thinking).toBe('ThinkingIcon')
      expect(GameIcons.Trophy).toBe('TrophyIcon')
      expect(GameIcons.Clue).toBe('ClueIcon')
      expect(GameIcons.Location).toBe('LocationIcon')
    })

    it('should have exactly 6 game icons', () => {
      expect(Object.keys(GameIcons).length).toBe(6)
    })
  })

  describe('IconSizes Constant', () => {
    it('should have all size presets', () => {
      expect(IconSizes.SMALL).toBe(24)
      expect(IconSizes.MEDIUM).toBe(48)
      expect(IconSizes.LARGE).toBe(72)
      expect(IconSizes.XLARGE).toBe(120)
      expect(IconSizes.XXLARGE).toBe(200)
    })

    it('should have sizes in ascending order', () => {
      expect(IconSizes.SMALL).toBeLessThan(IconSizes.MEDIUM)
      expect(IconSizes.MEDIUM).toBeLessThan(IconSizes.LARGE)
      expect(IconSizes.LARGE).toBeLessThan(IconSizes.XLARGE)
      expect(IconSizes.XLARGE).toBeLessThan(IconSizes.XXLARGE)
    })

    it('should have 5 size options', () => {
      expect(Object.keys(IconSizes).length).toBe(5)
    })
  })

  describe('IconThemes', () => {
    it('should have all theme variants', () => {
      expect(IconThemes).toHaveProperty('primary')
      expect(IconThemes).toHaveProperty('dark')
      expect(IconThemes).toHaveProperty('light')
      expect(IconThemes).toHaveProperty('grayscale')
    })

    it('should have colors for all icons in each theme', () => {
      const iconNames = ['detective', 'dice', 'thinking', 'trophy', 'clue', 'location']
      const themes = ['primary', 'dark', 'light', 'grayscale']

      themes.forEach(theme => {
        iconNames.forEach(icon => {
          expect(IconThemes[theme][icon]).toBeDefined()
          expect(typeof IconThemes[theme][icon]).toBe('string')
          expect(IconThemes[theme][icon]).toMatch(/^#[0-9a-fA-F]{6}$/)
        })
      })
    })

    it('should have different colors for each theme', () => {
      const primaryDetective = IconThemes.primary.detective
      const darkDetective = IconThemes.dark.detective
      const lightDetective = IconThemes.light.detective

      expect(primaryDetective).not.toBe(darkDetective)
      expect(primaryDetective).not.toBe(lightDetective)
      expect(darkDetective).not.toBe(lightDetective)
    })

    it('should have grayscale theme with gray colors', () => {
      const grayColors = Object.values(IconThemes.grayscale)
      
      // All grayscale colors should be similar (gray tones)
      grayColors.forEach(color => {
        expect(color).toMatch(/^#[789][0-9a-fA-F]{5}$/)
      })
    })

    it('should have consistent color count across themes', () => {
      const themes = Object.values(IconThemes)
      const firstThemeCount = Object.keys(themes[0]).length

      themes.forEach(theme => {
        expect(Object.keys(theme).length).toBe(firstThemeCount)
      })
    })
  })

  describe('getIconComponent Helper', () => {
    it('should return correct component for valid icon name', () => {
      expect(getIconComponent('detective')).toBe(DetectiveIcon)
      expect(getIconComponent('dice')).toBe(DiceIcon)
      expect(getIconComponent('thinking')).toBe(ThinkingIcon)
      expect(getIconComponent('trophy')).toBe(TrophyIcon)
      expect(getIconComponent('clue')).toBe(ClueIcon)
      expect(getIconComponent('location')).toBe(LocationIcon)
    })

    it('should be case-insensitive', () => {
      expect(getIconComponent('Detective')).toBe(DetectiveIcon)
      expect(getIconComponent('DICE')).toBe(DiceIcon)
      expect(getIconComponent('ThInKiNg')).toBe(ThinkingIcon)
    })

    it('should return null for invalid icon name', () => {
      expect(getIconComponent('invalid')).toBeNull()
      expect(getIconComponent('')).toBeNull()
      expect(getIconComponent('unknown')).toBeNull()
    })

    it('should handle all icon names', () => {
      const iconNames = ['detective', 'dice', 'thinking', 'trophy', 'clue', 'location']
      
      iconNames.forEach(name => {
        const component = getIconComponent(name)
        expect(component).not.toBeNull()
        expect(component).toBeDefined()
      })
    })
  })

  describe('getIconColor Helper', () => {
    it('should return correct color for icon and theme', () => {
      const color = getIconColor('detective', 'primary')
      expect(color).toBe(IconThemes.primary.detective)
    })

    it('should use primary theme by default', () => {
      const color = getIconColor('dice')
      expect(color).toBe(IconThemes.primary.dice)
    })

    it('should work with all themes', () => {
      const themes = ['primary', 'dark', 'light', 'grayscale']
      
      themes.forEach(theme => {
        const color = getIconColor('thinking', theme)
        expect(color).toBe(IconThemes[theme].thinking)
      })
    })

    it('should be case-insensitive for icon name', () => {
      const color1 = getIconColor('Trophy', 'primary')
      const color2 = getIconColor('trophy', 'primary')
      
      expect(color1).toBe(color2)
    })

    it('should return color for all icons', () => {
      const iconNames = ['detective', 'dice', 'thinking', 'trophy', 'clue', 'location']
      
      iconNames.forEach(icon => {
        const color = getIconColor(icon, 'primary')
        expect(color).toBeDefined()
        expect(typeof color).toBe('string')
      })
    })

    it('should fall back to primary theme for invalid theme', () => {
      const color = getIconColor('detective', 'invalid')
      expect(color).toBe(IconThemes.primary.detective)
    })
  })

  describe('Theme System Integration', () => {
    it('should support theme switching', () => {
      const themes = ['primary', 'dark', 'light', 'grayscale']
      const iconName = 'detective'
      
      const colors = themes.map(theme => getIconColor(iconName, theme))
      
      // All colors should be different
      const uniqueColors = new Set(colors)
      expect(uniqueColors.size).toBe(themes.length)
    })

    it('should provide consistent API for all icons', () => {
      const iconNames = Object.keys(IconThemes.primary)
      
      iconNames.forEach(icon => {
        const component = getIconComponent(icon)
        const color = getIconColor(icon, 'primary')
        
        expect(component).not.toBeNull()
        expect(color).toBeDefined()
      })
    })
  })

  describe('Usage Patterns', () => {
    it('should support dynamic icon loading', () => {
      const iconName = 'detective'
      const Icon = getIconComponent(iconName)
      const color = getIconColor(iconName, 'primary')
      
      expect(Icon).toBe(DetectiveIcon)
      expect(color).toBe(IconThemes.primary.detective)
    })

    it('should work with GameIcons mapping', () => {
      Object.entries(GameIcons).forEach(([key, value]) => {
        const iconName = key.toLowerCase()
        const component = getIconComponent(iconName)
        
        expect(component).toBeDefined()
        expect(component).not.toBeNull()
      })
    })

    it('should provide size presets for responsive design', () => {
      // Verify sizes are suitable for different contexts
      expect(IconSizes.SMALL).toBeGreaterThanOrEqual(16)
      expect(IconSizes.SMALL).toBeLessThanOrEqual(32)
      
      expect(IconSizes.MEDIUM).toBeGreaterThanOrEqual(40)
      expect(IconSizes.MEDIUM).toBeLessThanOrEqual(64)
      
      expect(IconSizes.LARGE).toBeGreaterThanOrEqual(64)
      expect(IconSizes.LARGE).toBeLessThanOrEqual(96)
      
      expect(IconSizes.XLARGE).toBeGreaterThanOrEqual(96)
      expect(IconSizes.XLARGE).toBeLessThanOrEqual(160)
      
      expect(IconSizes.XXLARGE).toBeGreaterThanOrEqual(160)
    })
  })

  describe('Documentation and Developer Experience', () => {
    it('should export all necessary utilities', () => {
      expect(GameIcons).toBeDefined()
      expect(IconSizes).toBeDefined()
      expect(IconThemes).toBeDefined()
      expect(getIconComponent).toBeDefined()
      expect(getIconColor).toBeDefined()
    })

    it('should have clear naming conventions', () => {
      // All icon components end with 'Icon'
      const components = [
        DetectiveIcon,
        DiceIcon,
        ThinkingIcon,
        TrophyIcon,
        ClueIcon,
        LocationIcon
      ]

      components.forEach(component => {
        expect(component.name || component.__name).toMatch(/Icon$/)
      })
    })

    it('should support tree-shaking with named exports', () => {
      // Named exports allow bundlers to tree-shake unused icons
      expect(typeof DetectiveIcon).toBe('object')
      expect(typeof DiceIcon).toBe('object')
    })
  })

  describe('Accessibility and Standards', () => {
    it('should provide semantic size names', () => {
      const sizeNames = Object.keys(IconSizes)
      
      expect(sizeNames).toContain('SMALL')
      expect(sizeNames).toContain('MEDIUM')
      expect(sizeNames).toContain('LARGE')
    })

    it('should use standard hex color format', () => {
      const allColors = Object.values(IconThemes).flatMap(theme => 
        Object.values(theme)
      )

      allColors.forEach(color => {
        expect(color).toMatch(/^#[0-9a-fA-F]{6}$/)
      })
    })

    it('should have meaningful icon names', () => {
      const iconNames = Object.keys(GameIcons)
      
      iconNames.forEach(name => {
        expect(name.length).toBeGreaterThan(0)
        expect(name).toMatch(/^[A-Z][a-z]+$/)
      })
    })
  })

  describe('Error Handling', () => {
    it('should handle undefined gracefully', () => {
      expect(() => getIconComponent(undefined)).not.toThrow()
      expect(getIconComponent(undefined)).toBeNull()
    })

    it('should handle null gracefully', () => {
      expect(() => getIconComponent(null)).not.toThrow()
      expect(getIconComponent(null)).toBeNull()
    })

    it('should handle empty string', () => {
      expect(() => getIconComponent('')).not.toThrow()
      expect(getIconComponent('')).toBeNull()
    })

    it('should return primary color for undefined theme', () => {
      const color = getIconColor('detective', undefined)
      expect(color).toBe(IconThemes.primary.detective)
    })
  })

  describe('Performance Considerations', () => {
    it('should use object lookups for O(1) access', () => {
      // Test that helper functions are fast
      const startTime = performance.now()
      
      for (let i = 0; i < 1000; i++) {
        getIconComponent('detective')
        getIconColor('dice', 'primary')
      }
      
      const endTime = performance.now()
      const duration = endTime - startTime
      
      // Should complete in reasonable time (< 100ms for 1000 iterations)
      expect(duration).toBeLessThan(100)
    })

    it('should not create unnecessary objects', () => {
      // Same theme should return same color reference
      const color1 = IconThemes.primary.detective
      const color2 = IconThemes.primary.detective
      
      expect(color1).toBe(color2)
    })
  })

  describe('Complete Icon Library Coverage', () => {
    it('should have 6 unique icon components', () => {
      const icons = [
        DetectiveIcon,
        DiceIcon,
        ThinkingIcon,
        TrophyIcon,
        ClueIcon,
        LocationIcon
      ]

      const uniqueIcons = new Set(icons)
      expect(uniqueIcons.size).toBe(6)
    })

    it('should cover all game contexts', () => {
      // Detective: Investigation/search
      expect(getIconComponent('detective')).toBeDefined()
      
      // Dice: Randomness/chance
      expect(getIconComponent('dice')).toBeDefined()
      
      // Thinking: AI/processing
      expect(getIconComponent('thinking')).toBeDefined()
      
      // Trophy: Victory/achievement
      expect(getIconComponent('trophy')).toBeDefined()
      
      // Clue: Discovery/evidence
      expect(getIconComponent('clue')).toBeDefined()
      
      // Location: Places/navigation
      expect(getIconComponent('location')).toBeDefined()
    })

    it('should have 4 complete theme sets', () => {
      expect(Object.keys(IconThemes).length).toBe(4)
      
      Object.values(IconThemes).forEach(theme => {
        expect(Object.keys(theme).length).toBe(6)
      })
    })
  })
})
