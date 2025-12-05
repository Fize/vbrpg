/**
 * Phase 5: 遗言与观战模式测试
 * 
 * 测试覆盖:
 * - T52: game.js 遗言状态管理
 * - T51: LastWordsPanel.vue 组件
 * - T53: 观战模式
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { useGameStore } from '@/stores/game'
import { useSocketStore } from '@/stores/socket'
import LastWordsPanel from '@/components/werewolf/LastWordsPanel.vue'

describe('Phase 5: 遗言与观战模式', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  // ============================================================
  // T52: game store 遗言状态管理
  // ============================================================
  
  describe('T52: game store 遗言状态管理', () => {
    it('应该有 isLastWordsPhase 状态', () => {
      const store = useGameStore()
      expect(store.isLastWordsPhase).toBeDefined()
      expect(store.isLastWordsPhase).toBe(false)
    })

    it('应该有 lastWordsSeat 状态', () => {
      const store = useGameStore()
      expect(store.lastWordsSeat).toBeDefined()
      expect(store.lastWordsSeat).toBe(null)
    })

    it('应该有 lastWordsOptions 状态', () => {
      const store = useGameStore()
      expect(store.lastWordsOptions).toBeDefined()
      expect(store.lastWordsOptions).toEqual([])
    })

    it('应该有 lastWordsDeathReason 状态', () => {
      const store = useGameStore()
      expect(store.lastWordsDeathReason).toBeDefined()
      expect(store.lastWordsDeathReason).toBe(null)
    })

    it('应该有 lastWordsTimeout 状态', () => {
      const store = useGameStore()
      expect(store.lastWordsTimeout).toBeDefined()
      expect(store.lastWordsTimeout).toBe(0)
    })

    it('应该有 isSpectatorMode 状态', () => {
      const store = useGameStore()
      expect(store.isSpectatorMode).toBeDefined()
      expect(store.isSpectatorMode).toBe(false)
    })
  })

  describe('T52: game store 遗言方法', () => {
    it('setLastWordsPhase 应该设置遗言阶段状态', () => {
      const store = useGameStore()
      
      store.setLastWordsPhase(true, {
        seat_number: 3,
        options: [{ id: '1', text: '选项1' }],
        death_reason: 'vote',
        timeout_seconds: 60
      })
      
      expect(store.isLastWordsPhase).toBe(true)
      expect(store.lastWordsSeat).toBe(3)
      expect(store.lastWordsOptions.length).toBe(1)
      expect(store.lastWordsDeathReason).toBe('vote')
      expect(store.lastWordsTimeout).toBe(60)
    })

    it('setLastWordsPhase(false) 应该清除所有遗言状态', () => {
      const store = useGameStore()
      
      // 先设置状态
      store.setLastWordsPhase(true, {
        seat_number: 3,
        options: [{ id: '1' }],
        death_reason: 'vote',
        timeout_seconds: 60
      })
      
      // 清除状态
      store.setLastWordsPhase(false)
      
      expect(store.isLastWordsPhase).toBe(false)
      expect(store.lastWordsSeat).toBe(null)
      expect(store.lastWordsOptions).toEqual([])
      expect(store.lastWordsDeathReason).toBe(null)
      expect(store.lastWordsTimeout).toBe(0)
    })

    it('setSpectatorMode 应该设置观战模式', () => {
      const store = useGameStore()
      store.isAlive = true
      
      store.setSpectatorMode(true)
      
      expect(store.isSpectatorMode).toBe(true)
      expect(store.isAlive).toBe(false)  // 观战模式下玩家不存活
    })

    it('clearLastWordsState 应该清除遗言状态', () => {
      const store = useGameStore()
      
      store.setLastWordsPhase(true, {
        seat_number: 3,
        options: [{ id: '1' }],
        death_reason: 'vote',
        timeout_seconds: 60
      })
      
      store.clearLastWordsState()
      
      expect(store.isLastWordsPhase).toBe(false)
      expect(store.lastWordsSeat).toBe(null)
    })
  })

  // ============================================================
  // T50: socket store submitLastWords 方法
  // ============================================================
  
  describe('T50: socket store submitLastWords 方法', () => {
    it('应该存在 submitLastWords 方法', () => {
      const store = useSocketStore()
      expect(store.submitLastWords).toBeDefined()
      expect(typeof store.submitLastWords).toBe('function')
    })

    it('submitLastWords 未连接时应抛出错误', () => {
      const store = useSocketStore()
      
      expect(() => {
        store.submitLastWords('test-room', 'game-id', '遗言内容')
      }).toThrow('WebSocket 未连接')
    })

    it('submitLastWords 连接时应发送正确事件', () => {
      const store = useSocketStore()
      const mockEmit = vi.fn()
      store.socket = {
        connected: true,
        emit: mockEmit
      }
      
      store.submitLastWords('test-room', 'game-id', '我是好人')
      
      expect(mockEmit).toHaveBeenCalledWith('werewolf_human_last_words', {
        room_code: 'test-room',
        game_id: 'game-id',
        content: '我是好人'
      })
    })

    it('submitLastWords 跳过遗言应发送空内容', () => {
      const store = useSocketStore()
      const mockEmit = vi.fn()
      store.socket = {
        connected: true,
        emit: mockEmit
      }
      
      store.submitLastWords('test-room', 'game-id', '')
      
      expect(mockEmit).toHaveBeenCalledWith('werewolf_human_last_words', {
        room_code: 'test-room',
        game_id: 'game-id',
        content: ''
      })
    })
  })

  // ============================================================
  // T51: LastWordsPanel.vue 组件渲染
  // ============================================================
  
  describe('T51: LastWordsPanel.vue 组件渲染', () => {
    function setupStoreForLastWords() {
      const gameStore = useGameStore()
      gameStore.mySeatNumber = 3
      gameStore.setLastWordsPhase(true, {
        seat_number: 3,
        options: [
          { id: 'no_words', text: '我没什么想说的，走了。', type: 'skip' },
          { id: 'innocent', text: '我是好人！', type: 'plea' }
        ],
        death_reason: 'vote',
        timeout_seconds: 60
      })
      
      // Mock playerStates for target selection
      gameStore.playerStates = {
        1: { seat_number: 1, player_name: '玩家1', is_alive: true },
        2: { seat_number: 2, player_name: '玩家2', is_alive: true },
        3: { seat_number: 3, player_name: '玩家3', is_alive: false },
        4: { seat_number: 4, player_name: '玩家4', is_alive: true }
      }
      
      return gameStore
    }

    it('遗言阶段且是自己回合时应显示面板', () => {
      setupStoreForLastWords()
      
      const wrapper = mount(LastWordsPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      expect(wrapper.find('.last-words-panel').exists()).toBe(true)
    })

    it('不是自己的遗言回合不应显示面板', () => {
      const gameStore = useGameStore()
      gameStore.mySeatNumber = 1  // 我是1号
      gameStore.setLastWordsPhase(true, {
        seat_number: 3,  // 但3号在遗言
        options: [],
        death_reason: 'vote',
        timeout_seconds: 60
      })
      
      const wrapper = mount(LastWordsPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      expect(wrapper.find('.last-words-panel').exists()).toBe(false)
    })

    it('应该显示面板标题', () => {
      setupStoreForLastWords()
      
      const wrapper = mount(LastWordsPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      expect(wrapper.find('.header-title').text()).toContain('遗言')
    })

    it('应该显示死亡原因', () => {
      setupStoreForLastWords()
      
      const wrapper = mount(LastWordsPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      expect(wrapper.find('.death-reason').text()).toContain('放逐出局')
    })
  })

  describe('T51: LastWordsPanel.vue 预设选项', () => {
    function setupStoreForLastWords() {
      const gameStore = useGameStore()
      gameStore.mySeatNumber = 3
      gameStore.setLastWordsPhase(true, {
        seat_number: 3,
        options: [
          { id: 'no_words', text: '我没什么想说的，走了。', type: 'skip' },
          { id: 'innocent', text: '我是好人！', type: 'plea' },
          { id: 'accusation', text: '我怀疑X号是狼人', type: 'accusation', needs_target: true }
        ],
        death_reason: 'vote',
        timeout_seconds: 60
      })
      gameStore.playerStates = {
        1: { seat_number: 1, player_name: '玩家1', is_alive: true },
        2: { seat_number: 2, player_name: '玩家2', is_alive: true },
        3: { seat_number: 3, player_name: '玩家3', is_alive: false }
      }
      return gameStore
    }

    it('应该渲染所有预设选项', () => {
      setupStoreForLastWords()
      
      const wrapper = mount(LastWordsPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      const options = wrapper.findAll('.option-button')
      expect(options.length).toBe(3)
    })

    it('点击选项应该选中', async () => {
      setupStoreForLastWords()
      
      const wrapper = mount(LastWordsPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      const option = wrapper.findAll('.option-button')[1]
      await option.trigger('click')
      
      expect(option.classes()).toContain('selected')
    })

    it('跳过选项应有特殊样式', () => {
      setupStoreForLastWords()
      
      const wrapper = mount(LastWordsPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      const skipOption = wrapper.find('.skip-option')
      expect(skipOption.exists()).toBe(true)
    })
  })

  describe('T51: LastWordsPanel.vue 自由输入', () => {
    function setupStoreForLastWords() {
      const gameStore = useGameStore()
      gameStore.mySeatNumber = 3
      gameStore.setLastWordsPhase(true, {
        seat_number: 3,
        options: [],
        death_reason: 'vote',
        timeout_seconds: 60
      })
      return gameStore
    }

    it('应该有自由输入文本框', () => {
      setupStoreForLastWords()
      
      const wrapper = mount(LastWordsPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      expect(wrapper.find('.custom-textarea').exists()).toBe(true)
    })

    it('输入内容后提交按钮应启用', async () => {
      setupStoreForLastWords()
      
      const wrapper = mount(LastWordsPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      const textarea = wrapper.find('.custom-textarea')
      await textarea.setValue('我的遗言')
      
      const submitBtn = wrapper.find('.submit-button')
      expect(submitBtn.attributes('disabled')).toBeUndefined()
    })
  })

  describe('T51: LastWordsPanel.vue 倒计时', () => {
    function setupStoreForLastWords() {
      const gameStore = useGameStore()
      gameStore.mySeatNumber = 3
      gameStore.setLastWordsPhase(true, {
        seat_number: 3,
        options: [],
        death_reason: 'vote',
        timeout_seconds: 60
      })
      return gameStore
    }

    it('应该显示倒计时', async () => {
      setupStoreForLastWords()
      
      const wrapper = mount(LastWordsPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      // 等待组件更新
      await wrapper.vm.$nextTick()
      
      // 倒计时需要 remainingTime > 0 才显示，由 startCountdown 设置
      // 组件在 mounted 时会调用 startCountdown 设置 remainingTime
      expect(wrapper.find('.countdown-section').exists()).toBe(true)
      expect(wrapper.find('.countdown-text').text()).toContain('60')
    })

    it('应该显示倒计时进度条', async () => {
      setupStoreForLastWords()
      
      const wrapper = mount(LastWordsPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      // 等待组件更新
      await wrapper.vm.$nextTick()
      
      expect(wrapper.find('.countdown-bar').exists()).toBe(true)
      expect(wrapper.find('.countdown-progress').exists()).toBe(true)
    })
  })

  describe('T51: LastWordsPanel.vue 操作按钮', () => {
    function setupStoreForLastWords() {
      const gameStore = useGameStore()
      gameStore.mySeatNumber = 3
      gameStore.setLastWordsPhase(true, {
        seat_number: 3,
        options: [
          { id: 'innocent', text: '我是好人！', type: 'plea' }
        ],
        death_reason: 'vote',
        timeout_seconds: 60
      })
      return gameStore
    }

    it('应该有跳过按钮', () => {
      setupStoreForLastWords()
      
      const wrapper = mount(LastWordsPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      expect(wrapper.find('.skip-button').exists()).toBe(true)
      expect(wrapper.find('.skip-button').text()).toContain('跳过')
    })

    it('应该有提交按钮', () => {
      setupStoreForLastWords()
      
      const wrapper = mount(LastWordsPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      expect(wrapper.find('.submit-button').exists()).toBe(true)
      expect(wrapper.find('.submit-button').text()).toContain('发表')
    })

    it('未选择内容时提交按钮应禁用', () => {
      setupStoreForLastWords()
      
      const wrapper = mount(LastWordsPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      const submitBtn = wrapper.find('.submit-button')
      expect(submitBtn.attributes('disabled')).toBeDefined()
    })

    it('点击跳过按钮应触发事件', async () => {
      setupStoreForLastWords()
      const socketStore = useSocketStore()
      socketStore.socket = {
        connected: true,
        emit: vi.fn()
      }
      
      const wrapper = mount(LastWordsPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      await wrapper.find('.skip-button').trigger('click')
      
      expect(wrapper.emitted('last-words-skipped')).toBeTruthy()
    })

    it('选择选项后点击提交应调用 submitLastWords', async () => {
      setupStoreForLastWords()
      const socketStore = useSocketStore()
      const mockEmit = vi.fn()
      socketStore.socket = {
        connected: true,
        emit: mockEmit
      }
      
      const wrapper = mount(LastWordsPanel, {
        global: { plugins: [pinia] },
        props: { roomCode: 'test-room' }
      })
      
      // 选择选项
      await wrapper.find('.option-button').trigger('click')
      // 点击提交
      await wrapper.find('.submit-button').trigger('click')
      
      expect(mockEmit).toHaveBeenCalledWith('werewolf_human_last_words', expect.objectContaining({
        room_code: 'test-room',
        content: '我是好人！'
      }))
    })
  })

  // ============================================================
  // T53: 观战模式
  // ============================================================
  
  describe('T53: 观战模式状态', () => {
    it('setSpectatorMode(true) 应该启用观战模式', () => {
      const store = useGameStore()
      store.isAlive = true
      
      store.setSpectatorMode(true)
      
      expect(store.isSpectatorMode).toBe(true)
    })

    it('观战模式下 isAlive 应该为 false', () => {
      const store = useGameStore()
      store.isAlive = true
      
      store.setSpectatorMode(true)
      
      expect(store.isAlive).toBe(false)
    })

    it('setSpectatorMode(false) 应该禁用观战模式', () => {
      const store = useGameStore()
      store.setSpectatorMode(true)
      
      store.setSpectatorMode(false)
      
      expect(store.isSpectatorMode).toBe(false)
    })
  })
})
