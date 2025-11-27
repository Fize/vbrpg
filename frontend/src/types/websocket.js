/**
 * @fileoverview WebSocket event payload type definitions
 * @module types/websocket
 */

/**
 * Player joined lobby event
 * @typedef {Object} LobbyJoinedPayload
 * @property {string} room_code - Room code joined
 * @property {number} player_id - Player ID
 * @property {string} timestamp - Event timestamp
 */

/**
 * Player left lobby event
 * @typedef {Object} LobbyLeftPayload
 * @property {string} room_code - Room code left
 * @property {number} player_id - Player ID
 * @property {string} timestamp - Event timestamp
 */

/**
 * Game started event
 * @typedef {Object} GameStartedPayload
 * @property {string} room_code - Room code
 * @property {Object} game_state - Initial game state
 * @property {string} timestamp - Event timestamp
 */

/**
 * Game state update event
 * @typedef {Object} GameStateUpdatePayload
 * @property {string} room_code - Room code
 * @property {Object} game_state - Updated game state
 * @property {string} update_type - Type of update: "action" | "turn" | "status"
 * @property {string} timestamp - Event timestamp
 */

/**
 * Turn changed event
 * @typedef {Object} TurnChangedPayload
 * @property {string} room_code - Room code
 * @property {number} current_player_id - Player whose turn it is now
 * @property {number} turn_time_limit - Turn time limit in seconds
 * @property {string} timestamp - Event timestamp
 */

/**
 * Game action event (submitted by player)
 * @typedef {Object} GameActionPayload
 * @property {string} room_code - Room code
 * @property {number} player_id - Player who performed action
 * @property {import('./game').GameAction} action - Action details
 * @property {string} timestamp - Event timestamp
 */

/**
 * AI thinking event
 * @typedef {Object} AIThinkingPayload
 * @property {string} room_code - Room code
 * @property {number} ai_player_id - AI player ID
 * @property {string} status - Thinking status: "started" | "in_progress"
 * @property {string} timestamp - Event timestamp
 */

/**
 * AI action event
 * @typedef {Object} AIActionPayload
 * @property {string} room_code - Room code
 * @property {number} ai_player_id - AI player ID
 * @property {import('./game').GameAction} action - Action performed
 * @property {string} reasoning - AI reasoning (optional)
 * @property {string} timestamp - Event timestamp
 */

/**
 * AI timeout event
 * @typedef {Object} AITimeoutPayload
 * @property {string} room_code - Room code
 * @property {number} ai_player_id - AI player ID
 * @property {string} fallback_action - Default action taken
 * @property {string} timestamp - Event timestamp
 */

/**
 * Game ended event
 * @typedef {Object} GameEndedPayload
 * @property {string} room_code - Room code
 * @property {number|null} winner_id - Winner player ID (null if no winner)
 * @property {Object} final_state - Final game state
 * @property {Object} statistics - Game statistics
 * @property {string} timestamp - Event timestamp
 */

/**
 * Reconnect event
 * @typedef {Object} ReconnectPayload
 * @property {string} room_code - Room code
 * @property {number} player_id - Reconnecting player ID
 * @property {Object} full_game_state - Complete game state snapshot
 * @property {string} timestamp - Event timestamp
 */

/**
 * Error event
 * @typedef {Object} ErrorPayload
 * @property {string} error_code - Error code
 * @property {string} message - Error message
 * @property {Object|null} [details] - Additional error details
 * @property {string} timestamp - Event timestamp
 */

export {}
