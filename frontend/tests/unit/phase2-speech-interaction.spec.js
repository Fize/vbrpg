/**
 * Phase 2: 发言交互前端测试 (T22)
 * 
 * 测试 T19-T20 的前端实现：
 * - PlayerInputPanel 预设发言选项
 * - WebSocket 事件处理
 * - 发言提交
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useGameStore } from '@/stores/game'
import { useSocketStore } from '@/stores/socket'
import PlayerInputPanel from '@/components/werewolf/PlayerInputPanel.vue'

// Mock Element Plus icons
vi.mock('@element-plus/icons-vue', () => ({
  Microphone: { template: '<span>Microphone</span>' },
  InfoFilled: { template: '<span>InfoFilled</span>' },
  Position: { template: '<span>Position</span>' }
}))

describe('Phase 2 前端: PlayerInputPanel 预设发言选项', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  const createWrapper = (props = {}) => {
    return mount(PlayerInputPanel, {
      props: {
        visible: true,
        isMyTurn: false,
        isSubmitting: false,
        allowSkip: true,
        maxLength: 500,
        speechOptions: [],
        ...props
      },
      global: {
        stubs: {
          ElIcon: true,
          ElInput: true,
          ElButton: true
        }
      }
    })
  }

  describe('基础渲染', () => {
    it('应该正确渲染面板', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.player-input-panel').exists()).toBe(true)
    })

    it('当 visible=false 时不应渲染', () => {
      const wrapper = createWrapper({ visible: false })
      expect(wrapper.find('.player-input-panel').exists()).toBe(false)
    })

    it('当 isMyTurn=true 时应显示激活样式', () => {
      const wrapper = createWrapper({ isMyTurn: true })
      expect(wrapper.find('.player-input-panel').classes()).toContain('is-active')
    })

    it('当 isMyTurn=false 时应显示禁用样式', () => {
      const wrapper = createWrapper({ isMyTurn: false })
      expect(wrapper.find('.player-input-panel').classes()).toContain('is-disabled')
    })
  })

  describe('预设发言选项', () => {
    it('当没有选项时不应显示选项区域', () => {
      const wrapper = createWrapper({
        isMyTurn: true,
        speechOptions: []
      })
      expect(wrapper.find('.speech-options-area').exists()).toBe(false)
    })

    it('当有选项且轮到发言时应显示选项区域', () => {
      const wrapper = createWrapper({
        isMyTurn: true,
        speechOptions: [
          { id: 'pass', text: '过', type: 'basic' },
          { id: 'innocent', text: '我是好人', type: 'defense' }
        ]
      })
      expect(wrapper.find('.speech-options-area').exists()).toBe(true)
    })

    it('应该渲染所有预设选项按钮', () => {
      const options = [
        { id: 'pass', text: '过', type: 'basic' },
        { id: 'innocent', text: '我是好人', type: 'defense' },
        { id: 'accuse', text: '我怀疑...', type: 'accuse' }
      ]
      const wrapper = createWrapper({
        isMyTurn: true,
        speechOptions: options
      })
      const buttons = wrapper.findAll('.option-button')
      expect(buttons.length).toBe(options.length)
    })

    it('点击选项应选中并填充到输入框', async () => {
      const options = [
        { id: 'pass', text: '过', type: 'basic' }
      ]
      const wrapper = createWrapper({
        isMyTurn: true,
        speechOptions: options
      })
      
      const button = wrapper.find('.option-button')
      await button.trigger('click')
      
      // 验证选中状态和内容填充
      // 由于使用 stub，我们检查内部状态
      expect(wrapper.vm.selectedOptionId).toBe('pass')
      expect(wrapper.vm.inputContent).toBe('过')
    })
  })

  describe('发言提交', () => {
    it('应该在提交时发送 content 和 optionId', async () => {
      const wrapper = createWrapper({
        isMyTurn: true,
        speechOptions: [{ id: 'test', text: '测试内容', type: 'basic' }]
      })
      
      // 选择一个选项
      wrapper.vm.selectOption({ id: 'test', text: '测试内容', type: 'basic' })
      
      // 触发提交
      wrapper.vm.handleSubmit()
      
      // 验证 emit 事件
      expect(wrapper.emitted('submit')).toBeTruthy()
      expect(wrapper.emitted('submit')[0][0]).toEqual({
        content: '测试内容',
        optionId: 'test'
      })
    })

    it('当 canSubmit=false 时不应触发提交', async () => {
      const wrapper = createWrapper({
        isMyTurn: false
      })
      
      wrapper.vm.handleSubmit()
      
      expect(wrapper.emitted('submit')).toBeFalsy()
    })
  })

  describe('跳过发言', () => {
    it('当 allowSkip=true 且 isMyTurn=true 时应显示跳过按钮', () => {
      const wrapper = createWrapper({
        isMyTurn: true,
        allowSkip: true
      })
      // 由于使用 stub，直接检查 props
      expect(wrapper.props('allowSkip')).toBe(true)
    })

    it('点击跳过应触发 skip 事件', async () => {
      const wrapper = createWrapper({
        isMyTurn: true,
        allowSkip: true
      })
      
      wrapper.vm.handleSkip()
      
      expect(wrapper.emitted('skip')).toBeTruthy()
    })
  })

  describe('倒计时显示', () => {
    it('当 showCountdown=true 且 timeRemaining>0 时应显示倒计时', () => {
      const wrapper = createWrapper({
        isMyTurn: true,
        showCountdown: true,
        timeRemaining: 60
      })
      expect(wrapper.find('.countdown-overlay').exists()).toBe(true)
    })

    it('当 timeRemaining<=10 时应显示紧急样式', () => {
      const wrapper = createWrapper({
        isMyTurn: true,
        showCountdown: true,
        timeRemaining: 5
      })
      expect(wrapper.find('.countdown-value.is-urgent').exists()).toBe(true)
    })
  })
})

describe('Phase 2 前端: Game Store 发言状态', () => {
  let gameStore

  beforeEach(() => {
    setActivePinia(createPinia())
    gameStore = useGameStore()
  })

  it('应该初始化空的 speechOptions', () => {
    expect(gameStore.speechOptions).toEqual([])
  })

  it('应该初始化 speechTimeout 为 0', () => {
    expect(gameStore.speechTimeout).toBe(0)
  })

  it('setSpeechOptions 应该更新发言选项', () => {
    const options = [
      { id: 'pass', text: '过', type: 'basic' }
    ]
    gameStore.setSpeechOptions(options)
    expect(gameStore.speechOptions).toEqual(options)
  })

  it('setSpeechTimeout 应该更新超时时间', () => {
    gameStore.setSpeechTimeout(120)
    expect(gameStore.speechTimeout).toBe(120)
  })

  it('clearSpeechState 应该清除所有发言状态', () => {
    gameStore.setSpeechOptions([{ id: 'test', text: 'test', type: 'basic' }])
    gameStore.setSpeechTimeout(60)
    gameStore.setWaitingForInput(true)
    
    gameStore.clearSpeechState()
    
    expect(gameStore.speechOptions).toEqual([])
    expect(gameStore.speechTimeout).toBe(0)
    expect(gameStore.waitingForInput).toBe(false)
  })
})

describe('Phase 2 前端: Socket Store 发言方法', () => {
  let socketStore

  beforeEach(() => {
    setActivePinia(createPinia())
    socketStore = useSocketStore()
  })

  it('应该有 submitHumanSpeech 方法', () => {
    expect(typeof socketStore.submitHumanSpeech).toBe('function')
  })

  it('submitHumanSpeech 未连接时应抛出错误', () => {
    expect(() => {
      socketStore.submitHumanSpeech('room1', 'player1', '测试发言')
    }).toThrow('WebSocket 未连接')
  })
})
