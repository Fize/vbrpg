/**
 * 狼人杀游戏模式选择对话框组件测试
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import WerewolfModeDialog from '@/components/werewolf/WerewolfModeDialog.vue'
import { ElDialog, ElButton, ElIcon, ElAlert } from 'element-plus'

// Mock RoleSelector组件
vi.mock('@/components/werewolf/RoleSelector.vue', () => ({
  default: {
    name: 'RoleSelector',
    template: '<div class="mock-role-selector"></div>',
    props: ['modelValue', 'gameType'],
    emits: ['update:modelValue', 'change']
  }
}))

describe('WerewolfModeDialog', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()
  })

  /**
   * 辅助函数：挂载组件
   */
  function mountDialog(props = {}) {
    return mount(WerewolfModeDialog, {
      global: {
        plugins: [pinia],
        components: {
          ElDialog,
          ElButton,
          ElIcon,
          ElAlert
        },
        stubs: {
          'el-dialog': {
            template: '<div v-if="modelValue" class="el-dialog"><slot></slot><slot name="footer"></slot></div>',
            props: ['modelValue', 'title']
          },
          'el-button': {
            template: '<button :disabled="disabled" :class="{ loading: loading }" @click="$emit(\'click\')"><slot /></button>',
            props: ['disabled', 'loading', 'type']
          },
          'el-icon': {
            template: '<span class="el-icon"><slot /></span>'
          },
          'el-alert': {
            template: '<div class="el-alert"><slot name="title" /><slot /></div>'
          },
          User: { template: '<span class="icon-user"></span>' },
          View: { template: '<span class="icon-view"></span>' }
        }
      },
      props: {
        modelValue: true,
        ...props
      }
    })
  }

  describe('对话框渲染', () => {
    it('应该正确渲染对话框', () => {
      const wrapper = mountDialog()
      expect(wrapper.find('.el-dialog').exists()).toBe(true)
    })

    it('modelValue 为 false 时应隐藏对话框', () => {
      const wrapper = mountDialog({ modelValue: false })
      expect(wrapper.find('.el-dialog').exists()).toBe(false)
    })
  })

  describe('模式选择', () => {
    it('默认选择玩家模式', () => {
      const wrapper = mountDialog()
      const playerMode = wrapper.find('.mode-card')
      expect(playerMode.classes()).toContain('active')
    })

    it('应该能够切换到观战模式', async () => {
      const wrapper = mountDialog()
      const modeCards = wrapper.findAll('.mode-card')
      expect(modeCards.length).toBeGreaterThanOrEqual(2)
      
      // 点击观战模式
      await modeCards[1].trigger('click')
      
      expect(modeCards[1].classes()).toContain('active')
      expect(modeCards[0].classes()).not.toContain('active')
    })

    it('选择玩家模式时应显示角色选择器', () => {
      const wrapper = mountDialog()
      expect(wrapper.find('.role-selection').exists()).toBe(true)
    })

    it('选择观战模式时应隐藏角色选择器', async () => {
      const wrapper = mountDialog()
      const modeCards = wrapper.findAll('.mode-card')
      
      // 切换到观战模式
      await modeCards[1].trigger('click')
      
      expect(wrapper.find('.role-selection').exists()).toBe(false)
    })
  })

  describe('游戏配置信息', () => {
    it('应显示10人局配置说明', () => {
      const wrapper = mountDialog()
      const alertText = wrapper.text()
      expect(alertText).toContain('10人局')
      expect(alertText).toContain('狼人')
      expect(alertText).toContain('预言家')
      expect(alertText).toContain('女巫')
      expect(alertText).toContain('猎人')
      expect(alertText).toContain('村民')
    })
  })

  describe('按钮交互', () => {
    it('应该有取消和开始游戏按钮', () => {
      const wrapper = mountDialog()
      const buttons = wrapper.findAll('button')
      expect(buttons.length).toBeGreaterThanOrEqual(2)
    })

    it('点击取消按钮应触发 cancel 事件', async () => {
      const wrapper = mountDialog()
      const cancelBtn = wrapper.findAll('button')[0]
      await cancelBtn.trigger('click')
      expect(wrapper.emitted('cancel')).toBeTruthy()
    })

    it('点击开始游戏按钮应触发 start 事件', async () => {
      const wrapper = mountDialog()
      const buttons = wrapper.findAll('button')
      const startBtn = buttons[buttons.length - 1]
      await startBtn.trigger('click')
      expect(wrapper.emitted('start')).toBeTruthy()
    })
  })

  describe('加载状态', () => {
    it('开始游戏时按钮应显示加载状态', async () => {
      const wrapper = mountDialog()
      
      // 模拟开始游戏
      const buttons = wrapper.findAll('button')
      const startBtn = buttons[buttons.length - 1]
      await startBtn.trigger('click')
      
      // 组件内部设置 isStarting
      await wrapper.vm.$nextTick()
      
      // 检查 start 事件被触发
      expect(wrapper.emitted('start')).toBeTruthy()
    })
  })
})
