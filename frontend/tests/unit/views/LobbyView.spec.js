import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import LobbyView from '@/views/LobbyView.vue'
import { useLobbyStore } from '@/stores/lobby'

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

describe('LobbyView', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()
  })

  describe('Room Information Display', () => {
    it('displays room code', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: {
          code: 'ABC123',
          game_type: 'crime-scene',
          status: 'Waiting',
          max_players: 4,
          current_participant_count: 2
        },
        participants: [],
        is_owner: false
      })

      const wrapper = mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))
      await wrapper.vm.$nextTick()
      
      expect(wrapper.text()).toContain('ABC123')
    })

    it('displays game type', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: {
          code: 'ABC123',
          game_type: 'crime-scene',
          status: 'Waiting'
        },
        participants: [],
        is_owner: false
      })

      const wrapper = mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))
      await wrapper.vm.$nextTick()
      
      expect(wrapper.text()).toContain('犯罪现场')
    })

    it('displays participant count', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: {
          code: 'ABC123',
          game_type: 'crime-scene',
          max_players: 4,
          current_participant_count: 2
        },
        participants: [
          { id: 'p1', name: 'Alice' },
          { id: 'p2', name: 'Bob' }
        ],
        is_owner: false
      })

      const wrapper = mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))
      await wrapper.vm.$nextTick()
      
      expect(wrapper.text()).toContain('2/4')
    })

    it('displays room status', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: {
          code: 'ABC123',
          status: 'Waiting'
        },
        participants: [],
        is_owner: false
      })

      const wrapper = mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))
      await wrapper.vm.$nextTick()
      
      expect(wrapper.text()).toContain('等待中')
    })
  })

  describe('Participant List', () => {
    it('shows all participants in list', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: { code: 'ABC123' },
        participants: [
          { id: 'p1', name: 'Alice', participant_type: 'human' },
          { id: 'p2', name: 'Bob', participant_type: 'human' },
          { id: 'ai1', name: 'AI玩家1', participant_type: 'ai' }
        ],
        is_owner: false
      })

      const wrapper = mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))
      await wrapper.vm.$nextTick()
      
      expect(wrapper.text()).toContain('Alice')
      expect(wrapper.text()).toContain('Bob')
      expect(wrapper.text()).toContain('AI玩家1')
    })

    it('shows AI badge for AI agents', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: { code: 'ABC123' },
        participants: [
          { id: 'ai1', name: 'AI玩家1', participant_type: 'ai' }
        ],
        is_owner: false
      })

      const wrapper = mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))
      await wrapper.vm.$nextTick()
      
      expect(wrapper.html()).toContain('ai-badge')
    })

    it('shows owner badge for room owner', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: { code: 'ABC123' },
        participants: [
          { id: 'p1', name: 'Alice', is_owner: true }
        ],
        is_owner: false
      })

      const wrapper = mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))
      await wrapper.vm.$nextTick()
      
      expect(wrapper.html()).toContain('owner-badge')
    })

    it('shows no badges for regular human players', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: { code: 'ABC123' },
        participants: [
          { id: 'p1', name: 'Alice', participant_type: 'human', is_owner: false }
        ],
        is_owner: false
      })

      const wrapper = mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))
      await wrapper.vm.$nextTick()
      
      const html = wrapper.html()
      expect(html).not.toContain('ai-badge')
      expect(html).not.toContain('owner-badge')
    })
  })

  describe('Leave Room Functionality', () => {
    it('shows leave button when room status is Waiting', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: {
          code: 'ABC123',
          status: 'Waiting'
        },
        participants: [],
        is_owner: false
      })

      const wrapper = mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))
      await wrapper.vm.$nextTick()
      
      const leaveButton = wrapper.find('.leave-button')
      expect(leaveButton.exists()).toBe(true)
    })

    it('calls leave room API when leave button clicked', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: {
          code: 'ABC123',
          status: 'Waiting'
        },
        participants: [],
        is_owner: false
      })
      roomsApi.leaveRoom.mockResolvedValue({})

      const wrapper = mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))
      await wrapper.vm.$nextTick()
      
      const leaveButton = wrapper.find('.leave-button')
      await leaveButton.trigger('click')

      expect(roomsApi.leaveRoom).toHaveBeenCalledWith('ABC123')
    })

    it('navigates to home after successful leave', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: {
          code: 'ABC123',
          status: 'Waiting'
        },
        participants: [],
        is_owner: false
      })
      roomsApi.leaveRoom.mockResolvedValue({})

      const wrapper = mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))
      await wrapper.vm.$nextTick()
      
      const leaveButton = wrapper.find('.leave-button')
      await leaveButton.trigger('click')
      await new Promise(resolve => setTimeout(resolve, 10))

      expect(mockPush).toHaveBeenCalledWith({ name: 'home' })
    })

    it('clears lobby store after successful leave', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: {
          code: 'ABC123',
          status: 'Waiting'
        },
        participants: [],
        is_owner: false
      })
      roomsApi.leaveRoom.mockResolvedValue({})

      const wrapper = mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))
      await wrapper.vm.$nextTick()
      
      const store = useLobbyStore()
      const leaveButton = wrapper.find('.leave-button')
      await leaveButton.trigger('click')
      await new Promise(resolve => setTimeout(resolve, 10))

      expect(store.currentRoom).toBeNull()
      expect(store.participants).toEqual([])
    })

    it('hides leave button when room status is In Progress', async () => {
      roomsApi.getRoom.mockResolvedValue({
        room: {
          code: 'ABC123',
          status: 'In Progress'
        },
        participants: [],
        is_owner: false
      })

      const wrapper = mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))
      await wrapper.vm.$nextTick()
      
      const leaveButton = wrapper.find('.leave-button')
      expect(leaveButton.exists()).toBe(false)
    })
  })

  describe('Loading and Error States', () => {
    it('shows loading indicator while fetching room data', async () => {
      roomsApi.getRoom.mockImplementation(() => new Promise(() => {})) // Never resolves

      const wrapper = mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('加载房间信息')
    })

    it('shows error message when room not found', async () => {
      const error = new Error('Room not found')
      error.response = { status: 404 }
      roomsApi.getRoom.mockRejectedValue(error)

      const wrapper = mount(LobbyView, {
        global: {
          plugins: [pinia]
        }
      })

      await new Promise(resolve => setTimeout(resolve, 10))
      await wrapper.vm.$nextTick()
      
      expect(wrapper.text()).toContain('房间不存在')
    })
  })
})
