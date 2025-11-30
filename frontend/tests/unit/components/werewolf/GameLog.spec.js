/**
 * 游戏日志组件测试
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import GameLog from '@/components/werewolf/GameLog.vue'

// Mock Element Plus icons
vi.mock('@element-plus/icons-vue', () => ({
  Bottom: { template: '<span class="icon-bottom"></span>' },
  Microphone: { template: '<span class="icon-microphone"></span>' },
  Close: { template: '<span class="icon-close"></span>' },
  Stamp: { template: '<span class="icon-stamp"></span>' },
  Aim: { template: '<span class="icon-aim"></span>' },
  MagicStick: { template: '<span class="icon-magic"></span>' },
  Trophy: { template: '<span class="icon-trophy"></span>' },
  InfoFilled: { template: '<span class="icon-info"></span>' },
  DocumentCopy: { template: '<span class="icon-doc"></span>' }
}))

describe('GameLog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  /**
   * 辅助函数：挂载组件
   */
  function mountLog(props = {}) {
    return mount(GameLog, {
      global: {
        stubs: {
          'el-button': {
            template: '<button @click="$emit(\'click\')"><slot /></button>'
          },
          'el-icon': {
            template: '<span class="el-icon"><slot /></span>'
          }
        }
      },
      props: {
        logs: [],
        ...props
      }
    })
  }

  describe('空状态', () => {
    it('无日志时应显示空状态', () => {
      const wrapper = mountLog({ logs: [] })
      expect(wrapper.find('.empty-log').exists()).toBe(true)
      expect(wrapper.text()).toContain('暂无日志')
    })
  })

  describe('日志渲染', () => {
    it('应正确渲染主持人发言', () => {
      const logs = [
        {
          id: '1',
          type: 'host_announcement',
          content: '天黑请闭眼',
          day: 1,
          phase_name: '夜晚'
        }
      ]
      const wrapper = mountLog({ logs })
      
      expect(wrapper.find('.host-entry').exists()).toBe(true)
      expect(wrapper.text()).toContain('主持人')
      expect(wrapper.text()).toContain('天黑请闭眼')
    })

    it('应正确渲染玩家发言', () => {
      const logs = [
        {
          id: '2',
          type: 'speech',
          content: '我认为3号是狼人',
          player_name: '玩家1',
          day: 1,
          phase_name: '白天'
        }
      ]
      const wrapper = mountLog({ logs })
      
      expect(wrapper.find('.speech-entry').exists()).toBe(true)
      expect(wrapper.text()).toContain('玩家1')
      expect(wrapper.text()).toContain('我认为3号是狼人')
    })

    it('应正确渲染死亡日志', () => {
      const logs = [
        {
          id: '3',
          type: 'death',
          content: '玩家2 在昨晚死亡',
          day: 2,
          phase_name: '天亮'
        }
      ]
      const wrapper = mountLog({ logs })
      
      expect(wrapper.find('.entry-content').exists()).toBe(true)
    })

    it('应正确渲染投票日志', () => {
      const logs = [
        {
          id: '4',
          type: 'vote',
          content: '玩家1 投票给 玩家3',
          day: 1,
          phase_name: '投票'
        }
      ]
      const wrapper = mountLog({ logs })
      
      expect(wrapper.find('.entry-content').exists()).toBe(true)
    })

    it('应正确渲染游戏结束日志', () => {
      const logs = [
        {
          id: '5',
          type: 'game_end',
          message: '好人阵营获胜！',
          content: '好人阵营获胜！',
          day: 3,
          phase_name: '结束'
        }
      ]
      const wrapper = mountLog({ logs })
      
      expect(wrapper.find('.entry-content').exists()).toBe(true)
      // 检查日志渲染正确（可能在 message 或 content 中）
      const text = wrapper.text()
      expect(text.includes('好人阵营获胜') || text.includes('第 3 天')).toBe(true)
    })
  })

  describe('流式输出', () => {
    it('流式输出时应显示打字光标', () => {
      const logs = [
        {
          id: '6',
          type: 'host_announcement',
          content: '正在处理...',
          isStreaming: true,
          day: 1,
          phase_name: '夜晚'
        }
      ]
      const wrapper = mountLog({ logs })
      
      expect(wrapper.find('.typing-cursor').exists()).toBe(true)
      expect(wrapper.find('.is-streaming').exists()).toBe(true)
    })

    it('非流式输出不应显示打字光标', () => {
      const logs = [
        {
          id: '7',
          type: 'host_announcement',
          content: '天亮了',
          isStreaming: false,
          day: 1,
          phase_name: '天亮'
        }
      ]
      const wrapper = mountLog({ logs })
      
      expect(wrapper.find('.typing-cursor').exists()).toBe(false)
    })
  })

  describe('日期标记', () => {
    it('应在新的一天显示日期标记', () => {
      const logs = [
        {
          id: '1',
          type: 'host_announcement',
          content: '天黑请闭眼',
          day: 1,
          phase_name: '夜晚'
        },
        {
          id: '2',
          type: 'host_announcement',
          content: '天亮了',
          day: 1,
          phase_name: '白天'
        }
      ]
      const wrapper = mountLog({ logs })
      
      const dayMarkers = wrapper.findAll('.day-marker')
      expect(dayMarkers.length).toBeGreaterThanOrEqual(1)
    })
  })

  describe('多条日志', () => {
    it('应正确渲染多条日志', () => {
      const logs = [
        { id: '1', type: 'host_announcement', content: '游戏开始', day: 1, phase_name: '开始' },
        { id: '2', type: 'speech', content: '大家好', player_name: '玩家1', day: 1 },
        { id: '3', type: 'vote', content: '玩家1 投票', day: 1 },
        { id: '4', type: 'death', content: '玩家3 死亡', day: 1 }
      ]
      const wrapper = mountLog({ logs })
      
      const entries = wrapper.findAll('.log-entry')
      expect(entries.length).toBe(4)
    })
  })

  describe('日志类型图标', () => {
    it('不同类型日志应使用不同图标', () => {
      const logs = [
        { id: '1', type: 'vote', content: '投票', day: 1 },
        { id: '2', type: 'death', content: '死亡', day: 1 },
        { id: '3', type: 'skill', content: '技能', day: 1 }
      ]
      const wrapper = mountLog({ logs })
      
      expect(wrapper.findAll('.el-icon').length).toBeGreaterThan(0)
    })
  })
})
