import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
apiClient.interceptors.request.use(
  config => {
    // Add any auth tokens here if needed
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response) {
      // Server responded with error
      const errorData = error.response.data
      console.error('API Error:', errorData)
    } else if (error.request) {
      // Request made but no response
      console.error('Network Error:', error.message)
    } else {
      // Error setting up request
      console.error('Request Error:', error.message)
    }
    return Promise.reject(error)
  }
)

// Room API methods
export const roomsApi = {
  /**
   * Create a new game room
   * @param {Object} roomData - Room configuration
   * @param {string} roomData.game_type_slug - Game type slug (e.g., 'crime-scene')
   * @param {number} roomData.max_players - Maximum number of players
   * @param {number} roomData.min_players - Minimum number of players
   * @returns {Promise<Object>} Created room data
   */
  async createRoom(roomData) {
    const response = await apiClient.post('/rooms', roomData)
    return response.data
  },

  /**
   * Get list of game rooms
   * @param {Object} filters - Optional filters
   * @param {string} filters.status - Filter by status ('Waiting', 'In Progress', 'Completed')
   * @param {string} filters.gameType - Filter by game type slug
   * @param {number} filters.limit - Maximum number of results
   * @returns {Promise<Object>} List of rooms
   */
  async getRooms(filters = {}) {
    const params = {}
    if (filters.status) params.status = filters.status
    if (filters.gameType) params.gameType = filters.gameType
    if (filters.limit) params.limit = filters.limit
    
    const response = await apiClient.get('/rooms', { params })
    return response.data
  },

  /**
   * Get room details by code
   * @param {string} roomCode - 8-character room code
   * @returns {Promise<Object>} Room details
   */
  async getRoom(roomCode) {
    const response = await apiClient.get(`/rooms/${roomCode}`)
    return response.data
  },

  /**
   * Join a game room
   * @param {string} roomCode - Room code to join
   * @returns {Promise<Object>} Updated room data
   */
  async joinRoom(roomCode) {
    const response = await apiClient.post(`/rooms/${roomCode}/join`)
    return response.data
  },

  /**
   * Leave a game room
   * @param {string} roomCode - Room code to leave
   * @returns {Promise<Object>} Success message
   */
  async leaveRoom(roomCode) {
    const response = await apiClient.post(`/rooms/${roomCode}/leave`)
    return response.data
  },

  /**
   * Start a game (host only)
   * @param {string} roomCode - Room code to start
   * @returns {Promise<Object>} Updated room data with game started
   */
  async startGame(roomCode) {
    const response = await apiClient.post(`/rooms/${roomCode}/start`)
    return response.data
  }
}

// Games API methods
export const gamesApi = {
  /**
   * Get list of all game types
   * @param {boolean} availableOnly - If true, only return available games
   * @returns {Promise<Array>} List of game types
   */
  async getGames(availableOnly = false) {
    const params = availableOnly ? { available_only: true } : {}
    const response = await apiClient.get('/games', { params })
    return response.data
  },

  /**
   * Get detailed information about a specific game
   * @param {string} slug - Game slug identifier
   * @returns {Promise<Object>} Game details
   */
  async getGameDetails(slug) {
    const response = await apiClient.get(`/games/${slug}`)
    return response.data
  }
}

// Players API methods
export const playersApi = {
  /**
   * Create a new guest account
   * @returns {Promise<Object>} Created guest player
   */
  async createGuest() {
    const response = await apiClient.post('/players/guest')
    return response.data
  },

  /**
   * Get current player profile
   * @returns {Promise<Object>} Current player information
   */
  async getCurrentPlayer() {
    const response = await apiClient.get('/players/me')
    return response.data
  },

  /**
   * Upgrade guest account to permanent
   * @param {string} username - Desired permanent username
   * @returns {Promise<Object>} Updated player information
   */
  async upgradeAccount(username) {
    const response = await apiClient.post('/players/me/upgrade', { username })
    return response.data
  },

  /**
   * Get player statistics
   * @returns {Promise<Object>} Player statistics
   */
  async getStats() {
    const response = await apiClient.get('/players/me/stats')
    return response.data
  }
}

export default apiClient

