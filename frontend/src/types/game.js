/**
 * @fileoverview Game action and crime scene entity type definitions
 * @module types/game
 */

/**
 * Game action submitted by player
 * @typedef {Object} GameAction
 * @property {string} action_type - Action type: "investigate" | "interrogate" | "accuse" | "pass" | "move"
 * @property {string|null} [target] - Target location or character ID
 * @property {Object|null} [parameters] - Action-specific parameters
 * @property {string} timestamp - Action timestamp (ISO 8601)
 * @property {number} player_id - Player who performed the action
 */

/**
 * Turn timer configuration
 * @typedef {Object} TurnTimer
 * @property {number} remaining_seconds - Remaining time in current turn
 * @property {number} total_seconds - Total time limit per turn (30-300)
 * @property {number} warning_threshold_1 - Yellow warning threshold (default: 30s)
 * @property {number} warning_threshold_2 - Red warning threshold (default: 10s)
 */

/**
 * Clue item discovered during investigation
 * @typedef {Object} ClueItem
 * @property {number} id - Unique clue ID
 * @property {string} description - Clue description text
 * @property {string} location - Location where clue was found
 * @property {('low'|'medium'|'high')} importance - Importance level
 * @property {string} discovered_at - Discovery timestamp (ISO 8601)
 * @property {number} discovered_by - Player ID who found the clue
 */

/**
 * Suspect character in crime scene game
 * @typedef {Object} Suspect
 * @property {number} id - Unique suspect ID
 * @property {string} name - Suspect full name
 * @property {string} description - Character description
 * @property {string[]} relationships - Related character IDs
 * @property {string[]} available_topics - Topics that can be asked about
 */

/**
 * Investigation record for a player
 * @typedef {Object} Investigation
 * @property {number} player_id - Player conducting investigation
 * @property {string[]} investigated_locations - List of location IDs already investigated
 * @property {number[]} discovered_clues - List of clue IDs found
 * @property {Object[]} interrogation_history - History of interrogations
 * @property {number} interrogation_history[].suspect_id - Suspect interrogated
 * @property {string} interrogation_history[].topic - Topic discussed
 * @property {string} interrogation_history[].answer - Suspect's response
 * @property {string} interrogation_history[].timestamp - Interrogation timestamp
 * @property {string|null} reasoning_notes - Player's reasoning notes
 */

/**
 * Accusation made by player
 * @typedef {Object} Accusation
 * @property {number} suspect_id - Accused suspect ID
 * @property {number[]} evidence_clues - List of clue IDs used as evidence
 * @property {string} reasoning - Player's accusation reasoning
 * @property {boolean|null} is_correct - Whether accusation was correct (null until validated)
 * @property {string} submitted_at - Submission timestamp (ISO 8601)
 */

export {}
