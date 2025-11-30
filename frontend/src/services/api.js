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

  // 单人模式移除了 joinRoom 和 leaveRoom 接口
  // 用户通过 WebSocket 连接房间，不需要 REST API 加入/离开

  /**
   * Start a game (host only)
   * @param {string} roomCode - Room code to start
   * @returns {Promise<Object>} Updated room data with game started
   */
  async startGame(roomCode) {
    const response = await apiClient.post(`/rooms/${roomCode}/start`)
    return response.data
  },

  /**
   * Add an AI agent to the room (owner only)
   * @param {string} roomCode - Room code
   * @returns {Promise<Object>} Created AI agent data
   */
  async addAIAgent(roomCode) {
    const response = await apiClient.post(`/rooms/${roomCode}/ai-agents`)
    return response.data
  },

  /**
   * Remove an AI agent from the room (owner only)
   * @param {string} roomCode - Room code
   * @param {string} agentId - AI agent ID to remove
   * @returns {Promise<void>}
   */
  async removeAIAgent(roomCode, agentId) {
    await apiClient.delete(`/rooms/${roomCode}/ai-agents/${agentId}`)
  },

  /**
   * Select a role in the room
   * @param {string} roomCode - Room code
   * @param {string|null} roleId - Role ID to select, null for random
   * @param {boolean} isSpectator - Whether to join as spectator
   * @returns {Promise<Object>} Updated room data
   */
  async selectRole(roomCode, roleId, isSpectator = false) {
    const response = await apiClient.post(`/rooms/${roomCode}/select-role`, {
      role_id: roleId,
      is_spectator: isSpectator
    })
    return response.data
  },

  /**
   * Pause a game
   * @param {string} roomCode - Room code
   * @returns {Promise<Object>} Game control response
   */
  async pauseGame(roomCode) {
    const response = await apiClient.post(`/rooms/${roomCode}/pause`)
    return response.data
  },

  /**
   * Resume a paused game
   * @param {string} roomCode - Room code
   * @returns {Promise<Object>} Game control response
   */
  async resumeGame(roomCode) {
    const response = await apiClient.post(`/rooms/${roomCode}/resume`)
    return response.data
  },

  /**
   * Stop a game
   * @param {string} roomCode - Room code
   * @returns {Promise<Object>} Game control response
   */
  async stopGame(roomCode) {
    const response = await apiClient.post(`/rooms/${roomCode}/stop`)
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
  },

  /**
   * 狼人杀快速开始 - 直接创建房间并开始游戏
   * @param {Object} options - 游戏选项
   * @param {string} options.player_id - 玩家ID
   * @param {string|null} options.preferred_role - 首选角色（null 表示随机分配）
   * @returns {Promise<Object>} 返回房间信息和游戏状态
   */
  async quickStartWerewolf(options) {
    const response = await apiClient.post('/werewolf/quick-start', options)
    return response.data
  },

  /**
   * 狼人杀游戏行动
   * @param {string} roomCode - 房间码
   * @param {Object} action - 行动信息
   * @param {string} action.player_id - 玩家ID
   * @param {string} action.action_type - 行动类型 ('kill' | 'check' | 'save' | 'poison' | 'shoot' | 'vote')
   * @param {number|null} action.target_seat - 目标座位号
   * @returns {Promise<Object>} 返回操作结果
   */
  async werewolfAction(roomCode, action) {
    const response = await apiClient.post(`/werewolf/rooms/${roomCode}/action`, action)
    return response.data
  },

  /**
   * 获取狼人杀游戏状态
   * @param {string} roomCode - 房间码
   * @param {string} playerId - 玩家ID
   * @returns {Promise<Object>} 游戏状态
   */
  async getWerewolfState(roomCode, playerId) {
    const response = await apiClient.get(`/werewolf/rooms/${roomCode}/state`, {
      params: { player_id: playerId }
    })
    return response.data
  },

  /**
   * 获取玩家在狼人杀游戏中的角色
   * @param {string} roomCode - 房间码
   * @param {string} playerId - 玩家ID
   * @returns {Promise<Object>} 角色信息
   */
  async getWerewolfRole(roomCode, playerId) {
    const response = await apiClient.get(`/werewolf/rooms/${roomCode}/role`, {
      params: { player_id: playerId }
    })
    return response.data
  }
}

// Roles API methods
export const rolesApi = {
  /**
   * Get roles for a specific game type
   * @param {string} gameTypeSlug - Game type slug (e.g., 'werewolf')
   * @returns {Promise<Object>} Roles list response
   */
  async getRoles(gameTypeSlug) {
    const response = await apiClient.get(`/games/${gameTypeSlug}/roles`)
    return response.data
  }
}

// 单人模式下移除了 playersApi
// - 无需 /api/v1/players/guest (游客创建)
// - 无需 /api/v1/players/me (获取当前玩家)
// 所有玩家都是 AI，用户只是观战

export default apiClient

