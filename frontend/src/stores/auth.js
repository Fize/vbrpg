import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  // State
  const currentPlayer = ref(null)
  const isAuthenticated = ref(false)
  const isLoading = ref(false)

  // Getters
  const isGuest = computed(() => {
    return currentPlayer.value?.is_guest === true
  })

  const username = computed(() => {
    return currentPlayer.value?.username || 'Guest'
  })

  const playerId = computed(() => {
    return currentPlayer.value?.id
  })

  // Actions
  function setPlayer(player) {
    currentPlayer.value = player
    isAuthenticated.value = !!player
  }

  function clearPlayer() {
    currentPlayer.value = null
    isAuthenticated.value = false
  }

  function updateUsername(newUsername) {
    if (currentPlayer.value) {
      currentPlayer.value.username = newUsername
      currentPlayer.value.is_guest = false
    }
  }

  function setLoading(loading) {
    isLoading.value = loading
  }

  return {
    // State
    currentPlayer,
    isAuthenticated,
    isLoading,

    // Getters
    isGuest,
    username,
    playerId,

    // Actions
    setPlayer,
    clearPlayer,
    updateUsername,
    setLoading
  }
})
