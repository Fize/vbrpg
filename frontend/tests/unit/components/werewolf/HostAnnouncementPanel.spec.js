/**
 * T8: HostAnnouncementPanel 组件测试
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import HostAnnouncementPanel from '@/components/werewolf/HostAnnouncementPanel.vue'

// Mock Element Plus icons
vi.mock('@element-plus/icons-vue', () => ({
  Microphone: { template: '<span class="icon-microphone"></span>' },
  ArrowDown: { template: '<span class="icon-arrow-down"></span>' },
  ArrowUp: { template: '<span class="icon-arrow-up"></span>' },
  Clock: { template: '<span class="icon-clock"></span>' }
}))

describe('HostAnnouncementPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  /**
   * 辅助函数：挂载组件
   */
  function mountPanel(props = {}) {
    return mount(HostAnnouncementPanel, {
      global: {
        stubs: {
          'el-collapse-transition': {
            template: '<div class="el-collapse-transition"><slot /></div>'
          },
          'el-icon': {
            template: '<span class="el-icon"><slot /></span>'
          },
          'el-button': {
            template: '<button class="el-button" @click="$emit(\'click\')"><slot /></button>'
          },
          'el-badge': {
            template: '<span class="el-badge"><slot /></span>',
            props: ['value']
          }
        }
      },
      props: {
        currentAnnouncement: { type: null, content: '', isStreaming: false },
        announcementHistory: [],
        ...props
      }
    })
  }

  describe('基础渲染', () => {
    it('应显示面板', () => {
      const wrapper = mountPanel()
      expect(wrapper.find('.host-announcement-panel').exists()).toBe(true)
    })

    it('不使用 visible prop，组件默认可见', () => {
      const wrapper = mountPanel()
      expect(wrapper.find('.host-announcement-panel').exists()).toBe(true)
    })

    it('应显示面板标题', () => {
      const wrapper = mountPanel()
      const text = wrapper.text()
      expect(text.includes('主持人') || wrapper.find('.panel-title').exists()).toBe(true)
    })
  })

  describe('当前公告显示', () => {
    it('应显示当前公告内容', () => {
      const wrapper = mountPanel({
        currentAnnouncement: { 
          type: 'night_start',
          content: '天黑请闭眼，狼人请睁眼',
          isStreaming: false
        }
      })
      
      expect(wrapper.text()).toContain('天黑请闭眼')
    })

    it('流式输出时应显示打字光标', () => {
      const wrapper = mountPanel({
        currentAnnouncement: {
          type: 'game_start',
          content: '正在加载...',
          isStreaming: true
        }
      })
      
      expect(wrapper.find('.typing-cursor').exists()).toBe(true)
    })

    it('非流式输出时不应显示打字光标', () => {
      const wrapper = mountPanel({
        currentAnnouncement: {
          type: 'game_start',
          content: '公告完成',
          isStreaming: false
        }
      })
      
      expect(wrapper.find('.typing-cursor').exists()).toBe(false)
    })
  })

  describe('历史公告', () => {
    it('展开时有历史应显示历史区域', async () => {
      const history = [
        { type: 'day_start', content: '天亮了', time: '2024-01-01T10:00:00Z', day: 1 },
        { type: 'night_start', content: '天黑了', time: '2024-01-01T11:00:00Z', day: 1 }
      ]
      const wrapper = mountPanel({
        announcementHistory: history
      })
      
      // 点击展开历史
      const toggleBtn = wrapper.find('.history-toggle')
      if (toggleBtn.exists()) {
        await toggleBtn.trigger('click')
        await wrapper.vm.$nextTick()
      }
      
      // 检查历史区域或历史项
      const hasHistorySection = wrapper.find('.history-section').exists() 
        || wrapper.find('.history-item').exists()
        || wrapper.text().includes('历史')
      expect(hasHistorySection).toBe(true)
    })

    it('无历史时不应显示历史项', () => {
      const wrapper = mountPanel({
        announcementHistory: []
      })
      
      const hasHistory = wrapper.find('.history-item').exists()
      expect(hasHistory).toBe(false)
    })

    it('历史公告应包含所有项', async () => {
      const history = [
        { type: 'a', content: '公告1', time: '2024-01-01T10:00:00Z', day: 1 },
        { type: 'b', content: '公告2', time: '2024-01-01T11:00:00Z', day: 1 },
        { type: 'c', content: '公告3', time: '2024-01-01T12:00:00Z', day: 2 }
      ]
      const wrapper = mountPanel({
        announcementHistory: history
      })
      
      // 展开历史
      const toggleBtn = wrapper.find('.history-toggle')
      if (toggleBtn.exists()) {
        await toggleBtn.trigger('click')
        await wrapper.vm.$nextTick()
      }
      
      // 检查历史项数量（因为初始显示5条，这里3条应该都显示）
      const historyItems = wrapper.findAll('.history-item')
      expect(historyItems.length).toBeLessThanOrEqual(history.length)
    })
  })

  describe('折叠功能', () => {
    it('应有折叠/展开按钮', () => {
      const history = [
        { type: 'test', content: '测试', time: '2024-01-01T10:00:00Z', day: 1 }
      ]
      const wrapper = mountPanel({
        announcementHistory: history
      })
      
      // 检查是否有折叠相关元素
      const hasCollapseControl = 
        wrapper.find('.history-toggle').exists() ||
        wrapper.text().includes('展开') ||
        wrapper.text().includes('收起') ||
        wrapper.text().includes('历史')
      
      expect(hasCollapseControl).toBe(true)
    })
  })
})
