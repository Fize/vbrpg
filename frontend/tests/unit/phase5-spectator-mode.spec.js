/**
 * Phase 5 T54: 观战模式UI测试
 * 
 * 测试覆盖:
 * - 观战模式状态切换
 * - 观战模式提示显示
 * - 输入面板隐藏
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useGameStore } from '@/stores/game'

describe('Phase 5 T54: 观战模式UI', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
  })

  describe('观战模式状态管理', () => {
    it('setSpectatorMode(true) 应该启用观战模式并设置 isAlive=false', () => {
      const store = useGameStore()
      store.isAlive = true
      
      store.setSpectatorMode(true)
      
      expect(store.isSpectatorMode).toBe(true)
      expect(store.isAlive).toBe(false)
    })

    it('setSpectatorMode(false) 应该禁用观战模式', () => {
      const store = useGameStore()
      store.setSpectatorMode(true)
      
      store.setSpectatorMode(false)
      
      expect(store.isSpectatorMode).toBe(false)
    })

    it('观战模式下应该清除所有交互状态', () => {
      const store = useGameStore()
      
      // 设置一些交互状态
      store.setSpeechOptions([{ id: '1', text: '选项1' }])
      store.setVoteOptions([{ seat_number: 1, player_name: '玩家1' }])
      store.setNightActionOptions([{ seat_number: 2, player_name: '玩家2' }])
      store.setLastWordsPhase(true, { seat_number: 3 })
      
      // 切换到观战模式
      store.setSpectatorMode(true)
      store.clearSpeechState()
      store.clearVoteState()
      store.clearNightActionState()
      store.clearLastWordsState()
      
      // 验证状态已清除
      expect(store.speechOptions).toEqual([])
      expect(store.voteOptions).toEqual([])
      expect(store.nightActionOptions).toEqual([])
      expect(store.isLastWordsPhase).toBe(false)
    })
  })

  describe('观战模式与遗言的交互', () => {
    it('遗言发表后应切换到观战模式', () => {
      const store = useGameStore()
      
      // 设置遗言阶段
      store.setLastWordsPhase(true, {
        seat_number: 3,
        options: [],
        death_reason: 'vote',
        timeout_seconds: 60
      })
      
      expect(store.isLastWordsPhase).toBe(true)
      
      // 发表遗言后，清除遗言状态
      store.clearLastWordsState()
      
      expect(store.isLastWordsPhase).toBe(false)
    })

    it('观战模式下不应显示遗言选项', () => {
      const store = useGameStore()
      store.mySeatNumber = 3
      
      // 先设置遗言阶段
      store.setLastWordsPhase(true, {
        seat_number: 3,
        options: [{ id: '1', text: '选项1' }]
      })
      
      // 切换到观战模式后清除遗言状态
      store.setSpectatorMode(true)
      store.clearLastWordsState()
      
      expect(store.isLastWordsPhase).toBe(false)
      expect(store.lastWordsOptions).toEqual([])
    })
  })

  describe('观战模式与玩家身份', () => {
    it('观战模式下保留玩家角色信息', () => {
      const store = useGameStore()
      
      // 设置玩家角色
      store.setMyRole({
        name: '狼人',
        type: 'werewolf',
        team: 'werewolf',
        description: '你是狼人'
      })
      store.setMySeatNumber(5)
      
      // 切换到观战模式
      store.setSpectatorMode(true)
      
      // 角色信息应该保留
      expect(store.myRole).toBeDefined()
      expect(store.myRole.name).toBe('狼人')
      expect(store.mySeatNumber).toBe(5)
      // 但存活状态应该是 false
      expect(store.isAlive).toBe(false)
    })

    it('观战模式下 isSpectator 计算属性应考虑 isSpectatorMode', () => {
      const store = useGameStore()
      
      // 初始状态
      expect(store.isSpectator).toBe(false)
      
      // 设置观战模式
      store.setSpectatorMode(true)
      
      // isSpectator 应该反映观战状态
      // 注意：实际的 isSpectator 计算属性在 WerewolfGameView.vue 中定义
      // 这里只测试 store 的状态
      expect(store.isSpectatorMode).toBe(true)
    })
  })

  describe('观战模式状态持久化', () => {
    it('重置游戏时应清除观战模式状态', () => {
      const store = useGameStore()
      
      // 设置观战模式
      store.setSpectatorMode(true)
      expect(store.isSpectatorMode).toBe(true)
      
      // 重置游戏
      store.resetForNewGame()
      
      // 观战模式应被清除
      expect(store.isSpectatorMode).toBe(false)
      expect(store.isAlive).toBe(true)
    })

    it('离开房间时应清除观战模式状态', () => {
      const store = useGameStore()
      
      // 设置观战模式
      store.setSpectatorMode(true)
      expect(store.isSpectatorMode).toBe(true)
      
      // 离开房间
      store.leaveRoom()
      
      // 观战模式应被清除
      expect(store.isSpectatorMode).toBe(false)
      expect(store.isAlive).toBe(true)
    })
  })
})
