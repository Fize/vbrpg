/**
 * Unit tests for JoinRoomForm component
 * Tests room code validation, API integration, and error handling
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import JoinRoomForm from '@/components/lobby/JoinRoomForm.vue'
import { roomsApi } from '@/services/api'

// Mock the API service
vi.mock('@/services/api', () => ({
  roomsApi: {
    joinRoom: vi.fn()
  }
}))

// Mock vue-router
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockPush
  })
}))

describe('JoinRoomForm', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('Form Validation', () => {
    it('validates 6-character room code format', async () => {
      const wrapper = mount(JoinRoomForm)
      
      // Find room code input
      const input = wrapper.find('input[type="text"]')
      
      // Test too short
      await input.setValue('ABC12')
      expect(wrapper.vm.isValidCode).toBe(false)
      
      // Test too long
      await input.setValue('ABC1234')
      expect(wrapper.vm.isValidCode).toBe(false)
      
      // Test valid 6-char code
      await input.setValue('ABC123')
      expect(wrapper.vm.isValidCode).toBe(true)
    })

    it('converts room code to uppercase automatically', async () => {
      const wrapper = mount(JoinRoomForm)
      const input = wrapper.find('input[type="text"]')
      
      await input.setValue('abc123')
      expect(wrapper.vm.roomCode).toBe('ABC123')
    })

    it('only allows alphanumeric characters', async () => {
      const wrapper = mount(JoinRoomForm)
      const input = wrapper.find('input[type="text"]')
      
      await input.setValue('AB-123')
      expect(wrapper.vm.roomCode).not.toContain('-')
      
      await input.setValue('AB@123')
      expect(wrapper.vm.roomCode).not.toContain('@')
    })

    it('disables submit button when code is invalid', async () => {
      const wrapper = mount(JoinRoomForm)
      const input = wrapper.find('input[type="text"]')
      const button = wrapper.find('button[type="submit"]')
      
      // Empty code
      expect(button.attributes('disabled')).toBeDefined()
      
      // Invalid length
      await input.setValue('ABC')
      expect(button.attributes('disabled')).toBeDefined()
      
      // Valid code
      await input.setValue('ABC123')
      expect(button.attributes('disabled')).toBeUndefined()
    })
  })

  describe('API Integration', () => {
    it('calls API with room code on submit', async () => {
      roomsApi.joinRoom.mockResolvedValue({
        room: {
          code: 'ABC123',
          game_type: 'crime-scene',
          status: 'Waiting',
          current_participant_count: 2,
          max_players: 4
        },
        participants: [],
        is_owner: false
      })

      const wrapper = mount(JoinRoomForm)
      const input = wrapper.find('input[type="text"]')
      
      await input.setValue('ABC123')
      await wrapper.find('form').trigger('submit.prevent')
      
      expect(roomsApi.joinRoom).toHaveBeenCalledWith('ABC123')
    })

    it('emits join-success event with room data on successful join', async () => {
      const roomData = {
        room: {
          code: 'ABC123',
          game_type: 'crime-scene',
          status: 'Waiting'
        },
        participants: [],
        is_owner: false
      }
      
      roomsApi.joinRoom.mockResolvedValue(roomData)

      const wrapper = mount(JoinRoomForm)
      const input = wrapper.find('input[type="text"]')
      
      await input.setValue('ABC123')
      await wrapper.find('form').trigger('submit.prevent')
      
      // Wait for promise to resolve
      await wrapper.vm.$nextTick()
      await wrapper.vm.$nextTick()
      
      expect(wrapper.emitted('join-success')).toBeTruthy()
      expect(wrapper.emitted('join-success')[0][0]).toEqual(roomData)
    })

    it('navigates to lobby view on successful join', async () => {
      roomsApi.joinRoom.mockResolvedValue({
        room: { code: 'ABC123' },
        participants: [],
        is_owner: false
      })

      const wrapper = mount(JoinRoomForm)
      const input = wrapper.find('input[type="text"]')
      
      await input.setValue('ABC123')
      await wrapper.find('form').trigger('submit.prevent')
      
      await wrapper.vm.$nextTick()
      await wrapper.vm.$nextTick()
      
      expect(mockPush).toHaveBeenCalledWith({
        name: 'lobby',
        params: { code: 'ABC123' }
      })
    })
  })

  describe('Error Handling', () => {
    it('displays error message for non-existent room (404)', async () => {
      roomsApi.joinRoom.mockRejectedValue({
        response: {
          status: 404,
          data: { detail: 'Room not found' }
        }
      })

      const wrapper = mount(JoinRoomForm)
      const input = wrapper.find('input[type="text"]')
      
      await input.setValue('NOROOM')
      await wrapper.find('form').trigger('submit.prevent')
      
      await wrapper.vm.$nextTick()
      await wrapper.vm.$nextTick()
      
      expect(wrapper.text()).toContain('房间不存在')
    })

    it('displays error message for full room (409)', async () => {
      roomsApi.joinRoom.mockRejectedValue({
        response: {
          status: 409,
          data: { detail: 'Room is full' }
        }
      })

      const wrapper = mount(JoinRoomForm)
      const input = wrapper.find('input[type="text"]')
      
      await input.setValue('FULL01')
      await wrapper.find('form').trigger('submit.prevent')
      
      await wrapper.vm.$nextTick()
      await wrapper.vm.$nextTick()
      
      expect(wrapper.text()).toContain('房间已满')
    })

    it('displays error message for game in progress (409)', async () => {
      roomsApi.joinRoom.mockRejectedValue({
        response: {
          status: 409,
          data: { detail: 'Game already started' }
        }
      })

      const wrapper = mount(JoinRoomForm)
      const input = wrapper.find('input[type="text"]')
      
      await input.setValue('START1')
      await wrapper.find('form').trigger('submit.prevent')
      
      await wrapper.vm.$nextTick()
      await wrapper.vm.$nextTick()
      
      expect(wrapper.text()).toContain('游戏已开始')
    })

    it('clears error message when user edits room code', async () => {
      roomsApi.joinRoom.mockRejectedValue({
        response: {
          status: 404,
          data: { detail: 'Room not found' }
        }
      })

      const wrapper = mount(JoinRoomForm)
      const input = wrapper.find('input[type="text"]')
      
      // Trigger error
      await input.setValue('NOROOM')
      await wrapper.find('form').trigger('submit.prevent')
      await wrapper.vm.$nextTick()
      await wrapper.vm.$nextTick()
      
      expect(wrapper.vm.errorMessage).toBeTruthy()
      
      // Edit code
      await input.setValue('NEWCODE')
      expect(wrapper.vm.errorMessage).toBe('')
    })

    it('shows loading state during API call', async () => {
      let resolvePromise
      const promise = new Promise(resolve => { resolvePromise = resolve })
      roomsApi.joinRoom.mockReturnValue(promise)

      const wrapper = mount(JoinRoomForm)
      const input = wrapper.find('input[type="text"]')
      const button = wrapper.find('button[type="submit"]')
      
      await input.setValue('ABC123')
      await wrapper.find('form').trigger('submit.prevent')
      
      // Give Vue time to update
      await wrapper.vm.$nextTick()
      
      // Should be loading
      expect(wrapper.vm.isLoading).toBe(true)
      expect(button.attributes('disabled')).toBeDefined()
      expect(button.text()).toContain('加入中')
      
      // Resolve promise
      if (resolvePromise) {
        resolvePromise({ room: { code: 'ABC123' }, participants: [], is_owner: false })
      }
      await wrapper.vm.$nextTick()
      await wrapper.vm.$nextTick()
      
      // Wait a bit for the promise to fully resolve
      await new Promise(resolve => setTimeout(resolve, 50))
      
      // Should not be loading
      expect(wrapper.vm.isLoading).toBe(false)
      expect(button.text()).not.toContain('加入中')
    })
  })

  describe('UI/UX', () => {
    it('displays placeholder text in input field', () => {
      const wrapper = mount(JoinRoomForm)
      const input = wrapper.find('input[type="text"]')
      
      expect(input.attributes('placeholder')).toBe('请输入房间代码')
    })

    it('shows hint text about code format', () => {
      const wrapper = mount(JoinRoomForm)
      expect(wrapper.text()).toContain('6位字母数字组合')
    })

    it('autofocuses on input field when mounted', async () => {
      const wrapper = mount(JoinRoomForm, {
        attachTo: document.body
      })
      
      await wrapper.vm.$nextTick()
      
      const input = wrapper.find('input[type="text"]')
      expect(document.activeElement).toBe(input.element)
      
      wrapper.unmount()
    })
  })
})
