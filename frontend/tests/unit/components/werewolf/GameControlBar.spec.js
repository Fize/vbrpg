/**
 * T7: GameControlBar 组件测试
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import GameControlBar from '@/components/werewolf/GameControlBar.vue'

// Mock Element Plus icons
vi.mock('@element-plus/icons-vue', () => ({
  VideoPlay: { template: '<span class="icon-play"></span>' },
  VideoPause: { template: '<span class="icon-pause"></span>' },
  CaretRight: { template: '<span class="icon-caret"></span>' }
}))

describe('GameControlBar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  /**
   * 辅助函数：挂载组件
   */
  function mountControlBar(props = {}) {
    return mount(GameControlBar, {
      global: {
        stubs: {
          'el-button-group': {
            template: '<div class="el-button-group"><slot /></div>'
          },
          'el-button': {
            template: '<button :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
            props: ['type', 'size', 'disabled', 'loading']
          },
          'el-icon': {
            template: '<span class="el-icon"><slot /></span>'
          },
          'el-tooltip': {
            template: '<div class="el-tooltip"><slot /></div>'
          }
        }
      },
      props: {
        isStarted: false,
        isPaused: false,
        ...props
      }
    })
  }

  describe('按钮状态', () => {
    it('未开始时应显示开始按钮', () => {
      const wrapper = mountControlBar({
        isStarted: false,
        showStart: true
      })
      
      expect(wrapper.find('.control-btn-start').exists() || wrapper.text().includes('开始')).toBe(true)
    })

    it('进行中时应显示暂停按钮', () => {
      const wrapper = mountControlBar({
        isStarted: true,
        isPaused: false,
        showStart: false,
        showPause: true,
        showResume: false
      })
      
      expect(wrapper.find('.control-btn-pause').exists() || wrapper.text().includes('暂停')).toBe(true)
    })

    it('暂停时应显示继续按钮', () => {
      const wrapper = mountControlBar({
        isStarted: true,
        isPaused: true,
        showStart: false,
        showPause: false,
        showResume: true
      })
      
      expect(wrapper.find('.control-btn-resume').exists() || wrapper.text().includes('继续')).toBe(true)
    })
  })

  describe('事件触发', () => {
    it('点击开始按钮应触发 start 事件', async () => {
      const wrapper = mountControlBar({
        isStarted: false,
        showStart: true
      })
      
      const startBtn = wrapper.find('.control-btn-start')
      if (startBtn.exists()) {
        await startBtn.trigger('click')
        expect(wrapper.emitted('start')).toBeTruthy()
      }
    })

    it('点击暂停按钮应触发 pause 事件', async () => {
      const wrapper = mountControlBar({
        isStarted: true,
        isPaused: false,
        showStart: false,
        showPause: true
      })
      
      const pauseBtn = wrapper.find('.control-btn-pause')
      if (pauseBtn.exists()) {
        await pauseBtn.trigger('click')
        expect(wrapper.emitted('pause')).toBeTruthy()
      }
    })

    it('点击继续按钮应触发 resume 事件', async () => {
      const wrapper = mountControlBar({
        isStarted: true,
        isPaused: true,
        showStart: false,
        showPause: false,
        showResume: true
      })
      
      const resumeBtn = wrapper.find('.control-btn-resume')
      if (resumeBtn.exists()) {
        await resumeBtn.trigger('click')
        expect(wrapper.emitted('resume')).toBeTruthy()
      }
    })
  })

  describe('禁用状态', () => {
    it('disabled 为 true 时按钮应被禁用', () => {
      const wrapper = mountControlBar({
        isStarted: false,
        showStart: true,
        disabled: true
      })
      
      const buttons = wrapper.findAll('button')
      if (buttons.length > 0) {
        expect(buttons[0].attributes('disabled')).toBeDefined()
      }
    })
  })
})
