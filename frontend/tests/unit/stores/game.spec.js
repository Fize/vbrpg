/**
 * T12: Game Store 新状态单元测试
 * 测试 F1-F4, F9, F37-F40 新增的游戏控制状态
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useGameStore } from '@/stores/game'

describe('Game Store - New States (F1-F4, F9, F37-F40)', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useGameStore()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  // ============ F1: 游戏控制状态测试 ============
  describe('F1: Game Control State', () => {
    it('should initialize with isStarted = false', () => {
      expect(store.isStarted).toBe(false)
    })

    it('should initialize with isPaused = false', () => {
      expect(store.isPaused).toBe(false)
    })

    it('should set game started state', () => {
      store.setGameStarted(true)
      expect(store.isStarted).toBe(true)
      expect(store.isPaused).toBe(false)
    })

    it('should reset isPaused when game starts', () => {
      store.isPaused = true
      store.setGameStarted(true)
      expect(store.isPaused).toBe(false)
    })

    it('should set game paused state', () => {
      store.setGamePaused(true)
      expect(store.isPaused).toBe(true)
    })

    it('should unpause game', () => {
      store.setGamePaused(true)
      store.setGamePaused(false)
      expect(store.isPaused).toBe(false)
    })
  })

  // ============ F2: 主持人公告状态测试 ============
  describe('F2: Host Announcement State', () => {
    it('should initialize with empty hostAnnouncement', () => {
      expect(store.hostAnnouncement).toEqual({
        type: null,
        content: '',
        isStreaming: false
      })
    })

    it('should initialize with empty announcementHistory', () => {
      expect(store.announcementHistory).toEqual([])
    })

    it('should start host announcement with streaming', () => {
      store.startHostAnnouncement('phase_change', { phase: 'night' })
      
      expect(store.hostAnnouncement.type).toBe('phase_change')
      expect(store.hostAnnouncement.content).toBe('')
      expect(store.hostAnnouncement.isStreaming).toBe(true)
      expect(store.hostAnnouncement.metadata).toEqual({ phase: 'night' })
    })

    it('should append chunks to streaming announcement', () => {
      store.startHostAnnouncement('game_start')
      store.appendHostAnnouncementChunk('欢迎来到')
      store.appendHostAnnouncementChunk('狼人杀游戏')
      
      expect(store.hostAnnouncement.content).toBe('欢迎来到狼人杀游戏')
    })

    it('should not append chunks when not streaming', () => {
      store.hostAnnouncement = {
        type: 'test',
        content: 'original',
        isStreaming: false
      }
      store.appendHostAnnouncementChunk('new chunk')
      
      expect(store.hostAnnouncement.content).toBe('original')
    })

    it('should end host announcement and add to history', () => {
      store.dayNumber = 2
      store.startHostAnnouncement('phase_change')
      store.appendHostAnnouncementChunk('天亮了')
      
      const announcement = store.endHostAnnouncement('天亮了，开始讨论')
      
      expect(announcement.type).toBe('phase_change')
      expect(announcement.content).toBe('天亮了，开始讨论')
      expect(announcement.day).toBe(2)
      expect(store.announcementHistory.length).toBe(1)
      expect(store.hostAnnouncement.type).toBeNull()
      expect(store.hostAnnouncement.isStreaming).toBe(false)
    })

    it('should use accumulated content if fullContent not provided', () => {
      store.startHostAnnouncement('test')
      store.appendHostAnnouncementChunk('accumulated')
      
      const announcement = store.endHostAnnouncement()
      
      expect(announcement.content).toBe('accumulated')
    })
  })

  // ============ F3: 发言气泡状态测试 ============
  describe('F3: Speech Bubble State', () => {
    it('should initialize with empty activeSpeechBubbles', () => {
      expect(store.activeSpeechBubbles).toEqual({})
    })

    it('should start speech bubble with streaming', () => {
      store.startSpeechBubble(3, '小明')
      
      expect(store.activeSpeechBubbles[3]).toBeDefined()
      expect(store.activeSpeechBubbles[3].playerName).toBe('小明')
      expect(store.activeSpeechBubbles[3].content).toBe('')
      expect(store.activeSpeechBubbles[3].isStreaming).toBe(true)
    })

    it('should append chunks to speech bubble', () => {
      store.startSpeechBubble(5, '玩家5')
      store.appendSpeechBubbleChunk(5, '我觉得')
      store.appendSpeechBubbleChunk(5, '2号很可疑')
      
      expect(store.activeSpeechBubbles[5].content).toBe('我觉得2号很可疑')
    })

    it('should not append to non-existent bubble', () => {
      store.appendSpeechBubbleChunk(99, 'test')
      expect(store.activeSpeechBubbles[99]).toBeUndefined()
    })

    it('should end speech bubble and set auto-hide timer', () => {
      store.startSpeechBubble(7, '玩家7')
      store.appendSpeechBubbleChunk(7, '发言中')
      store.endSpeechBubble(7, '完整发言内容')
      
      expect(store.activeSpeechBubbles[7].content).toBe('完整发言内容')
      expect(store.activeSpeechBubbles[7].isStreaming).toBe(false)
      
      // 验证5秒后自动清除
      vi.advanceTimersByTime(5000)
      expect(store.activeSpeechBubbles[7]).toBeUndefined()
    })

    it('should clear specific speech bubble', () => {
      store.startSpeechBubble(1, '玩家1')
      store.startSpeechBubble(2, '玩家2')
      store.clearSpeechBubble(1)
      
      expect(store.activeSpeechBubbles[1]).toBeUndefined()
      expect(store.activeSpeechBubbles[2]).toBeDefined()
    })

    it('should clear all speech bubbles', () => {
      store.startSpeechBubble(1, '玩家1')
      store.startSpeechBubble(2, '玩家2')
      store.startSpeechBubble(3, '玩家3')
      store.clearAllSpeechBubbles()
      
      expect(store.activeSpeechBubbles).toEqual({})
    })
  })

  // ============ F4: 日志级别状态测试 ============
  describe('F4: Log Level State', () => {
    it('should initialize with logLevel = basic', () => {
      expect(store.logLevel).toBe('basic')
    })

    it('should set log level to detailed', () => {
      store.setLogLevel('detailed')
      expect(store.logLevel).toBe('detailed')
    })

    it('should set log level back to basic', () => {
      store.setLogLevel('detailed')
      store.setLogLevel('basic')
      expect(store.logLevel).toBe('basic')
    })

    it('should ignore invalid log levels', () => {
      store.setLogLevel('invalid')
      expect(store.logLevel).toBe('basic')
    })
  })

  // ============ F9: 当前发言者状态测试 ============
  describe('F9: Current Speaker State', () => {
    it('should initialize with empty currentSpeaker', () => {
      expect(store.currentSpeaker).toEqual({
        seatNumber: null,
        playerName: '',
        isHuman: false
      })
    })

    it('should initialize with waitingForInput = false', () => {
      expect(store.waitingForInput).toBe(false)
    })

    it('should set current speaker (AI player)', () => {
      store.setCurrentSpeaker(5, 'AI玩家5', false)
      
      expect(store.currentSpeaker.seatNumber).toBe(5)
      expect(store.currentSpeaker.playerName).toBe('AI玩家5')
      expect(store.currentSpeaker.isHuman).toBe(false)
      expect(store.waitingForInput).toBe(false)
    })

    it('should set current speaker (human player) and waitingForInput', () => {
      store.setCurrentSpeaker(3, '真人玩家', true)
      
      expect(store.currentSpeaker.seatNumber).toBe(3)
      expect(store.currentSpeaker.playerName).toBe('真人玩家')
      expect(store.currentSpeaker.isHuman).toBe(true)
      expect(store.waitingForInput).toBe(true)
    })

    it('should clear current speaker', () => {
      store.setCurrentSpeaker(5, '玩家5', true)
      store.clearCurrentSpeaker()
      
      expect(store.currentSpeaker.seatNumber).toBeNull()
      expect(store.currentSpeaker.playerName).toBe('')
      expect(store.currentSpeaker.isHuman).toBe(false)
      expect(store.waitingForInput).toBe(false)
    })

    it('should set waiting for input state', () => {
      store.setWaitingForInput(true)
      expect(store.waitingForInput).toBe(true)
      
      store.setWaitingForInput(false)
      expect(store.waitingForInput).toBe(false)
    })
  })

  // ============ F37-F40: 断线重连辅助方法测试 ============
  describe('F37-F40: Reconnection Helper Methods', () => {
    it('should clear game logs', () => {
      store.gameLogs = [
        { id: 1, content: 'log 1' },
        { id: 2, content: 'log 2' }
      ]
      store.clearGameLogs()
      
      expect(store.gameLogs).toEqual([])
    })

    it('should clear announcement history', () => {
      store.announcementHistory = [
        { type: 'test', content: 'announcement 1' },
        { type: 'test', content: 'announcement 2' }
      ]
      store.clearAnnouncementHistory()
      
      expect(store.announcementHistory).toEqual([])
    })

    it('should add to announcement history', () => {
      const announcement = {
        type: 'phase_change',
        content: '天黑请闭眼',
        time: '2024-01-01T00:00:00Z'
      }
      store.addToAnnouncementHistory(announcement)
      
      expect(store.announcementHistory.length).toBe(1)
      expect(store.announcementHistory[0]).toEqual(announcement)
    })

    it('should set host announcement directly', () => {
      const announcement = {
        type: 'game_start',
        content: '游戏开始',
        isStreaming: false,
        metadata: { game_id: 123 }
      }
      store.setHostAnnouncement(announcement)
      
      expect(store.hostAnnouncement.type).toBe('game_start')
      expect(store.hostAnnouncement.content).toBe('游戏开始')
      expect(store.hostAnnouncement.isStreaming).toBe(false)
      expect(store.hostAnnouncement.metadata).toEqual({ game_id: 123 })
    })

    it('should handle partial announcement data', () => {
      store.setHostAnnouncement({ type: 'partial' })
      
      expect(store.hostAnnouncement.type).toBe('partial')
      expect(store.hostAnnouncement.content).toBe('')
      expect(store.hostAnnouncement.isStreaming).toBe(false)
      expect(store.hostAnnouncement.metadata).toEqual({})
    })
  })

  // ============ 流式日志测试 ============
  describe('Streaming Log Methods', () => {
    it('should add streaming log with isStreaming flag', () => {
      store.dayNumber = 1
      store.currentPhase = 'discussion'
      
      const logId = store.addStreamingLog({
        type: 'speech',
        player_id: 'player1',
        player_name: '玩家1',
        content: ''
      })
      
      expect(logId).toContain('streaming_player1_')
      expect(store.gameLogs.length).toBe(1)
      expect(store.gameLogs[0].isStreaming).toBe(true)
      expect(store.gameLogs[0].day).toBe(1)
      expect(store.gameLogs[0].phase).toBe('discussion')
    })

    it('should update streaming log content', () => {
      store.addStreamingLog({
        type: 'speech',
        player_id: 'player2',
        player_name: '玩家2',
        content: ''
      })
      
      store.updateStreamingLog('player2', '我认为...')
      store.updateStreamingLog('player2', '我认为3号是狼')
      
      expect(store.gameLogs[0].content).toBe('我认为3号是狼')
    })

    it('should finalize streaming log', () => {
      store.addStreamingLog({
        type: 'speech',
        player_id: 'player3',
        content: ''
      })
      
      store.finalizeStreamingLog('player3', '完整的发言内容')
      
      expect(store.gameLogs[0].content).toBe('完整的发言内容')
      expect(store.gameLogs[0].isStreaming).toBe(false)
    })
  })

  // ============ leaveRoom 重置测试 ============
  describe('leaveRoom should reset all new states', () => {
    it('should reset F1-F4, F9 states when leaving room', () => {
      // 设置各种状态
      store.setGameStarted(true)
      store.setGamePaused(true)
      store.startHostAnnouncement('test')
      store.appendHostAnnouncementChunk('content')
      store.endHostAnnouncement('final')
      store.startSpeechBubble(1, '玩家1')
      store.setLogLevel('detailed')
      store.setCurrentSpeaker(5, '玩家5', true)
      
      // 离开房间
      store.leaveRoom()
      
      // 验证所有新状态已重置
      expect(store.isStarted).toBe(false)
      expect(store.isPaused).toBe(false)
      expect(store.hostAnnouncement).toEqual({ type: null, content: '', isStreaming: false })
      expect(store.announcementHistory).toEqual([])
      expect(store.activeSpeechBubbles).toEqual({})
      expect(store.logLevel).toBe('basic')
      expect(store.currentSpeaker).toEqual({ seatNumber: null, playerName: '', isHuman: false })
      expect(store.waitingForInput).toBe(false)
    })
  })
})
