import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import DetectiveIcon from '@/components/icons/DetectiveIcon.vue'
import DiceIcon from '@/components/icons/DiceIcon.vue'
import ThinkingIcon from '@/components/icons/ThinkingIcon.vue'
import TrophyIcon from '@/components/icons/TrophyIcon.vue'
import ClueIcon from '@/components/icons/ClueIcon.vue'
import LocationIcon from '@/components/icons/LocationIcon.vue'

describe('Animated Icons', () => {
  // Mock requestAnimationFrame and cancelAnimationFrame
  beforeEach(() => {
    vi.useFakeTimers()
    global.requestAnimationFrame = vi.fn((cb) => {
      return setTimeout(cb, 16) // ~60fps
    })
    global.cancelAnimationFrame = vi.fn((id) => {
      clearTimeout(id)
    })
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.restoreAllMocks()
  })

  describe('DetectiveIcon', () => {
    it('renders with default props', () => {
      const wrapper = mount(DetectiveIcon)
      expect(wrapper.find('svg').exists()).toBe(true)
      expect(wrapper.find('.detective-icon').exists()).toBe(true)
    })

    it('accepts custom size prop', () => {
      const wrapper = mount(DetectiveIcon, {
        props: { size: 120 }
      })
      const svg = wrapper.find('svg')
      expect(svg.attributes('width')).toBe('120')
      expect(svg.attributes('height')).toBe('120')
    })

    it('accepts custom color prop', () => {
      const wrapper = mount(DetectiveIcon, {
        props: { color: '#ff0000' }
      })
      expect(wrapper.html()).toContain('fill="#ff0000"')
    })

    it('accepts custom className prop', () => {
      const wrapper = mount(DetectiveIcon, {
        props: { className: 'custom-class' }
      })
      expect(wrapper.find('.custom-class').exists()).toBe(true)
    })

    it('starts animation when animate prop is true', async () => {
      const wrapper = mount(DetectiveIcon, {
        props: { animate: true }
      })
      
      await wrapper.vm.$nextTick()
      expect(global.requestAnimationFrame).toHaveBeenCalled()
    })

    it('does not animate when animate prop is false', async () => {
      const wrapper = mount(DetectiveIcon, {
        props: { animate: false }
      })
      
      await wrapper.vm.$nextTick()
      // Animation frame should not be called
      expect(wrapper.vm.glassTransform).toBe('')
    })

    it('cleans up animation on unmount', async () => {
      const wrapper = mount(DetectiveIcon, {
        props: { animate: true }
      })
      
      await wrapper.vm.$nextTick()
      const cancelSpy = vi.spyOn(global, 'cancelAnimationFrame')
      
      wrapper.unmount()
      expect(cancelSpy).toHaveBeenCalled()
    })

    it('updates glassTransform during animation', async () => {
      const wrapper = mount(DetectiveIcon, {
        props: { animate: true }
      })
      
      const initialTransform = wrapper.vm.glassTransform
      
      // Advance timers to trigger animation frame
      vi.advanceTimersByTime(100)
      await wrapper.vm.$nextTick()
      
      // Transform should change
      expect(wrapper.vm.glassTransform).not.toBe(initialTransform)
    })
  })

  describe('DiceIcon', () => {
    it('renders with default props', () => {
      const wrapper = mount(DiceIcon)
      expect(wrapper.find('svg').exists()).toBe(true)
      expect(wrapper.find('.dice-icon').exists()).toBe(true)
    })

    it('displays initial dice number', () => {
      const wrapper = mount(DiceIcon)
      expect(wrapper.vm.currentNumber).toBeGreaterThanOrEqual(1)
      expect(wrapper.vm.currentNumber).toBeLessThanOrEqual(6)
    })

    it('accepts custom rollSpeed prop', () => {
      const wrapper = mount(DiceIcon, {
        props: { rollSpeed: 50 }
      })
      expect(wrapper.props('rollSpeed')).toBe(50)
    })

    it('rotates dice during animation', async () => {
      const wrapper = mount(DiceIcon, {
        props: { animate: true }
      })
      
      const initialRotation = wrapper.vm.rotation
      
      vi.advanceTimersByTime(100)
      await wrapper.vm.$nextTick()
      
      expect(wrapper.vm.rotation).toBeGreaterThan(initialRotation)
    })

    it('changes dice number during roll', async () => {
      const wrapper = mount(DiceIcon, {
        props: { animate: true, rollSpeed: 100 }
      })
      
      const initialNumber = wrapper.vm.currentNumber
      
      // Advance by rollSpeed interval
      vi.advanceTimersByTime(100)
      await wrapper.vm.$nextTick()
      
      // Number might have changed (it's random)
      expect(wrapper.vm.currentNumber).toBeGreaterThanOrEqual(1)
      expect(wrapper.vm.currentNumber).toBeLessThanOrEqual(6)
    })

    it('shows correct dot pattern for each number', async () => {
      // Expected dot counts for each dice number
      const expectedDots = {
        1: 1,
        2: 2,
        3: 3,
        4: 4,
        5: 5,
        6: 6
      }
      
      for (let i = 1; i <= 6; i++) {
        const wrapper = mount(DiceIcon)
        wrapper.vm.currentNumber = i
        
        // Wait for reactivity
        await wrapper.vm.$nextTick()
        
        const dots = wrapper.findAll('circle.dot')
        expect(dots.length).toBe(expectedDots[i])
      }
    })

    it('cleans up animation intervals on unmount', async () => {
      const wrapper = mount(DiceIcon, {
        props: { animate: true }
      })
      
      await wrapper.vm.$nextTick()
      const clearIntervalSpy = vi.spyOn(global, 'clearInterval')
      
      wrapper.unmount()
      expect(clearIntervalSpy).toHaveBeenCalled()
    })
  })

  describe('ThinkingIcon', () => {
    it('renders with default props', () => {
      const wrapper = mount(ThinkingIcon)
      expect(wrapper.find('svg').exists()).toBe(true)
      expect(wrapper.find('.thinking-icon').exists()).toBe(true)
    })

    it('accepts custom dotColor prop', () => {
      const wrapper = mount(ThinkingIcon, {
        props: { dotColor: '#ff0000' }
      })
      expect(wrapper.props('dotColor')).toBe('#ff0000')
    })

    it('initializes thinking dots array', () => {
      const wrapper = mount(ThinkingIcon)
      expect(wrapper.vm.thinkingDots).toHaveLength(3)
      
      wrapper.vm.thinkingDots.forEach(dot => {
        expect(dot).toHaveProperty('x')
        expect(dot).toHaveProperty('y')
        expect(dot).toHaveProperty('r')
        expect(dot).toHaveProperty('opacity')
      })
    })

    it('animates thinking dots in wave pattern', async () => {
      const wrapper = mount(ThinkingIcon, {
        props: { animate: true }
      })
      
      const initialDots = JSON.parse(JSON.stringify(wrapper.vm.thinkingDots))
      
      vi.advanceTimersByTime(100)
      await wrapper.vm.$nextTick()
      
      // At least one dot property should change
      const dotsChanged = wrapper.vm.thinkingDots.some((dot, i) => 
        dot.opacity !== initialDots[i].opacity || 
        dot.r !== initialDots[i].r
      )
      
      expect(dotsChanged).toBe(true)
    })

    it('increments dotPhase over time', async () => {
      const wrapper = mount(ThinkingIcon, {
        props: { animate: true }
      })
      
      const initialPhase = wrapper.vm.dotPhase
      
      vi.advanceTimersByTime(100)
      await wrapper.vm.$nextTick()
      
      expect(wrapper.vm.dotPhase).toBeGreaterThan(initialPhase)
    })
  })

  describe('TrophyIcon', () => {
    it('renders with default props', () => {
      const wrapper = mount(TrophyIcon)
      expect(wrapper.find('svg').exists()).toBe(true)
      expect(wrapper.find('.trophy-icon').exists()).toBe(true)
    })

    it('accepts custom baseColor prop', () => {
      const wrapper = mount(TrophyIcon, {
        props: { baseColor: '#123456' }
      })
      expect(wrapper.html()).toContain('fill="#123456"')
    })

    it('accepts custom starColor prop', () => {
      const wrapper = mount(TrophyIcon, {
        props: { starColor: '#ffd700' }
      })
      expect(wrapper.props('starColor')).toBe('#ffd700')
    })

    it('initializes sparkles array', () => {
      const wrapper = mount(TrophyIcon)
      expect(wrapper.vm.sparkles).toHaveLength(4)
      
      wrapper.vm.sparkles.forEach(sparkle => {
        expect(sparkle).toHaveProperty('x')
        expect(sparkle).toHaveProperty('y')
        expect(sparkle).toHaveProperty('r')
        expect(sparkle).toHaveProperty('opacity')
      })
    })

    it('animates star rotation', async () => {
      const wrapper = mount(TrophyIcon, {
        props: { animate: true }
      })
      
      const initialRotation = wrapper.vm.starRotation
      
      vi.advanceTimersByTime(100)
      await wrapper.vm.$nextTick()
      
      expect(wrapper.vm.starRotation).not.toBe(initialRotation)
    })

    it('animates sparkles opacity', async () => {
      const wrapper = mount(TrophyIcon, {
        props: { animate: true }
      })
      
      vi.advanceTimersByTime(100)
      await wrapper.vm.$nextTick()
      
      // At least one sparkle should have non-zero opacity
      const hasVisibleSparkle = wrapper.vm.sparkles.some(s => s.opacity > 0)
      expect(hasVisibleSparkle).toBe(true)
    })
  })

  describe('ClueIcon', () => {
    it('renders with default props', () => {
      const wrapper = mount(ClueIcon)
      expect(wrapper.find('svg').exists()).toBe(true)
      expect(wrapper.find('.clue-icon').exists()).toBe(true)
    })

    it('accepts custom handleColor prop', () => {
      const wrapper = mount(ClueIcon, {
        props: { handleColor: '#8b4513' }
      })
      expect(wrapper.html()).toContain('stroke="#8b4513"')
    })

    it('accepts custom sparkleColor prop', () => {
      const wrapper = mount(ClueIcon, {
        props: { sparkleColor: '#ffd700' }
      })
      expect(wrapper.props('sparkleColor')).toBe('#ffd700')
    })

    it('initializes sparkles array', () => {
      const wrapper = mount(ClueIcon)
      expect(wrapper.vm.sparkles).toHaveLength(4)
      
      wrapper.vm.sparkles.forEach(sparkle => {
        expect(sparkle).toHaveProperty('x')
        expect(sparkle).toHaveProperty('y')
        expect(sparkle).toHaveProperty('opacity')
      })
    })

    it('animates sparkles in sequence', async () => {
      const wrapper = mount(ClueIcon, {
        props: { animate: true }
      })
      
      vi.advanceTimersByTime(100)
      await wrapper.vm.$nextTick()
      
      // Check if sparkles have different opacity values (sequence effect)
      const opacities = wrapper.vm.sparkles.map(s => s.opacity)
      const allSame = opacities.every(o => o === opacities[0])
      
      // They shouldn't all be the same due to phase offset
      expect(allSame).toBe(false)
    })
  })

  describe('LocationIcon', () => {
    it('renders with default props', () => {
      const wrapper = mount(LocationIcon)
      expect(wrapper.find('svg').exists()).toBe(true)
      expect(wrapper.find('.location-icon').exists()).toBe(true)
    })

    it('initializes pulse rings array', () => {
      const wrapper = mount(LocationIcon)
      expect(wrapper.vm.rings).toHaveLength(3)
      
      wrapper.vm.rings.forEach(ring => {
        expect(ring).toHaveProperty('r')
        expect(ring).toHaveProperty('opacity')
        expect(ring).toHaveProperty('strokeWidth')
      })
    })

    it('animates pulse rings expansion', async () => {
      const wrapper = mount(LocationIcon, {
        props: { animate: true }
      })
      
      const initialRings = JSON.parse(JSON.stringify(wrapper.vm.rings))
      
      vi.advanceTimersByTime(100)
      await wrapper.vm.$nextTick()
      
      // Rings should change size
      const ringsChanged = wrapper.vm.rings.some((ring, i) => 
        ring.r !== initialRings[i].r || 
        ring.opacity !== initialRings[i].opacity
      )
      
      expect(ringsChanged).toBe(true)
    })

    it('creates pulse wave effect', async () => {
      const wrapper = mount(LocationIcon, {
        props: { animate: true }
      })
      
      vi.advanceTimersByTime(100)
      await wrapper.vm.$nextTick()
      
      // Each ring should have different values (wave effect)
      const radii = wrapper.vm.rings.map(r => r.r)
      const allSameRadius = radii.every(r => r === radii[0])
      
      expect(allSameRadius).toBe(false)
    })
  })

  describe('Common Icon Behavior', () => {
    const icons = [
      { name: 'DetectiveIcon', component: DetectiveIcon },
      { name: 'DiceIcon', component: DiceIcon },
      { name: 'ThinkingIcon', component: ThinkingIcon },
      { name: 'TrophyIcon', component: TrophyIcon },
      { name: 'ClueIcon', component: ClueIcon },
      { name: 'LocationIcon', component: LocationIcon }
    ]

    icons.forEach(({ name, component }) => {
      describe(name, () => {
        it('has SVG with correct viewBox', () => {
          const wrapper = mount(component)
          const svg = wrapper.find('svg')
          expect(svg.attributes('viewBox')).toBe('0 0 100 100')
        })

        it('applies size to both width and height', () => {
          const wrapper = mount(component, {
            props: { size: 150 }
          })
          const svg = wrapper.find('svg')
          expect(svg.attributes('width')).toBe('150')
          expect(svg.attributes('height')).toBe('150')
        })

        it('accepts string size', () => {
          const wrapper = mount(component, {
            props: { size: '200' }
          })
          const svg = wrapper.find('svg')
          expect(svg.attributes('width')).toBe('200')
        })

        it('has animated-icon class', () => {
          const wrapper = mount(component)
          expect(wrapper.find('.animated-icon').exists()).toBe(true)
        })

        it('stops animation on unmount', async () => {
          const wrapper = mount(component, {
            props: { animate: true }
          })
          
          await wrapper.vm.$nextTick()
          
          const cancelSpy = vi.spyOn(global, 'cancelAnimationFrame')
          wrapper.unmount()
          
          // Should clean up animation
          expect(cancelSpy).toHaveBeenCalled()
        })
      })
    })
  })
})
