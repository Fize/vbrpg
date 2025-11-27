/**
 * @fileoverview Room filtering type definitions
 * @module types/room
 */

/**
 * Query parameters for room list filtering
 * @typedef {Object} RoomFilter
 * @property {('Waiting'|'In Progress'|'Completed')|null} [status] - Room status filter
 * @property {string|null} [game_type] - Game type filter (e.g., "Crime Scene")
 * @property {number} [limit=20] - Max results (1-100)
 * @property {number} [offset=0] - Pagination offset (>= 0)
 */

/**
 * Game room information
 * @typedef {Object} GameRoom
 * @property {string} room_code - Unique room identifier (6 chars uppercase)
 * @property {string} status - Room status: "Waiting" | "In Progress" | "Completed"
 * @property {string} game_type - Game type name
 * @property {number} max_players - Maximum player capacity
 * @property {number} current_players - Current player count
 * @property {string} created_at - Creation timestamp (ISO 8601)
 * @property {number} creator_id - Room creator player ID
 */

export {}
