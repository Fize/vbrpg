/**
 * 主持人公告组件测试
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import HostAnnouncement from '@/components/werewolf/HostAnnouncement.vue'

// Mock Element Plus icons
vi.mock('@element-plus/icons-vue', () => ({
  Microphone: { template: '<span class="icon-microphone"></span>' },
  Close: { template: '<span class="icon-close"></span>' }
}))

describe('HostAnnouncement', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  /**
   * 辅助函数：挂载组件
   */
  function mountAnnouncement(props = {}) {
    return mount(HostAnnouncement, {
      global: {
        stubs: {
          'el-button': {
            template: '<button @click="$emit(\'click\')"><slot /></button>',
            props: ['type', 'circle']
          },
          'el-icon': {
            template: '<span class="el-icon"><slot /></span>'
          }
        }
      },
      props: {
        content: '天黑请闭眼',
        ...props
      }
    })
  }

  describe('基本渲染', () => {
    it('应正确渲染公告内容', () => {
      const wrapper = mountAnnouncement({ content: '游戏开始' })
      expect(wrapper.text()).toContain('游戏开始')
    })

    it('应显示主持人标识', () => {
      const wrapper = mountAnnouncement()
      expect(wrapper.text()).toContain('主持人')
    })

    it('应显示主持人图标', () => {
      const wrapper = mountAnnouncement()
      expect(wrapper.find('.host-avatar').exists()).toBe(true)
    })
  })

  describe('可见性', () => {
    it('visible 为 true 时应显示', () => {
      const wrapper = mountAnnouncement({ visible: true })
      expect(wrapper.find('.is-visible').exists()).toBe(true)
    })

    it('visible 为 false 时应隐藏', () => {
      const wrapper = mountAnnouncement({ visible: false })
      expect(wrapper.find('.is-visible').exists()).toBe(false)
    })
  })

  describe('流式输出状态', () => {
    it('流式输出时应添加 is-streaming 类', () => {
      const wrapper = mountAnnouncement({ isStreaming: true })
      expect(wrapper.find('.is-streaming').exists()).toBe(true)
    })

    it('流式输出时应显示打字光标', () => {
      const wrapper = mountAnnouncement({ isStreaming: true })
      expect(wrapper.find('.typing-cursor').exists()).toBe(true)
    })

    it('非流式输出时不应显示打字光标', () => {
      const wrapper = mountAnnouncement({ isStreaming: false })
      expect(wrapper.find('.typing-cursor').exists()).toBe(false)
    })

    it('流式输出时不应显示关闭按钮', () => {
      const wrapper = mountAnnouncement({ isStreaming: true, closable: true })
      expect(wrapper.find('.close-btn').exists()).toBe(false)
    })
  })

  describe('关闭按钮', () => {
    it('closable 为 true 且非流式时应显示关闭按钮', () => {
      const wrapper = mountAnnouncement({ closable: true, isStreaming: false })
      expect(wrapper.find('.close-btn').exists()).toBe(true)
    })

    it('closable 为 false 时不应显示关闭按钮', () => {
      const wrapper = mountAnnouncement({ closable: false, isStreaming: false })
      expect(wrapper.find('.close-btn').exists()).toBe(false)
    })

    it('点击关闭按钮应触发 close 事件', async () => {
      const wrapper = mountAnnouncement({ closable: true, isStreaming: false })
      const closeBtn = wrapper.find('.close-btn')
      await closeBtn.trigger('click')
      expect(wrapper.emitted('close')).toBeTruthy()
    })
  })

  describe('公告类型', () => {
    it('应显示游戏开始类型标签', () => {
      const wrapper = mountAnnouncement({ announcementType: 'game_start' })
      expect(wrapper.text()).toContain('游戏开始')
    })

    it('应显示夜幕降临类型标签', () => {
      const wrapper = mountAnnouncement({ announcementType: 'night_start' })
      expect(wrapper.text()).toContain('夜幕降临')
    })

    it('应显示天亮了类型标签', () => {
      const wrapper = mountAnnouncement({ announcementType: 'dawn' })
      expect(wrapper.text()).toContain('天亮了')
    })

    it('应显示投票开始类型标签', () => {
      const wrapper = mountAnnouncement({ announcementType: 'vote_start' })
      expect(wrapper.text()).toContain('投票开始')
    })

    it('应显示投票结果类型标签', () => {
      const wrapper = mountAnnouncement({ announcementType: 'vote_result' })
      expect(wrapper.text()).toContain('投票结果')
    })

    it('应显示游戏结束类型标签', () => {
      const wrapper = mountAnnouncement({ announcementType: 'game_end' })
      expect(wrapper.text()).toContain('游戏结束')
    })

    it('应显示狼人行动类型标签', () => {
      const wrapper = mountAnnouncement({ announcementType: 'werewolf_action' })
      expect(wrapper.text()).toContain('狼人行动')
    })

    it('应显示预言家行动类型标签', () => {
      const wrapper = mountAnnouncement({ announcementType: 'seer_action' })
      expect(wrapper.text()).toContain('预言家行动')
    })

    it('应显示女巫行动类型标签', () => {
      const wrapper = mountAnnouncement({ announcementType: 'witch_action' })
      expect(wrapper.text()).toContain('女巫行动')
    })
  })

  describe('内容更新', () => {
    it('内容变化时应更新显示', async () => {
      const wrapper = mountAnnouncement({ content: '初始内容' })
      expect(wrapper.text()).toContain('初始内容')
      
      await wrapper.setProps({ content: '更新后的内容' })
      expect(wrapper.text()).toContain('更新后的内容')
    })
  })
})
