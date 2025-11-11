/**
 * Integration tests for Pinia lobby store
 * Tests state management for lobby/room functionality
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useLobbyStore } from '@/stores/lobby'

describe('Lobby Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('Initial State', () => {
    it('starts with null currentRoom', () => {
      const store = useLobbyStore()
      expect(store.currentRoom).toBeNull()
    })

    it('starts with empty participants array', () => {
      const store = useLobbyStore()
      expect(store.participants).toEqual([])
    })

    it('starts with isOwner as false', () => {
      const store = useLobbyStore()
      expect(store.isOwner).toBe(false)
    })
  })

  describe('joinRoom Action', () => {
    it('updates currentRoom with room data', () => {
      const store = useLobbyStore()
      const roomData = {
        room: {
          code: 'ABC123',
          game_type: 'crime-scene',
          status: 'Waiting',
          max_players: 4,
          current_participant_count: 2
        },
        participants: [
          { id: 'player-1', name: 'Alice', participant_type: 'human', is_owner: true },
          { id: 'player-2', name: 'Bob', participant_type: 'human', is_owner: false }
        ],
        is_owner: false
      }

      store.joinRoom(roomData)

      expect(store.currentRoom).toEqual(roomData.room)
    })

    it('updates participants list', () => {
      const store = useLobbyStore()
      const roomData = {
        room: { code: 'ABC123' },
        participants: [
          { id: 'player-1', name: 'Alice', participant_type: 'human', is_owner: true },
          { id: 'player-2', name: 'Bob', participant_type: 'human', is_owner: false }
        ],
        is_owner: false
      }

      store.joinRoom(roomData)

      expect(store.participants).toHaveLength(2)
      expect(store.participants[0].name).toBe('Alice')
      expect(store.participants[1].name).toBe('Bob')
    })

    it('sets isOwner flag correctly', () => {
      const store = useLobbyStore()
      
      // Test as non-owner
      store.joinRoom({
        room: { code: 'ABC123' },
        participants: [],
        is_owner: false
      })
      expect(store.isOwner).toBe(false)

      // Test as owner
      store.joinRoom({
        room: { code: 'DEF456' },
        participants: [],
        is_owner: true
      })
      expect(store.isOwner).toBe(true)
    })
  })

  describe('leaveRoom Action', () => {
    it('clears currentRoom state', () => {
      const store = useLobbyStore()
      
      // Set up initial state
      store.joinRoom({
        room: { code: 'ABC123' },
        participants: [],
        is_owner: false
      })

      // Leave room
      store.leaveRoom()

      expect(store.currentRoom).toBeNull()
    })

    it('clears participants list', () => {
      const store = useLobbyStore()
      
      // Set up initial state
      store.joinRoom({
        room: { code: 'ABC123' },
        participants: [
          { id: 'player-1', name: 'Alice' }
        ],
        is_owner: false
      })

      // Leave room
      store.leaveRoom()

      expect(store.participants).toEqual([])
    })

    it('resets isOwner flag', () => {
      const store = useLobbyStore()
      
      // Set up as owner
      store.joinRoom({
        room: { code: 'ABC123' },
        participants: [],
        is_owner: true
      })

      // Leave room
      store.leaveRoom()

      expect(store.isOwner).toBe(false)
    })
  })

  describe('updateParticipants Action', () => {
    it('adds new participant to list', () => {
      const store = useLobbyStore()
      
      // Initial state with one participant
      store.joinRoom({
        room: { code: 'ABC123' },
        participants: [
          { id: 'player-1', name: 'Alice', participant_type: 'human' }
        ],
        is_owner: false
      })

      // Add new participant
      const newParticipant = { id: 'player-2', name: 'Bob', participant_type: 'human' }
      store.addParticipant(newParticipant)

      expect(store.participants).toHaveLength(2)
      expect(store.participants[1]).toEqual(newParticipant)
    })

    it('removes participant from list', () => {
      const store = useLobbyStore()
      
      // Initial state with two participants
      store.joinRoom({
        room: { code: 'ABC123' },
        participants: [
          { id: 'player-1', name: 'Alice' },
          { id: 'player-2', name: 'Bob' }
        ],
        is_owner: false
      })

      // Remove one participant
      store.removeParticipant('player-2')

      expect(store.participants).toHaveLength(1)
      expect(store.participants[0].id).toBe('player-1')
    })

    it('does not duplicate participants', () => {
      const store = useLobbyStore()
      
      store.joinRoom({
        room: { code: 'ABC123' },
        participants: [
          { id: 'player-1', name: 'Alice' }
        ],
        is_owner: false
      })

      // Try to add same participant
      store.addParticipant({ id: 'player-1', name: 'Alice' })

      expect(store.participants).toHaveLength(1)
    })
  })

  describe('transferOwnership Action', () => {
    it('updates owner flags correctly', () => {
      const store = useLobbyStore()
      
      // Initial state with owner
      store.joinRoom({
        room: { code: 'ABC123' },
        participants: [
          { id: 'player-1', name: 'Alice', is_owner: true },
          { id: 'player-2', name: 'Bob', is_owner: false }
        ],
        is_owner: true
      })

      // Transfer ownership to Bob
      store.transferOwnership('player-2')

      expect(store.participants[0].is_owner).toBe(false)
      expect(store.participants[1].is_owner).toBe(true)
    })

    it('updates isOwner flag for current player', () => {
      const store = useLobbyStore()
      const authStore = { playerId: 'player-1' }
      
      store.joinRoom({
        room: { code: 'ABC123' },
        participants: [
          { id: 'player-1', name: 'Alice', is_owner: true },
          { id: 'player-2', name: 'Bob', is_owner: false }
        ],
        is_owner: true
      })

      // Transfer ownership away from current player
      store.transferOwnership('player-2', 'player-1')

      expect(store.isOwner).toBe(false)
    })

    it('handles ownership transfer when current player becomes owner', () => {
      const store = useLobbyStore()
      
      store.joinRoom({
        room: { code: 'ABC123' },
        participants: [
          { id: 'player-1', name: 'Alice', is_owner: true },
          { id: 'player-2', name: 'Bob', is_owner: false }
        ],
        is_owner: false
      })

      // Current player (Bob) becomes owner
      store.transferOwnership('player-2', 'player-2')

      expect(store.isOwner).toBe(true)
    })
  })

  describe('Computed Getters', () => {
    it('participantCount returns correct count', () => {
      const store = useLobbyStore()
      
      store.joinRoom({
        room: { code: 'ABC123' },
        participants: [
          { id: 'player-1', name: 'Alice' },
          { id: 'player-2', name: 'Bob' },
          { id: 'ai-1', name: 'AI玩家1', participant_type: 'ai' }
        ],
        is_owner: false
      })

      expect(store.participantCount).toBe(3)
    })

    it('hasCapacity checks against max_players', () => {
      const store = useLobbyStore()
      
      store.joinRoom({
        room: { 
          code: 'ABC123',
          max_players: 4,
          current_participant_count: 3
        },
        participants: [
          { id: 'player-1', name: 'Alice' },
          { id: 'player-2', name: 'Bob' },
          { id: 'ai-1', name: 'AI玩家1' }
        ],
        is_owner: false
      })

      expect(store.hasCapacity).toBe(true)

      // Add one more to reach max
      store.addParticipant({ id: 'player-3', name: 'Charlie' })
      store.currentRoom.current_participant_count = 4

      expect(store.hasCapacity).toBe(false)
    })

    it('sortedParticipants orders by join_timestamp', () => {
      const store = useLobbyStore()
      
      store.joinRoom({
        room: { code: 'ABC123' },
        participants: [
          { id: 'player-3', name: 'Charlie', join_timestamp: '2025-11-09T10:32:00Z' },
          { id: 'player-1', name: 'Alice', join_timestamp: '2025-11-09T10:30:00Z' },
          { id: 'player-2', name: 'Bob', join_timestamp: '2025-11-09T10:31:00Z' }
        ],
        is_owner: false
      })

      const sorted = store.sortedParticipants
      expect(sorted[0].name).toBe('Alice')  // Earliest
      expect(sorted[1].name).toBe('Bob')
      expect(sorted[2].name).toBe('Charlie')  // Latest
    })

    it('aiAgents filters participants by type', () => {
      const store = useLobbyStore()
      
      store.joinRoom({
        room: { code: 'ABC123' },
        participants: [
          { id: 'player-1', name: 'Alice', participant_type: 'human' },
          { id: 'ai-1', name: 'AI玩家1', participant_type: 'ai' },
          { id: 'player-2', name: 'Bob', participant_type: 'human' },
          { id: 'ai-2', name: 'AI玩家2', participant_type: 'ai' }
        ],
        is_owner: false
      })

      const aiAgents = store.aiAgents
      expect(aiAgents).toHaveLength(2)
      expect(aiAgents[0].name).toBe('AI玩家1')
      expect(aiAgents[1].name).toBe('AI玩家2')
    })
  })
})
