/**
 * @fileoverview Player entity type definitions
 * @module types/player
 */

/**
 * Full player account with authentication credentials and game statistics
 * @typedef {Object} RegisteredPlayer
 * @property {number} id - Unique player ID (backend-generated)
 * @property {string} username - Display name (3-20 chars, alphanumeric/underscore/中文)
 * @property {string} email - Unique email address (RFC 5322 format)
 * @property {boolean} is_guest - Guest flag (always false for registered players)
 * @property {string} created_at - Registration timestamp (ISO 8601)
 * @property {number} total_games - Total games participated (>= 0)
 * @property {number} total_wins - Total games won (>= 0)
 * @property {number} win_rate - Win percentage (0.0 - 1.0)
 */

/**
 * Sanitized player profile visible to other users (excludes private data)
 * @typedef {Object} PublicProfile
 * @property {number} id - Player ID
 * @property {string} username - Display name
 * @property {string} created_at - Registration timestamp (ISO 8601)
 * @property {number} total_games - Total games participated
 * @property {number} total_wins - Total games won
 * @property {number} win_rate - Win percentage (0.0 - 1.0)
 */

export {}
