import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import LobbyView from '@/views/LobbyView.vue'
import { useLobbyStore } from '@/stores/lobby'
import websocket from '@/services/websocket'

// Mock API service
vi.mock('@/services/api', () => ({
  roomsApi: {
    getRoom: vi.fn(),
    leaveRoom: vi.fn()
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

import { roomsApi } from '@/services/api'

describe('WebSocket Lobby Subscriptions', () => {
  let pinia
  let store

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    store = useLobbyStore()
    vi.clearAllMocks()

    // Mock WebSocket methods
    vi.spyOn(websocket, 'connect').mockImplementation(() => {})
    vi.spyOn(websocket, 'joinLobby').mockImplementation(() => {})
    vi.spyOn(websocket, 'leaveLobby').mockImplementation(() => {})
    vi.spyOn(websocket, 'offLobbyEvents').mockImplementation(() => {})
    vi.spyOn(websocket, 'onPlayerJoined').mockImplementation(() => {})
    vi.spyOn(websocket, 'onPlayerLeft').mockImplementation(() => {})
    vi.spyOn(websocket, 'onAIAgentAdded').mockImplementation(() => {})
    vi.spyOn(websocket, 'onAIAgentRemoved').mockImplementation(() => {})
    vi.spyOn(websocket, 'onOwnershipTransferred').mockImplementation(() => {})
    vi.spyOn(websocket, 'onRoomDissolved').mockImplementation(() => {})
    vi.spyOn(websocket, 'onLobbyJoined').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Lobby Room Subscription', () => {
    it('joins lobby WebSocket room on component mount', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: {
          code: 'ABC123',
          status: 'Waiting',
          max_players: 4,
          current_participant_count: 1
        },
        participants: [],
        is_owner: true
      })

      mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))

      expect(websocket.connect).toHaveBeenCalled()
      expect(websocket.joinLobby).toHaveBeenCalledWith('ABC123')
    })

    it('leaves lobby WebSocket room on component unmount', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: {
          code: 'ABC123',
          status: 'Waiting',
          max_players: 4,
          current_participant_count: 1
        },
        participants: [],
        is_owner: true
      })

      const wrapper = mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))

      wrapper.unmount()

      expect(websocket.leaveLobby).toHaveBeenCalledWith('ABC123')
      expect(websocket.offLobbyEvents).toHaveBeenCalled()
    })
  })

  describe('Player Events', () => {
    it('registers listener for player_joined event', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: { code: 'ABC123', status: 'Waiting' },
        participants: [],
        is_owner: true
      })

      mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))

      expect(websocket.onPlayerJoined).toHaveBeenCalled()
    })

    it('registers listener for player_left event', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: { code: 'ABC123', status: 'Waiting' },
        participants: [],
        is_owner: true
      })

      mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))

      expect(websocket.onPlayerLeft).toHaveBeenCalled()
    })

    it('adds participant to store when player_joined event received', async () => {
      let playerJoinedHandler = null

      roomsApi.getRoom.mockResolvedValue({
        room: { code: 'ABC123', status: 'Waiting' },
        participants: [],
        is_owner: true
      })

      websocket.onPlayerJoined.mockImplementation((handler) => {
        playerJoinedHandler = handler
      })

      mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))

      // Simulate player_joined event
      if (playerJoinedHandler) {
        playerJoinedHandler({
          player: {
            id: 'p2',
            name: 'New Player',
            participant_type: 'human'
          }
        })
      }

      expect(store.participants).toHaveLength(1)
      expect(store.participants[0].name).toBe('New Player')
    })

    it('removes participant from store when player_left event received', async () => {
      let playerLeftHandler = null

      roomsApi.getRoom.mockResolvedValue({
        room: { code: 'ABC123', status: 'Waiting' },
        participants: [
          { id: 'p1', name: 'Player 1' },
          { id: 'p2', name: 'Player 2' }
        ],
        is_owner: true
      })

      websocket.onPlayerLeft.mockImplementation((handler) => {
        playerLeftHandler = handler
      })

      mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))

      expect(store.participants).toHaveLength(2)

      // Simulate player_left event
      if (playerLeftHandler) {
        playerLeftHandler({ player_id: 'p2' })
      }

      expect(store.participants).toHaveLength(1)
      expect(store.participants[0].id).toBe('p1')
    })
  })

  describe('AI Agent Events', () => {
    it('registers listener for ai_agent_added event', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: { code: 'ABC123', status: 'Waiting' },
        participants: [],
        is_owner: true
      })

      mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))

      expect(websocket.onAIAgentAdded).toHaveBeenCalled()
    })

    it('registers listener for ai_agent_removed event', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: { code: 'ABC123', status: 'Waiting' },
        participants: [],
        is_owner: true
      })

      mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))

      expect(websocket.onAIAgentRemoved).toHaveBeenCalled()
    })

    it('adds AI agent to store when ai_agent_added event received', async () => {
      let aiAgentAddedHandler = null

      roomsApi.getRoom.mockResolvedValue({
        room: { code: 'ABC123', status: 'Waiting' },
        participants: [],
        is_owner: true
      })

      websocket.onAIAgentAdded.mockImplementation((handler) => {
        aiAgentAddedHandler = handler
      })

      mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))

      // Simulate ai_agent_added event
      if (aiAgentAddedHandler) {
        aiAgentAddedHandler({
          ai_agent: {
            id: 'ai1',
            name: 'AI玩家1',
            participant_type: 'ai'
          }
        })
      }

      expect(store.participants).toHaveLength(1)
      expect(store.participants[0].participant_type).toBe('ai')
    })

    it('removes AI agent from store when ai_agent_removed event received', async () => {
      let aiAgentRemovedHandler = null

      roomsApi.getRoom.mockResolvedValue({
        room: { code: 'ABC123', status: 'Waiting' },
        participants: [
          { id: 'p1', name: 'Human', participant_type: 'human' },
          { id: 'ai1', name: 'AI玩家1', participant_type: 'ai' }
        ],
        is_owner: true
      })

      websocket.onAIAgentRemoved.mockImplementation((handler) => {
        aiAgentRemovedHandler = handler
      })

      mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))

      expect(store.participants).toHaveLength(2)

      // Simulate ai_agent_removed event
      if (aiAgentRemovedHandler) {
        aiAgentRemovedHandler({ ai_agent_id: 'ai1' })
      }

      expect(store.participants).toHaveLength(1)
      expect(store.participants[0].participant_type).toBe('human')
    })
  })

  describe('Ownership and Room Events', () => {
    it('registers listener for ownership_transferred event', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: { code: 'ABC123', status: 'Waiting' },
        participants: [],
        is_owner: true
      })

      mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))

      expect(websocket.onOwnershipTransferred).toHaveBeenCalled()
    })

    it('registers listener for room_dissolved event', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: { code: 'ABC123', status: 'Waiting' },
        participants: [],
        is_owner: true
      })

      mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))

      expect(websocket.onRoomDissolved).toHaveBeenCalled()
    })

    it('updates ownership when ownership_transferred event received', async () => {
      let ownershipTransferredHandler = null

      roomsApi.getRoom.mockResolvedValue({
        room: { code: 'ABC123', status: 'Waiting', owner_id: 'p1' },
        participants: [
          { id: 'p1', name: 'Owner', is_owner: true },
          { id: 'p2', name: 'Player 2', is_owner: false }
        ],
        is_owner: true
      })

      websocket.onOwnershipTransferred.mockImplementation((handler) => {
        ownershipTransferredHandler = handler
      })

      mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))

      // Simulate ownership_transferred event
      if (ownershipTransferredHandler) {
        ownershipTransferredHandler({ new_owner_id: 'p2' })
      }

      // Check that ownership flags are updated
      const newOwner = store.participants.find(p => p.id === 'p2')
      const oldOwner = store.participants.find(p => p.id === 'p1')
      
      expect(newOwner.is_owner).toBe(true)
      expect(oldOwner.is_owner).toBe(false)
    })

    it('navigates to home when room_dissolved event received', async () => {
      let roomDissolvedHandler = null

      roomsApi.getRoom.mockResolvedValue({
        room: { code: 'ABC123', status: 'Waiting' },
        participants: [],
        is_owner: true
      })

      websocket.onRoomDissolved.mockImplementation((handler) => {
        roomDissolvedHandler = handler
      })

      mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))

      // Simulate room_dissolved event
      if (roomDissolvedHandler) {
        roomDissolvedHandler()
      }

      expect(mockPush).toHaveBeenCalledWith({ name: 'home' })
      expect(store.currentRoom).toBeNull()
    })
  })
})
