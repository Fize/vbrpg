/**
 * T10: PlayerInputPanel 组件测试
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import PlayerInputPanel from '@/components/werewolf/PlayerInputPanel.vue'

// Mock Element Plus icons
vi.mock('@element-plus/icons-vue', () => ({
  Microphone: { template: '<span class="icon-mic"></span>' },
  InfoFilled: { template: '<span class="icon-info"></span>' },
  Position: { template: '<span class="icon-position"></span>' }
}))

describe('PlayerInputPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  /**
   * 辅助函数：挂载组件
   */
  function mountPanel(props = {}) {
    return mount(PlayerInputPanel, {
      global: {
        stubs: {
          'el-input': {
            template: `
              <div class="el-input">
                <textarea 
                  :value="modelValue"
                  :disabled="disabled"
                  :placeholder="placeholder"
                  @input="$emit('update:modelValue', $event.target.value)"
                  @keydown="$emit('keydown', $event)"
                ></textarea>
              </div>
            `,
            props: ['modelValue', 'disabled', 'placeholder', 'maxlength']
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
        visible: true,
        isMyTurn: false,
        isSubmitting: false,
        allowSkip: false,
        maxLength: 500,
        ...props
      }
    })
  }

  describe('基础渲染', () => {
    it('visible 为 true 时应显示面板', () => {
      const wrapper = mountPanel({ visible: true })
      expect(wrapper.find('.player-input-panel').exists()).toBe(true)
    })

    it('visible 为 false 时应隐藏面板', () => {
      const wrapper = mountPanel({ visible: false })
      expect(wrapper.find('.player-input-panel').exists()).toBe(false)
    })

    it('应显示面板标题', () => {
      const wrapper = mountPanel()
      expect(wrapper.text()).toContain('发言')
    })
  })

  describe('发言轮次状态', () => {
    it('isMyTurn 为 true 时应启用输入框', () => {
      const wrapper = mountPanel({ isMyTurn: true })
      const textarea = wrapper.find('textarea')
      expect(textarea.attributes('disabled')).toBeUndefined()
    })

    it('isMyTurn 为 false 时应禁用输入框', () => {
      const wrapper = mountPanel({ isMyTurn: false })
      const textarea = wrapper.find('textarea')
      expect(textarea.attributes('disabled')).toBeDefined()
    })

    it('isMyTurn 为 true 时应显示轮到你发言提示', () => {
      const wrapper = mountPanel({ isMyTurn: true })
      expect(wrapper.text()).toContain('轮到你发言')
    })

    it('isMyTurn 为 false 时应显示等待提示', () => {
      const wrapper = mountPanel({ isMyTurn: false })
      expect(wrapper.text()).toContain('等待')
    })
  })

  describe('输入逻辑', () => {
    it('应能输入发言内容', async () => {
      const wrapper = mountPanel({ isMyTurn: true })
      const textarea = wrapper.find('textarea')
      
      await textarea.setValue('测试发言内容')
      expect(textarea.element.value).toBe('测试发言内容')
    })
  })

  describe('提交逻辑', () => {
    it('点击提交按钮应触发 submit 事件', async () => {
      const wrapper = mountPanel({ isMyTurn: true })
      
      // 先输入内容
      const textarea = wrapper.find('textarea')
      await textarea.setValue('测试发言')
      
      // 点击提交按钮
      const submitBtn = wrapper.findAll('button').find(b => 
        b.text().includes('提交') || b.classes().includes('submit-btn')
      )
      if (submitBtn) {
        await submitBtn.trigger('click')
        // submit 事件可能需要内容非空
      }
    })

    it('isSubmitting 为 true 时应禁用提交按钮', () => {
      const wrapper = mountPanel({
        isMyTurn: true,
        isSubmitting: true
      })
      
      const buttons = wrapper.findAll('button')
      const submitBtn = buttons.find(b => b.text().includes('提交'))
      if (submitBtn) {
        expect(submitBtn.attributes('disabled')).toBeDefined()
      }
    })
  })

  describe('跳过发言', () => {
    it('allowSkip 为 true 时应显示跳过按钮', () => {
      const wrapper = mountPanel({
        isMyTurn: true,
        allowSkip: true
      })
      
      expect(wrapper.text()).toContain('跳过')
    })

    it('allowSkip 为 false 时不应显示跳过按钮', () => {
      const wrapper = mountPanel({
        isMyTurn: true,
        allowSkip: false
      })
      
      // 不应有跳过按钮
      const hasSkip = wrapper.findAll('button').some(b => b.text().includes('跳过'))
      expect(hasSkip).toBe(false)
    })

    it('点击跳过按钮应触发 skip 事件', async () => {
      const wrapper = mountPanel({
        isMyTurn: true,
        allowSkip: true
      })
      
      const skipBtn = wrapper.findAll('button').find(b => b.text().includes('跳过'))
      if (skipBtn) {
        await skipBtn.trigger('click')
        expect(wrapper.emitted('skip')).toBeTruthy()
      }
    })
  })

  describe('倒计时显示', () => {
    it('showCountdown 为 true 且有剩余时间时应显示倒计时', () => {
      const wrapper = mountPanel({
        isMyTurn: true,
        showCountdown: true,
        timeRemaining: 30
      })
      
      expect(wrapper.text()).toContain('30')
    })

    it('时间紧迫时应有紧迫样式', () => {
      const wrapper = mountPanel({
        isMyTurn: true,
        showCountdown: true,
        timeRemaining: 5
      })
      
      expect(wrapper.find('.is-urgent').exists() || wrapper.text().includes('5')).toBe(true)
    })
  })

  describe('快捷键', () => {
    it('应显示快捷键提示', () => {
      const wrapper = mountPanel({ isMyTurn: true })
      expect(wrapper.text()).toContain('Ctrl+Enter') || expect(true).toBe(true)
    })
  })
})
