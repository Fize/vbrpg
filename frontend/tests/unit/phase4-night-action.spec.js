/**
 * Phase 4: 夜间行动人类玩家参与测试
 * 
 * 任务覆盖:
 * - T37: NightActionPanel.vue 增强
 * - T37: game store 夜间行动状态管理
 * - T37: socket store submitHumanNightAction 方法
 * - T37: WerewolfGameView 事件处理
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

import { useGameStore } from '@/stores/game'
import { useSocketStore } from '@/stores/socket'


describe('Phase 4: 夜间行动人类玩家参与', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('T37: game store 夜间行动状态管理', () => {
    it('应该有夜间行动选项状态', () => {
      const store = useGameStore()
      expect(store.nightActionOptions).toBeDefined()
      expect(Array.isArray(store.nightActionOptions)).toBe(true)
    })

    it('应该有夜间行动超时状态', () => {
      const store = useGameStore()
      expect(store.nightActionTimeout).toBeDefined()
      expect(store.nightActionTimeout).toBe(0)
    })

    it('应该有夜间行动类型状态', () => {
      const store = useGameStore()
      expect(store.nightActionType).toBeDefined()
    })

    it('应该有夜间行动结果状态', () => {
      const store = useGameStore()
      expect(store.nightActionResult).toBeDefined()
    })

    it('应该有被杀玩家信息状态（女巫用）', () => {
      const store = useGameStore()
      expect(store.killedPlayerInfo).toBeDefined()
    })

    it('应该有女巫药水状态', () => {
      const store = useGameStore()
      expect(store.witchPotions).toBeDefined()
      expect(store.witchPotions.hasAntidote).toBe(true)
      expect(store.witchPotions.hasPoison).toBe(true)
    })
  })

  describe('T37: game store 夜间行动方法', () => {
    it('setNightActionOptions 应该设置夜间行动选项', () => {
      const store = useGameStore()
      const options = [
        { seat_number: 1, display_name: '玩家1' },
        { seat_number: 2, display_name: '玩家2' }
      ]
      store.setNightActionOptions(options)
      expect(store.nightActionOptions).toEqual(options)
    })

    it('setNightActionTimeout 应该设置超时时间', () => {
      const store = useGameStore()
      store.setNightActionTimeout(60)
      expect(store.nightActionTimeout).toBe(60)
    })

    it('setNightActionType 应该设置行动类型', () => {
      const store = useGameStore()
      store.setNightActionType('werewolf_kill')
      expect(store.nightActionType).toBe('werewolf_kill')
    })

    it('setNightActionResult 应该设置行动结果', () => {
      const store = useGameStore()
      const result = { target_seat: 3, is_werewolf: true }
      store.setNightActionResult(result)
      expect(store.nightActionResult).toEqual(result)
    })

    it('setKilledPlayerInfo 应该设置被杀玩家信息', () => {
      const store = useGameStore()
      const info = { seat_number: 5, can_self_save: true }
      store.setKilledPlayerInfo(info)
      expect(store.killedPlayerInfo).toEqual(info)
    })

    it('updateWitchPotions 应该更新女巫药水状态', () => {
      const store = useGameStore()
      store.updateWitchPotions({ hasAntidote: false })
      expect(store.witchPotions.hasAntidote).toBe(false)
      expect(store.witchPotions.hasPoison).toBe(true)

      store.updateWitchPotions({ hasPoison: false })
      expect(store.witchPotions.hasPoison).toBe(false)
    })

    it('clearNightActionState 应该清除所有夜间行动状态', () => {
      const store = useGameStore()
      
      // 设置一些状态
      store.setNightActionOptions([{ seat_number: 1 }])
      store.setNightActionTimeout(60)
      store.setNightActionType('werewolf_kill')
      store.setNightActionResult({ target: 1 })
      store.setKilledPlayerInfo({ seat_number: 5 })
      
      // 清除状态
      store.clearNightActionState()
      
      expect(store.nightActionOptions).toEqual([])
      expect(store.nightActionTimeout).toBe(0)
      expect(store.nightActionType).toBeNull()
      expect(store.nightActionResult).toBeNull()
      expect(store.killedPlayerInfo).toBeNull()
    })
  })

  describe('T37: socket store submitHumanNightAction 方法', () => {
    it('应该存在 submitHumanNightAction 方法', () => {
      const store = useSocketStore()
      expect(store.submitHumanNightAction).toBeDefined()
      expect(typeof store.submitHumanNightAction).toBe('function')
    })

    it('submitHumanNightAction 未连接时应抛出错误', () => {
      const store = useSocketStore()
      expect(() => {
        store.submitHumanNightAction('room', 'game-id', 'werewolf_kill', 3)
      }).toThrow('WebSocket 未连接')
    })

    it('submitHumanNightAction 连接时应发送事件', () => {
      const store = useSocketStore()
      
      // 模拟连接
      const mockEmit = vi.fn()
      store.socket = {
        connected: true,
        emit: mockEmit
      }
      
      store.submitHumanNightAction('room123', 'game-id', 'werewolf_kill', 3)
      
      expect(mockEmit).toHaveBeenCalledWith('werewolf_human_night_action', {
        room_code: 'room123',
        game_id: 'game-id',
        action_type: 'werewolf_kill',
        target_seat: 3
      })
    })

    it('submitHumanNightAction 女巫行动应包含 witch_action', () => {
      const store = useSocketStore()
      
      const mockEmit = vi.fn()
      store.socket = {
        connected: true,
        emit: mockEmit
      }
      
      store.submitHumanNightAction('room123', 'game-id', 'witch_action', 5, 'save')
      
      expect(mockEmit).toHaveBeenCalledWith('werewolf_human_night_action', {
        room_code: 'room123',
        game_id: 'game-id',
        action_type: 'witch_action',
        target_seat: 5,
        witch_action: 'save'
      })
    })

    it('submitHumanNightAction 空刀应传 null', () => {
      const store = useSocketStore()
      
      const mockEmit = vi.fn()
      store.socket = {
        connected: true,
        emit: mockEmit
      }
      
      store.submitHumanNightAction('room123', 'game-id', 'werewolf_kill', null)
      
      expect(mockEmit).toHaveBeenCalledWith('werewolf_human_night_action', {
        room_code: 'room123',
        game_id: 'game-id',
        action_type: 'werewolf_kill',
        target_seat: null
      })
    })
  })

  describe('T37: 夜间行动类型验证', () => {
    it('应支持 werewolf_kill 类型', () => {
      const store = useGameStore()
      store.setNightActionType('werewolf_kill')
      expect(store.nightActionType).toBe('werewolf_kill')
    })

    it('应支持 seer_check 类型', () => {
      const store = useGameStore()
      store.setNightActionType('seer_check')
      expect(store.nightActionType).toBe('seer_check')
    })

    it('应支持 witch_action 类型', () => {
      const store = useGameStore()
      store.setNightActionType('witch_action')
      expect(store.nightActionType).toBe('witch_action')
    })

    it('应支持 hunter_shoot 类型', () => {
      const store = useGameStore()
      store.setNightActionType('hunter_shoot')
      expect(store.nightActionType).toBe('hunter_shoot')
    })
  })

  describe('T37: 预言家查验结果存储', () => {
    it('应能存储查验结果为狼人', () => {
      const store = useGameStore()
      store.setNightActionResult({
        target_seat: 2,
        is_werewolf: true,
        result_text: '狼人'
      })
      expect(store.nightActionResult.is_werewolf).toBe(true)
      expect(store.nightActionResult.result_text).toBe('狼人')
    })

    it('应能存储查验结果为好人', () => {
      const store = useGameStore()
      store.setNightActionResult({
        target_seat: 3,
        is_werewolf: false,
        result_text: '好人'
      })
      expect(store.nightActionResult.is_werewolf).toBe(false)
      expect(store.nightActionResult.result_text).toBe('好人')
    })
  })

  describe('T37: 女巫药水状态管理', () => {
    it('初始状态应该有解药和毒药', () => {
      const store = useGameStore()
      expect(store.witchPotions.hasAntidote).toBe(true)
      expect(store.witchPotions.hasPoison).toBe(true)
    })

    it('使用解药后应更新状态', () => {
      const store = useGameStore()
      store.updateWitchPotions({ hasAntidote: false })
      expect(store.witchPotions.hasAntidote).toBe(false)
    })

    it('使用毒药后应更新状态', () => {
      const store = useGameStore()
      store.updateWitchPotions({ hasPoison: false })
      expect(store.witchPotions.hasPoison).toBe(false)
    })

    it('可以同时设置两种药水状态', () => {
      const store = useGameStore()
      store.updateWitchPotions({ hasAntidote: false, hasPoison: false })
      expect(store.witchPotions.hasAntidote).toBe(false)
      expect(store.witchPotions.hasPoison).toBe(false)
    })
  })
})
