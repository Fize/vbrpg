import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AIAgentControls from '@/components/lobby/AIAgentControls.vue'
import { useLobbyStore } from '@/stores/lobby'

// Mock API service
vi.mock('@/services/api', () => ({
  roomsApi: {
    addAIAgent: vi.fn(),
    removeAIAgent: vi.fn()
  }
}))

import { roomsApi } from '@/services/api'

describe('AIAgentControls', () => {
  let pinia
  let store

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    store = useLobbyStore()
    vi.clearAllMocks()
  })

  describe('Add AI Agent Button', () => {
    it('shows add AI button when user is owner', () => {
      store.joinRoom({
        room: { code: 'ABC123', status: 'Waiting', max_players: 4, current_participant_count: 1 },
        participants: [],
        is_owner: true
      })

      const wrapper = mount(AIAgentControls, {
        global: {
          plugins: [pinia]
        }
      })

      const addButton = wrapper.find('.add-ai-button')
      expect(addButton.exists()).toBe(true)
    })

    it('hides add AI button when user is not owner', () => {
      store.joinRoom({
        room: { code: 'ABC123', status: 'Waiting', max_players: 4, current_participant_count: 2 },
        participants: [],
        is_owner: false
      })

      const wrapper = mount(AIAgentControls, {
        global: {
          plugins: [pinia]
        }
      })

      const addButton = wrapper.find('.add-ai-button')
      expect(addButton.exists()).toBe(false)
    })

    it('disables add AI button when room is at capacity', () => {
      store.joinRoom({
        room: { code: 'ABC123', status: 'Waiting', max_players: 4, current_participant_count: 4 },
        participants: [],
        is_owner: true
      })

      const wrapper = mount(AIAgentControls, {
        global: {
          plugins: [pinia]
        }
      })

      const addButton = wrapper.find('.add-ai-button')
      expect(addButton.attributes('disabled')).toBeDefined()
    })

    it('enables add AI button when room has capacity', () => {
      store.joinRoom({
        room: { code: 'ABC123', status: 'Waiting', max_players: 4, current_participant_count: 2 },
        participants: [],
        is_owner: true
      })

      const wrapper = mount(AIAgentControls, {
        global: {
          plugins: [pinia]
        }
      })

      const addButton = wrapper.find('.add-ai-button')
      expect(addButton.attributes('disabled')).toBeUndefined()
    })

    it('calls API to add AI agent when button clicked', async () => {
      store.joinRoom({
        room: { code: 'ABC123', status: 'Waiting', max_players: 4, current_participant_count: 1 },
        participants: [],
        is_owner: true
      })

      roomsApi.addAIAgent.mockResolvedValue({
        ai_agent: {
          id: 'ai1',
          name: 'AI玩家1',
          participant_type: 'ai'
        }
      })

      const wrapper = mount(AIAgentControls, {
        global: {
          plugins: [pinia]
        }
      })

      const addButton = wrapper.find('.add-ai-button')
      await addButton.trigger('click')

      expect(roomsApi.addAIAgent).toHaveBeenCalledWith('ABC123')
    })

    it('shows loading state while adding AI agent', async () => {
      store.joinRoom({
        room: { code: 'ABC123', status: 'Waiting', max_players: 4, current_participant_count: 1 },
        participants: [],
        is_owner: true
      })

      roomsApi.addAIAgent.mockImplementation(() => new Promise(() => {})) // Never resolves

      const wrapper = mount(AIAgentControls, {
        global: {
          plugins: [pinia]
        }
      })

      const addButton = wrapper.find('.add-ai-button')
      await addButton.trigger('click')
      await wrapper.vm.$nextTick()

      expect(addButton.attributes('disabled')).toBeDefined()
      expect(wrapper.text()).toContain('添加中')
    })

    it('displays error message when add AI fails with 409', async () => {
      store.joinRoom({
        room: { code: 'ABC123', status: 'Waiting', max_players: 4, current_participant_count: 1 },
        participants: [],
        is_owner: true
      })

      const error = new Error('Room full')
      error.response = { status: 409 }
      roomsApi.addAIAgent.mockRejectedValue(error)

      const wrapper = mount(AIAgentControls, {
        global: {
          plugins: [pinia]
        }
      })

      const addButton = wrapper.find('.add-ai-button')
      await addButton.trigger('click')
      await new Promise(resolve => setTimeout(resolve, 10))
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('房间已满')
    })
  })

  describe('Remove AI Agent Button', () => {
    it('shows remove button for each AI agent when user is owner', () => {
      store.joinRoom({
        room: { code: 'ABC123', status: 'Waiting', max_players: 4, current_participant_count: 3 },
        participants: [
          { id: 'p1', name: 'Human', participant_type: 'human', is_owner: true },
          { id: 'ai1', name: 'AI玩家1', participant_type: 'ai' },
          { id: 'ai2', name: 'AI玩家2', participant_type: 'ai' }
        ],
        is_owner: true
      })

      const wrapper = mount(AIAgentControls, {
        global: {
          plugins: [pinia]
        }
      })

      const removeButtons = wrapper.findAll('.remove-ai-button')
      expect(removeButtons.length).toBe(2)
    })

    it('hides remove buttons when user is not owner', () => {
      store.joinRoom({
        room: { code: 'ABC123', status: 'Waiting', max_players: 4, current_participant_count: 3 },
        participants: [
          { id: 'p1', name: 'Owner', participant_type: 'human', is_owner: true },
          { id: 'p2', name: 'Me', participant_type: 'human', is_owner: false },
          { id: 'ai1', name: 'AI玩家1', participant_type: 'ai' }
        ],
        is_owner: false
      })

      const wrapper = mount(AIAgentControls, {
        global: {
          plugins: [pinia]
        }
      })

      const removeButtons = wrapper.findAll('.remove-ai-button')
      expect(removeButtons.length).toBe(0)
    })

    it('calls API to remove AI agent when button clicked', async () => {
      store.joinRoom({
        room: { code: 'ABC123', status: 'Waiting', max_players: 4, current_participant_count: 2 },
        participants: [
          { id: 'p1', name: 'Human', participant_type: 'human', is_owner: true },
          { id: 'ai1', name: 'AI玩家1', participant_type: 'ai' }
        ],
        is_owner: true
      })

      roomsApi.removeAIAgent.mockResolvedValue()

      const wrapper = mount(AIAgentControls, {
        global: {
          plugins: [pinia]
        }
      })

      const removeButton = wrapper.find('.remove-ai-button')
      await removeButton.trigger('click')

      expect(roomsApi.removeAIAgent).toHaveBeenCalledWith('ABC123', 'ai1')
    })

    it('displays error message when remove AI fails with 403', async () => {
      store.joinRoom({
        room: { code: 'ABC123', status: 'Waiting', max_players: 4, current_participant_count: 2 },
        participants: [
          { id: 'p1', name: 'Human', participant_type: 'human', is_owner: true },
          { id: 'ai1', name: 'AI玩家1', participant_type: 'ai' }
        ],
        is_owner: true
      })

      const error = new Error('Forbidden')
      error.response = { status: 403 }
      roomsApi.removeAIAgent.mockRejectedValue(error)

      const wrapper = mount(AIAgentControls, {
        global: {
          plugins: [pinia]
        }
      })

      const removeButton = wrapper.find('.remove-ai-button')
      await removeButton.trigger('click')
      await new Promise(resolve => setTimeout(resolve, 10))
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('无权限')
    })
  })

  describe('No AI Agents', () => {
    it('shows message when no AI agents exist', () => {
      store.joinRoom({
        room: { code: 'ABC123', status: 'Waiting', max_players: 4, current_participant_count: 1 },
        participants: [
          { id: 'p1', name: 'Human', participant_type: 'human', is_owner: true }
        ],
        is_owner: true
      })

      const wrapper = mount(AIAgentControls, {
        global: {
          plugins: [pinia]
        }
      })

      expect(wrapper.text()).toContain('暂无AI玩家')
    })
  })
})
