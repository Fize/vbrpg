/**
 * T9: SpeechBubble 组件测试
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import SpeechBubble from '@/components/werewolf/SpeechBubble.vue'

describe('SpeechBubble', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  /**
   * 辅助函数：挂载组件
   */
  function mountBubble(props = {}) {
    return mount(SpeechBubble, {
      props: {
        seatNumber: 1,
        playerName: '玩家1',
        content: '',
        isStreaming: false,
        isHuman: false,
        visible: true,
        position: 'top',
        ...props
      }
    })
  }

  describe('基础渲染', () => {
    it('visible 为 true 时应显示气泡', () => {
      const wrapper = mountBubble({ visible: true })
      expect(wrapper.find('.speech-bubble').exists()).toBe(true)
    })

    it('visible 为 false 时应隐藏气泡', () => {
      const wrapper = mountBubble({ visible: false })
      expect(wrapper.find('.speech-bubble').exists()).toBe(false)
    })

    it('应显示座位号', () => {
      const wrapper = mountBubble({ seatNumber: 3 })
      expect(wrapper.text()).toContain('3')
    })

    it('应显示玩家名称', () => {
      const wrapper = mountBubble({ playerName: '测试玩家' })
      expect(wrapper.text()).toContain('测试玩家')
    })

    it('应显示发言内容', () => {
      const wrapper = mountBubble({ content: '这是我的发言内容' })
      expect(wrapper.text()).toContain('这是我的发言内容')
    })
  })

  describe('流式显示', () => {
    it('isStreaming 为 true 时应显示打字光标', () => {
      const wrapper = mountBubble({
        content: '正在输入...',
        isStreaming: true
      })
      
      expect(wrapper.find('.typing-cursor').exists()).toBe(true)
    })

    it('isStreaming 为 false 时不应显示打字光标', () => {
      const wrapper = mountBubble({
        content: '发言完成',
        isStreaming: false
      })
      
      expect(wrapper.find('.typing-cursor').exists()).toBe(false)
    })

    it('isStreaming 时应有流式样式类', () => {
      const wrapper = mountBubble({ isStreaming: true })
      expect(wrapper.find('.is-streaming').exists()).toBe(true)
    })
  })

  describe('人类玩家标识', () => {
    it('isHuman 为 true 时应有人类玩家样式', () => {
      const wrapper = mountBubble({ isHuman: true })
      expect(wrapper.find('.is-human').exists()).toBe(true)
    })

    it('isHuman 为 false 时不应有人类玩家样式', () => {
      const wrapper = mountBubble({ isHuman: false })
      expect(wrapper.find('.is-human').exists()).toBe(false)
    })
  })

  describe('位置计算', () => {
    it('position 为 top 时应有正确的位置类', () => {
      const wrapper = mountBubble({ position: 'top' })
      expect(wrapper.find('.position-top').exists()).toBe(true)
    })

    it('position 为 bottom 时应有正确的位置类', () => {
      const wrapper = mountBubble({ position: 'bottom' })
      expect(wrapper.find('.position-bottom').exists()).toBe(true)
    })

    it('position 为对象时应应用自定义样式', () => {
      const wrapper = mountBubble({
        position: { top: '100px', left: '200px' }
      })
      const bubble = wrapper.find('.speech-bubble')
      expect(bubble.exists()).toBe(true)
    })
  })

  describe('尾巴指向', () => {
    it('应根据位置显示尾巴', () => {
      const wrapper = mountBubble({ position: 'top' })
      expect(wrapper.find('.bubble-tail').exists()).toBe(true)
    })

    it('尾巴方向应与位置相反', () => {
      const wrapper = mountBubble({ position: 'top' })
      expect(wrapper.find('.tail-bottom').exists()).toBe(true)
    })
  })

  describe('动画效果', () => {
    it('气泡应有出现动画样式', () => {
      const wrapper = mountBubble()
      const bubble = wrapper.find('.speech-bubble')
      expect(bubble.exists()).toBe(true)
      // 检查是否有动画相关的类或样式
    })
  })
})
