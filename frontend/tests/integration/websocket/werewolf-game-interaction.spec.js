/**
 * T13-T16: 狼人杀游戏交互集成测试
 * 测试完整的游戏流程和交互
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useGameStore } from '@/stores/game'
import websocket from '@/services/websocket'

// Mock API service
vi.mock('@/services/api', () => ({
  api: {
    getGameLogs: vi.fn()
  },
  werewolfApi: {
    startGame: vi.fn(),
    pauseGame: vi.fn(),
    resumeGame: vi.fn(),
    submitSpeech: vi.fn()
  }
}))

// Mock vue-router
const mockPush = vi.fn()
const mockParams = { code: 'ABC123' }
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockPush
  }),
  useRoute: () => ({
    params: mockParams
  })
}))

import { api, werewolfApi } from '@/services/api'

describe('Werewolf Game Interaction Integration Tests', () => {
  let pinia
  let store
  let mockSocket

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    store = useGameStore()
    vi.clearAllMocks()
    
    // Create mock socket
    mockSocket = {
      on: vi.fn(),
      off: vi.fn(),
      emit: vi.fn(),
      disconnect: vi.fn()
    }

    // Mock WebSocket service methods
    vi.spyOn(websocket, 'connect').mockImplementation(() => mockSocket)
    vi.spyOn(websocket, 'disconnect').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
    store.leaveRoom()
  })

  // ============ T13: 完整游戏开始流程测试 ============
  describe('T13: Complete Game Start Flow', () => {
    it('should complete full game start flow with host announcement', async () => {
      // 初始化房间状态
      store.setCurrentRoom({
        code: 'ABC123',
        status: 'Waiting',
        owner_id: 'player1'
      })
      store.setMyPlayerId('player1')

      werewolfApi.startGame.mockResolvedValue({
        success: true,
        game_id: 'game123'
      })

      // 1. 验证可以开始游戏
      expect(store.isHost).toBe(true)
      expect(store.isStarted).toBe(false)

      // 2. 调用开始游戏 API
      const response = await werewolfApi.startGame('ABC123')
      expect(response.success).toBe(true)

      // 3. 模拟接收 game_started WebSocket 事件
      store.setGameStarted(true)
      store.setCurrentRoom({
        ...store.currentRoom,
        status: 'In Progress'
      })

      // 4. 模拟主持人公告开始
      store.startHostAnnouncement('game_start')
      expect(store.hostAnnouncement.isStreaming).toBe(true)

      // 5. 模拟流式内容到达
      store.appendHostAnnouncementChunk('欢迎来到狼人杀游戏，')
      store.appendHostAnnouncementChunk('今晚将会是一个不平静的夜晚...')

      // 6. 完成公告
      const announcement = store.endHostAnnouncement()
      
      // 验证最终状态
      expect(store.isStarted).toBe(true)
      expect(store.currentRoom.status).toBe('In Progress')
      expect(store.announcementHistory.length).toBe(1)
      expect(store.announcementHistory[0].type).toBe('game_start')
    })

    it('should handle game start with role assignment', async () => {
      store.setCurrentRoom({
        code: 'ABC123',
        status: 'Waiting',
        owner_id: 'player1'
      })
      store.setMyPlayerId('player1')

      werewolfApi.startGame.mockResolvedValue({ success: true })

      // 开始游戏
      await werewolfApi.startGame('ABC123')
      store.setGameStarted(true)

      // 模拟角色分配事件
      store.setMyRole({
        name: '预言家',
        type: 'seer',
        team: 'villager',
        description: '每晚可以查验一名玩家的身份'
      })

      // 验证角色分配
      expect(store.myRole).not.toBeNull()
      expect(store.myRole.name).toBe('预言家')
      expect(store.myRole.team).toBe('villager')
    })

    it('should transition through phases after game start', async () => {
      store.setCurrentRoom({
        code: 'ABC123',
        status: 'In Progress',
        owner_id: 'player1'
      })
      store.setGameStarted(true)

      // 模拟阶段转换: 夜晚 -> 白天
      store.setPhase('night')
      expect(store.currentPhase).toBe('night')

      // 主持人公告夜晚开始
      store.startHostAnnouncement('phase_change')
      store.appendHostAnnouncementChunk('天黑请闭眼...')
      store.endHostAnnouncement()

      // 转换到白天
      store.setPhase('day')
      expect(store.currentPhase).toBe('day')

      // 公告历史应该有记录
      expect(store.announcementHistory.length).toBe(1)
    })
  })

  // ============ T14: 暂停/恢复流程测试 ============
  describe('T14: Pause/Resume Flow', () => {
    beforeEach(() => {
      store.setCurrentRoom({
        code: 'ABC123',
        status: 'In Progress',
        owner_id: 'player1'
      })
      store.setMyPlayerId('player1')
      store.setGameStarted(true)
    })

    it('should pause game and show pause announcement', async () => {
      werewolfApi.pauseGame.mockResolvedValue({ success: true })

      // 验证初始状态
      expect(store.isPaused).toBe(false)
      expect(store.isHost).toBe(true)

      // 调用暂停 API
      const response = await werewolfApi.pauseGame('ABC123')
      expect(response.success).toBe(true)

      // 模拟接收 game_paused 事件
      store.setGamePaused(true)
      
      // 模拟暂停公告
      store.startHostAnnouncement('game_paused')
      store.appendHostAnnouncementChunk('游戏已暂停，请等待房主恢复游戏...')
      store.endHostAnnouncement()

      expect(store.isPaused).toBe(true)
      expect(store.announcementHistory.length).toBe(1)
      expect(store.announcementHistory[0].type).toBe('game_paused')
    })

    it('should resume game and continue from pause point', async () => {
      // 先暂停
      store.setGamePaused(true)
      store.setPhase('discussion')
      store.dayNumber = 2

      werewolfApi.resumeGame.mockResolvedValue({ success: true })

      // 调用恢复 API
      const response = await werewolfApi.resumeGame('ABC123')
      expect(response.success).toBe(true)

      // 模拟接收 game_resumed 事件
      store.setGamePaused(false)
      
      // 模拟恢复公告
      store.startHostAnnouncement('game_resumed')
      store.appendHostAnnouncementChunk('游戏继续，')
      store.appendHostAnnouncementChunk('当前是第2天讨论阶段...')
      store.endHostAnnouncement()

      // 验证状态
      expect(store.isPaused).toBe(false)
      expect(store.currentPhase).toBe('discussion')
      expect(store.dayNumber).toBe(2)
    })

    it('should disable controls during pause for non-hosts', () => {
      store.setMyPlayerId('player2') // 非房主
      store.setGamePaused(true)
      store.setCurrentSpeaker(3, '玩家3', true)

      // 非房主应该看到暂停状态
      expect(store.isPaused).toBe(true)
      expect(store.isHost).toBe(false)
      
      // 等待输入应该仍然显示，但 UI 应该禁用（由组件处理）
      expect(store.waitingForInput).toBe(true)
    })

    it('should preserve game state across pause/resume cycle', async () => {
      // 设置游戏状态
      store.setPhase('vote')
      store.dayNumber = 3
      store.addGameLog({ type: 'speech', content: 'test speech' })
      store.startSpeechBubble(5, '玩家5')
      store.appendSpeechBubbleChunk(5, '我投票给3号')

      // 暂停
      store.setGamePaused(true)

      // 验证状态保留
      expect(store.currentPhase).toBe('vote')
      expect(store.dayNumber).toBe(3)
      expect(store.gameLogs.length).toBe(1)

      // 恢复
      store.setGamePaused(false)

      // 验证状态仍然保留
      expect(store.currentPhase).toBe('vote')
      expect(store.dayNumber).toBe(3)
      expect(store.gameLogs.length).toBe(1)
    })
  })

  // ============ T15: 玩家发言交互流程测试 ============
  describe('T15: Player Speech Interaction Flow', () => {
    beforeEach(() => {
      store.setCurrentRoom({
        code: 'ABC123',
        status: 'In Progress',
        owner_id: 'player1'
      })
      store.setGameStarted(true)
      store.setPhase('discussion')
    })

    it('should handle AI player speech with streaming bubble', async () => {
      // 设置当前发言者为 AI
      store.setCurrentSpeaker(5, 'AI玩家5', false)
      expect(store.currentSpeaker.isHuman).toBe(false)
      expect(store.waitingForInput).toBe(false)

      // 开始发言气泡
      store.startSpeechBubble(5, 'AI玩家5')
      expect(store.activeSpeechBubbles[5]).toBeDefined()
      expect(store.activeSpeechBubbles[5].isStreaming).toBe(true)

      // 流式添加内容
      store.appendSpeechBubbleChunk(5, '我认为')
      store.appendSpeechBubbleChunk(5, '3号很可疑，')
      store.appendSpeechBubbleChunk(5, '因为他昨晚沉默太久了。')

      expect(store.activeSpeechBubbles[5].content).toBe(
        '我认为3号很可疑，因为他昨晚沉默太久了。'
      )

      // 结束发言
      store.endSpeechBubble(5, '我认为3号很可疑，因为他昨晚沉默太久了。')
      expect(store.activeSpeechBubbles[5].isStreaming).toBe(false)

      // 同时添加到日志
      store.addGameLog({
        type: 'speech',
        player_id: 'ai5',
        player_name: 'AI玩家5',
        content: '我认为3号很可疑，因为他昨晚沉默太久了。'
      })

      // 清除发言者
      store.clearCurrentSpeaker()
      expect(store.currentSpeaker.seatNumber).toBeNull()
    })

    it('should handle human player speech input flow', async () => {
      store.setMyPlayerId('player3')

      // 设置当前发言者为真人玩家（自己）
      store.setCurrentSpeaker(3, '我', true)
      expect(store.currentSpeaker.isHuman).toBe(true)
      expect(store.waitingForInput).toBe(true)

      // 模拟玩家提交发言
      const speechContent = '我昨晚验了5号，他是狼人！'
      
      werewolfApi.submitSpeech.mockResolvedValue({
        success: true,
        message: 'Speech submitted'
      })

      const response = await werewolfApi.submitSpeech('ABC123', {
        player_id: 'player3',
        content: speechContent
      })

      expect(response.success).toBe(true)

      // 提交后更新状态
      store.setWaitingForInput(false)
      
      // 显示发言气泡
      store.startSpeechBubble(3, '我')
      store.endSpeechBubble(3, speechContent)

      // 添加到日志
      store.addGameLog({
        type: 'speech',
        player_id: 'player3',
        player_name: '我',
        content: speechContent
      })

      // 清除发言者
      store.clearCurrentSpeaker()

      expect(store.waitingForInput).toBe(false)
      expect(store.gameLogs.length).toBe(1)
    })

    it('should track speech order through multiple speakers', async () => {
      const speakers = [
        { seat: 1, name: '玩家1', isHuman: false },
        { seat: 2, name: '玩家2', isHuman: false },
        { seat: 3, name: '我', isHuman: true },
        { seat: 4, name: '玩家4', isHuman: false }
      ]

      for (const speaker of speakers) {
        // 设置发言者
        store.setCurrentSpeaker(speaker.seat, speaker.name, speaker.isHuman)
        
        if (speaker.isHuman) {
          expect(store.waitingForInput).toBe(true)
          // 模拟提交发言
          store.setWaitingForInput(false)
        }

        // 发言气泡
        store.startSpeechBubble(speaker.seat, speaker.name)
        store.endSpeechBubble(speaker.seat, `${speaker.name}的发言内容`)

        // 添加日志
        store.addGameLog({
          type: 'speech',
          player_name: speaker.name,
          content: `${speaker.name}的发言内容`
        })

        // 清除
        store.clearCurrentSpeaker()
      }

      expect(store.gameLogs.length).toBe(4)
    })

    it('should handle streaming speech log updates', () => {
      // 开始流式日志
      const logId = store.addStreamingLog({
        type: 'speech',
        player_id: 'ai7',
        player_name: 'AI玩家7',
        content: ''
      })

      expect(logId).toContain('streaming_ai7_')
      expect(store.gameLogs[0].isStreaming).toBe(true)

      // 更新内容
      store.updateStreamingLog('ai7', '第一段...')
      store.updateStreamingLog('ai7', '第一段...第二段...')
      store.updateStreamingLog('ai7', '第一段...第二段...完整发言。')

      expect(store.gameLogs[0].content).toBe('第一段...第二段...完整发言。')

      // 完成流式
      store.finalizeStreamingLog('ai7', '第一段...第二段...完整发言。')
      expect(store.gameLogs[0].isStreaming).toBe(false)
    })
  })

  // ============ T16: 断线重连恢复测试 ============
  describe('T16: Reconnection Recovery', () => {
    beforeEach(() => {
      store.setCurrentRoom({
        code: 'ABC123',
        status: 'In Progress',
        owner_id: 'player1'
      })
      store.setMyPlayerId('player2')
      store.setGameStarted(true)
    })

    it('should restore game state from server logs after reconnection', async () => {
      // 模拟断线前的状态
      store.setPhase('discussion')
      store.dayNumber = 2
      store.addGameLog({ id: 1, type: 'speech', content: 'old log' })

      // 模拟服务器返回的日志
      const serverLogs = [
        { log_type: 'game_start', content: '游戏开始', timestamp: '2024-01-01T00:00:00Z' },
        { log_type: 'phase_change', content: '天黑请闭眼', phase: 'night', day: 1 },
        { log_type: 'speech', content: '玩家1发言', player_id: 'p1', day: 1 },
        { log_type: 'phase_change', content: '天亮了', phase: 'day', day: 2 },
        { log_type: 'speech', content: '玩家2发言', player_id: 'p2', day: 2 }
      ]

      api.getGameLogs.mockResolvedValue({ logs: serverLogs })

      // 重连后获取日志
      const response = await api.getGameLogs('ABC123')
      expect(response.logs.length).toBe(5)

      // 清空旧日志
      store.clearGameLogs()
      expect(store.gameLogs.length).toBe(0)

      // 恢复日志
      response.logs.forEach(log => {
        store.addGameLog({
          type: log.log_type,
          content: log.content,
          player_id: log.player_id
        })
      })

      expect(store.gameLogs.length).toBe(5)
    })

    it('should restore announcement history after reconnection', async () => {
      // 模拟断线前有公告历史
      store.announcementHistory = [
        { type: 'old', content: 'old announcement' }
      ]

      // 模拟服务器返回的公告
      const serverAnnouncements = [
        { type: 'game_start', content: '欢迎来到狼人杀', day: 1 },
        { type: 'phase_change', content: '天黑请闭眼', day: 1 },
        { type: 'phase_change', content: '天亮了', day: 2 }
      ]

      // 清空旧历史
      store.clearAnnouncementHistory()
      expect(store.announcementHistory.length).toBe(0)

      // 恢复公告历史
      serverAnnouncements.forEach(ann => {
        store.addToAnnouncementHistory(ann)
      })

      expect(store.announcementHistory.length).toBe(3)
      expect(store.announcementHistory[0].type).toBe('game_start')
    })

    it('should restore current speaker state after reconnection', () => {
      // 模拟服务器告知当前发言者
      const currentSpeakerInfo = {
        seat_number: 5,
        player_name: 'AI玩家5',
        is_human: false
      }

      store.setCurrentSpeaker(
        currentSpeakerInfo.seat_number,
        currentSpeakerInfo.player_name,
        currentSpeakerInfo.is_human
      )

      expect(store.currentSpeaker.seatNumber).toBe(5)
      expect(store.currentSpeaker.playerName).toBe('AI玩家5')
      expect(store.waitingForInput).toBe(false)
    })

    it('should restore human player input state after reconnection', () => {
      store.setMyPlayerId('player3')

      // 模拟重连时轮到自己发言
      const currentSpeakerInfo = {
        seat_number: 3,
        player_name: '我',
        is_human: true
      }

      store.setCurrentSpeaker(
        currentSpeakerInfo.seat_number,
        currentSpeakerInfo.player_name,
        currentSpeakerInfo.is_human
      )

      expect(store.waitingForInput).toBe(true)
      expect(store.currentSpeaker.isHuman).toBe(true)
    })

    it('should handle reconnection during streaming announcement', () => {
      // 模拟重连时正好有流式公告在进行
      const streamingAnnouncement = {
        type: 'speech_summary',
        content: '讨论结束，现在开始投票',
        isStreaming: false // 服务器端已完成
      }

      store.setHostAnnouncement(streamingAnnouncement)

      expect(store.hostAnnouncement.content).toBe('讨论结束，现在开始投票')
      expect(store.hostAnnouncement.isStreaming).toBe(false)
    })

    it('should clear speech bubbles on reconnection', () => {
      // 断线前有活跃的发言气泡
      store.startSpeechBubble(3, '玩家3')
      store.appendSpeechBubbleChunk(3, '发言中...')
      store.startSpeechBubble(5, '玩家5')

      expect(Object.keys(store.activeSpeechBubbles).length).toBe(2)

      // 重连时清空气泡（因为发言状态可能已变化）
      store.clearAllSpeechBubbles()

      expect(Object.keys(store.activeSpeechBubbles).length).toBe(0)
    })

    it('should restore log level setting after reconnection', () => {
      // 直接通过 store 方法模拟恢复设置
      // 在真实场景中，这会从 localStorage 读取
      const savedLogLevel = 'detailed'
      store.setLogLevel(savedLogLevel)

      expect(store.logLevel).toBe('detailed')
    })

    it('should handle full reconnection flow', async () => {
      // 模拟完整的重连流程
      const serverGameState = {
        status: 'In Progress',
        day_number: 3,
        phase: 'vote',
        is_paused: false,
        current_speaker: {
          seat_number: 7,
          player_name: 'AI玩家7',
          is_human: false
        },
        logs: [
          { log_type: 'speech', content: 'log1' },
          { log_type: 'speech', content: 'log2' }
        ],
        announcements: [
          { type: 'phase_change', content: 'announcement1' }
        ]
      }

      api.getGameLogs.mockResolvedValue({ logs: serverGameState.logs })

      // 1. 清空旧状态
      store.clearGameLogs()
      store.clearAnnouncementHistory()
      store.clearAllSpeechBubbles()

      // 2. 恢复游戏状态
      store.setPhase(serverGameState.phase)
      store.dayNumber = serverGameState.day_number
      store.setGamePaused(serverGameState.is_paused)

      // 3. 恢复日志
      const logsResponse = await api.getGameLogs('ABC123')
      logsResponse.logs.forEach(log => {
        store.addGameLog({ type: log.log_type, content: log.content })
      })

      // 4. 恢复公告历史
      serverGameState.announcements.forEach(ann => {
        store.addToAnnouncementHistory(ann)
      })

      // 5. 恢复当前发言者
      store.setCurrentSpeaker(
        serverGameState.current_speaker.seat_number,
        serverGameState.current_speaker.player_name,
        serverGameState.current_speaker.is_human
      )

      // 验证恢复后的状态
      expect(store.currentPhase).toBe('vote')
      expect(store.dayNumber).toBe(3)
      expect(store.isPaused).toBe(false)
      expect(store.gameLogs.length).toBe(2)
      expect(store.announcementHistory.length).toBe(1)
      expect(store.currentSpeaker.seatNumber).toBe(7)
    })
  })
})
