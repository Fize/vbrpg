/**
 * Phase 4.1: 狼人私密讨论测试
 * 
 * 任务覆盖:
 * - T43: WolfChatPanel.vue 组件
 * - T44: game store 狼人讨论状态管理
 * - T44: socket store sendWolfChatMessage 方法
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'

import { useGameStore } from '@/stores/game'
import { useSocketStore } from '@/stores/socket'
import WolfChatPanel from '@/components/werewolf/WolfChatPanel.vue'


describe('Phase 4.1: 狼人私密讨论', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('T44: game store 狼人讨论状态管理', () => {
    it('应该有 isWerewolf 状态', () => {
      const store = useGameStore()
      expect(store.isWerewolf).toBeDefined()
      expect(store.isWerewolf).toBe(false)
    })

    it('应该有 wolfChatMessages 状态', () => {
      const store = useGameStore()
      expect(store.wolfChatMessages).toBeDefined()
      expect(Array.isArray(store.wolfChatMessages)).toBe(true)
      expect(store.wolfChatMessages.length).toBe(0)
    })

    it('应该有 isWolfChatEnabled 状态', () => {
      const store = useGameStore()
      expect(store.isWolfChatEnabled).toBeDefined()
      expect(store.isWolfChatEnabled).toBe(false)
    })
  })

  describe('T44: game store 狼人讨论方法', () => {
    it('setIsWerewolf 应该设置狼人状态', () => {
      const store = useGameStore()
      store.setIsWerewolf(true)
      expect(store.isWerewolf).toBe(true)
      
      store.setIsWerewolf(false)
      expect(store.isWerewolf).toBe(false)
    })

    it('addWolfChatMessage 应该添加狼人讨论消息', () => {
      const store = useGameStore()
      const message = {
        id: '1',
        seat_number: 2,
        sender_name: '玩家A',
        content: '杀3号',
        timestamp: Date.now()
      }
      
      store.addWolfChatMessage(message)
      expect(store.wolfChatMessages.length).toBe(1)
      expect(store.wolfChatMessages[0].content).toBe('杀3号')
    })

    it('addWolfChatMessage 应该正确设置时间', () => {
      const store = useGameStore()
      const message = {
        seat_number: 2,
        sender_name: '玩家A',
        content: '杀3号'
      }
      
      store.addWolfChatMessage(message)
      expect(store.wolfChatMessages[0].time).toBeDefined()
      expect(store.wolfChatMessages[0].id).toBeDefined()
    })

    it('setWolfChatHistory 应该设置完整消息列表', () => {
      const store = useGameStore()
      const messages = [
        { id: '1', seat_number: 1, sender_name: '玩家A', content: '消息1' },
        { id: '2', seat_number: 2, sender_name: '玩家B', content: '消息2' }
      ]
      
      store.setWolfChatHistory(messages)
      expect(store.wolfChatMessages.length).toBe(2)
      expect(store.wolfChatMessages[0].content).toBe('消息1')
      expect(store.wolfChatMessages[1].content).toBe('消息2')
    })

    it('setWolfChatHistory 传入空值应该清空消息', () => {
      const store = useGameStore()
      store.addWolfChatMessage({ id: '1', content: 'test' })
      
      store.setWolfChatHistory(null)
      expect(store.wolfChatMessages.length).toBe(0)
    })

    it('clearWolfChatMessages 应该清空消息列表', () => {
      const store = useGameStore()
      store.addWolfChatMessage({ id: '1', content: 'test1' })
      store.addWolfChatMessage({ id: '2', content: 'test2' })
      
      store.clearWolfChatMessages()
      expect(store.wolfChatMessages.length).toBe(0)
    })

    it('setWolfChatEnabled 应该设置聊天启用状态', () => {
      const store = useGameStore()
      expect(store.setWolfChatEnabled).toBeDefined()
      
      store.setWolfChatEnabled(true)
      expect(store.isWolfChatEnabled).toBe(true)
      
      store.setWolfChatEnabled(false)
      expect(store.isWolfChatEnabled).toBe(false)
    })
  })

  describe('T44: socket store sendWolfChatMessage 方法', () => {
    it('应该存在 sendWolfChatMessage 方法', () => {
      const store = useSocketStore()
      expect(store.sendWolfChatMessage).toBeDefined()
      expect(typeof store.sendWolfChatMessage).toBe('function')
    })

    it('sendWolfChatMessage 未连接时应抛出错误', () => {
      const store = useSocketStore()
      expect(() => {
        store.sendWolfChatMessage('room123', '杀3号')
      }).toThrow('WebSocket 未连接')
    })

    it('sendWolfChatMessage 连接时应发送正确事件', () => {
      const store = useSocketStore()
      
      // 模拟连接
      const mockEmit = vi.fn()
      store.socket = {
        connected: true,
        emit: mockEmit
      }
      
      store.sendWolfChatMessage('room123', '杀3号')
      
      expect(mockEmit).toHaveBeenCalledWith('werewolf_wolf_chat', {
        room_code: 'room123',
        content: '杀3号'
      })
    })

    it('sendWolfChatMessage 应处理空内容', () => {
      const store = useSocketStore()
      
      const mockEmit = vi.fn()
      store.socket = {
        connected: true,
        emit: mockEmit
      }
      
      // 空内容也应该发送（由后端验证）
      store.sendWolfChatMessage('room123', '')
      
      expect(mockEmit).toHaveBeenCalledWith('werewolf_wolf_chat', {
        room_code: 'room123',
        content: ''
      })
    })
  })

  describe('T43: WolfChatPanel.vue 组件渲染', () => {
    function createWrapper(overrides = {}) {
      const gameStore = useGameStore()
      
      // 设置默认狼人状态使面板可见
      gameStore.setIsWerewolf(true)
      gameStore.currentPhase = 'night_werewolf'
      
      return mount(WolfChatPanel, {
        global: {
          plugins: [pinia]
        },
        props: {
          roomCode: 'test-room',
          showTargetSelection: false,
          killTargets: [],
          ...overrides
        }
      })
    }

    it('狼人在狼人阶段应该显示面板', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.wolf-chat-panel').exists()).toBe(true)
    })

    it('非狼人不应显示面板', () => {
      const gameStore = useGameStore()
      gameStore.setIsWerewolf(false)
      
      const wrapper = mount(WolfChatPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      expect(wrapper.find('.wolf-chat-panel').exists()).toBe(false)
    })

    it('应该显示面板标题', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.header-title').text()).toBe('狼人私密讨论')
    })

    it('应该显示狼人图标', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.header-icon').text()).toBe('🐺')
    })
  })

  describe('T43: WolfChatPanel.vue 狼队友显示', () => {
    function createWrapper(teammates = []) {
      const gameStore = useGameStore()
      gameStore.setIsWerewolf(true)
      gameStore.currentPhase = 'night_werewolf'
      gameStore.werewolfTeammates = teammates
      
      return mount(WolfChatPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
    }

    it('有狼队友时应显示队友标签', () => {
      const wrapper = createWrapper([
        { seat_number: 3, player_name: '玩家C' },
        { seat_number: 5, player_name: '玩家E' }
      ])
      
      const tags = wrapper.findAll('.teammate-tag')
      expect(tags.length).toBe(2)
      expect(tags[0].text()).toContain('3号')
      expect(tags[0].text()).toContain('玩家C')
    })

    it('没有狼队友时应显示唯一狼人提示', () => {
      const wrapper = createWrapper([])
      expect(wrapper.find('.no-teammate').text()).toBe('你是唯一的狼人')
    })
  })

  describe('T43: WolfChatPanel.vue 消息显示', () => {
    function createWrapper(messages = []) {
      const gameStore = useGameStore()
      gameStore.setIsWerewolf(true)
      gameStore.currentPhase = 'night_werewolf'
      gameStore.setWolfChatHistory(messages)
      gameStore.mySeatNumber = 2
      
      return mount(WolfChatPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
    }

    it('没有消息时应显示空状态提示', () => {
      const wrapper = createWrapper([])
      expect(wrapper.find('.no-messages').exists()).toBe(true)
      expect(wrapper.find('.no-messages').text()).toContain('暂无讨论消息')
    })

    it('有消息时应显示消息列表', () => {
      const wrapper = createWrapper([
        { id: '1', seat_number: 2, sender_name: '玩家A', content: '杀3号' },
        { id: '2', seat_number: 3, sender_name: '玩家B', content: '同意' }
      ])
      
      const messages = wrapper.findAll('.message')
      expect(messages.length).toBe(2)
    })

    it('消息应显示发送者和内容', () => {
      const wrapper = createWrapper([
        { id: '1', seat_number: 2, sender_name: '玩家A', content: '杀3号' }
      ])
      
      const message = wrapper.find('.message')
      expect(message.find('.sender').text()).toContain('2号')
      expect(message.find('.content').text()).toBe('杀3号')
    })

    it('自己的消息应有特殊样式', () => {
      const gameStore = useGameStore()
      gameStore.setIsWerewolf(true)
      gameStore.currentPhase = 'night_werewolf'
      gameStore.mySeatNumber = 2
      gameStore.setWolfChatHistory([
        { id: '1', seat_number: 2, sender_name: '我', content: '我的消息' }
      ])
      
      const wrapper = mount(WolfChatPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      const message = wrapper.find('.message')
      expect(message.classes()).toContain('my-message')
    })
  })

  describe('T43: WolfChatPanel.vue 消息输入', () => {
    function createWrapper() {
      const gameStore = useGameStore()
      gameStore.setIsWerewolf(true)
      gameStore.currentPhase = 'night_werewolf'
      gameStore.setWolfChatEnabled(true)
      
      return mount(WolfChatPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
    }

    it('聊天启用时应显示输入区域', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.chat-input').exists()).toBe(true)
    })

    it('聊天禁用时不应显示输入区域', () => {
      const gameStore = useGameStore()
      gameStore.setIsWerewolf(true)
      gameStore.currentPhase = 'night_werewolf'
      gameStore.setWolfChatEnabled(false)
      
      const wrapper = mount(WolfChatPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      expect(wrapper.find('.chat-input').exists()).toBe(false)
    })

    it('应该有消息输入框', () => {
      const wrapper = createWrapper()
      const input = wrapper.find('.message-input')
      expect(input.exists()).toBe(true)
      expect(input.attributes('placeholder')).toContain('与狼队友讨论')
    })

    it('应该有发送按钮', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.send-button').exists()).toBe(true)
      expect(wrapper.find('.send-button').text()).toBe('发送')
    })

    it('输入为空时发送按钮应禁用', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.send-button').attributes('disabled')).toBeDefined()
    })

    it('输入内容后发送按钮应启用', async () => {
      const wrapper = createWrapper()
      const input = wrapper.find('.message-input')
      
      await input.setValue('测试消息')
      expect(wrapper.find('.send-button').attributes('disabled')).toBeUndefined()
    })
  })

  describe('T43: WolfChatPanel.vue 目标选择', () => {
    function createWrapper(showTargetSelection = true, killTargets = []) {
      const gameStore = useGameStore()
      gameStore.setIsWerewolf(true)
      gameStore.currentPhase = 'night_werewolf'
      
      return mount(WolfChatPanel, {
        global: { plugins: [pinia] },
        props: {
          roomCode: 'test-room',
          showTargetSelection,
          killTargets
        }
      })
    }

    it('showTargetSelection 为 true 时应显示目标选择区域', () => {
      const wrapper = createWrapper(true, [{ seat_number: 1 }])
      expect(wrapper.find('.target-selection').exists()).toBe(true)
    })

    it('showTargetSelection 为 false 时不应显示目标选择区域', () => {
      const wrapper = createWrapper(false, [])
      expect(wrapper.find('.target-selection').exists()).toBe(false)
    })

    it('应该显示目标选择标签', () => {
      const wrapper = createWrapper(true, [{ seat_number: 1 }])
      expect(wrapper.find('.selection-label').text()).toContain('选择击杀目标')
    })

    it('应该渲染所有击杀目标按钮', () => {
      const targets = [
        { seat_number: 1 },
        { seat_number: 3 },
        { seat_number: 5 }
      ]
      const wrapper = createWrapper(true, targets)
      
      const buttons = wrapper.findAll('.target-button')
      expect(buttons.length).toBe(3)
    })

    it('目标按钮应显示座位号', () => {
      const wrapper = createWrapper(true, [{ seat_number: 3 }])
      const button = wrapper.find('.target-button')
      expect(button.text()).toContain('3号')
    })

    it('空刀按钮应显示特殊样式', () => {
      const wrapper = createWrapper(true, [{ seat_number: null }])
      const button = wrapper.find('.skip-button')
      expect(button.exists()).toBe(true)
      expect(button.text()).toBe('空刀')
    })

    it('点击目标应触发 select-target 事件', async () => {
      const target = { seat_number: 3 }
      const wrapper = createWrapper(true, [target])
      
      await wrapper.find('.target-button').trigger('click')
      
      expect(wrapper.emitted('select-target')).toBeTruthy()
      expect(wrapper.emitted('select-target')[0]).toEqual([target])
    })

    it('选中目标应添加 selected 样式', async () => {
      const wrapper = createWrapper(true, [{ seat_number: 3 }])
      
      await wrapper.find('.target-button').trigger('click')
      
      expect(wrapper.find('.target-button').classes()).toContain('selected')
    })

    it('未选择目标时确认按钮应禁用', () => {
      const wrapper = createWrapper(true, [{ seat_number: 1 }])
      expect(wrapper.find('.confirm-button').attributes('disabled')).toBeDefined()
    })

    it('选择目标后确认按钮应启用', async () => {
      const wrapper = createWrapper(true, [{ seat_number: 1 }])
      
      await wrapper.find('.target-button').trigger('click')
      
      expect(wrapper.find('.confirm-button').attributes('disabled')).toBeUndefined()
    })

    it('点击确认按钮应触发 confirm-kill 事件', async () => {
      const target = { seat_number: 3 }
      const wrapper = createWrapper(true, [target])
      
      await wrapper.find('.target-button').trigger('click')
      await wrapper.find('.confirm-button').trigger('click')
      
      expect(wrapper.emitted('confirm-kill')).toBeTruthy()
      expect(wrapper.emitted('confirm-kill')[0]).toEqual([target])
    })
  })

  describe('T43: WolfChatPanel.vue 消息发送', () => {
    it('点击发送按钮应调用 sendWolfChatMessage', async () => {
      const gameStore = useGameStore()
      gameStore.setIsWerewolf(true)
      gameStore.currentPhase = 'night_werewolf'
      gameStore.setWolfChatEnabled(true)
      
      const socketStore = useSocketStore()
      const mockEmit = vi.fn()
      socketStore.socket = {
        connected: true,
        emit: mockEmit
      }
      
      const wrapper = mount(WolfChatPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      await wrapper.find('.message-input').setValue('杀3号')
      await wrapper.find('.send-button').trigger('click')
      
      // 等待异步操作
      await flushPromises()
      
      expect(mockEmit).toHaveBeenCalledWith('werewolf_wolf_chat', {
        room_code: 'test-room',
        content: '杀3号'
      })
    })

    it('发送后应清空输入框', async () => {
      const gameStore = useGameStore()
      gameStore.setIsWerewolf(true)
      gameStore.currentPhase = 'night_werewolf'
      gameStore.setWolfChatEnabled(true)
      
      const socketStore = useSocketStore()
      socketStore.socket = {
        connected: true,
        emit: vi.fn()
      }
      
      const wrapper = mount(WolfChatPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      const input = wrapper.find('.message-input')
      await input.setValue('测试消息')
      await wrapper.find('.send-button').trigger('click')
      await flushPromises()
      
      expect(input.element.value).toBe('')
    })

    it('按回车键应发送消息', async () => {
      const gameStore = useGameStore()
      gameStore.setIsWerewolf(true)
      gameStore.currentPhase = 'night_werewolf'
      gameStore.setWolfChatEnabled(true)
      
      const socketStore = useSocketStore()
      const mockEmit = vi.fn()
      socketStore.socket = {
        connected: true,
        emit: mockEmit
      }
      
      const wrapper = mount(WolfChatPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      const input = wrapper.find('.message-input')
      await input.setValue('杀5号')
      await input.trigger('keyup.enter')
      await flushPromises()
      
      expect(mockEmit).toHaveBeenCalledWith('werewolf_wolf_chat', {
        room_code: 'test-room',
        content: '杀5号'
      })
    })
  })
})
