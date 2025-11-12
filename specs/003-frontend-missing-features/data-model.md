# Data Model: Frontend Missing Features Implementation

**Generated**: 2025-11-12  
**Branch**: `003-frontend-missing-features`  
**Context**: Frontend data structures for user registration, profiles, rooms, and crime scene game state

## Overview

This document defines the client-side data models for 9 key entities from the feature specification. These models represent the structure of data managed in Pinia stores and passed between components via props. All models align with backend API contracts.

**Note**: Backend maintains authoritative state. Frontend models are **reactive views** of server data, not independent data sources.

---

## Core Entities

### 1. RegisteredPlayer

**Purpose**: Full player account with authentication credentials and game statistics

**Source**: REST API `POST /api/v1/players/register`, `GET /api/v1/players/{id}`

**Fields**:
| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `id` | `number` | ✓ | > 0 | Unique player ID (backend-generated) |
| `username` | `string` | ✓ | 3-20 chars, alphanumeric/underscore/中文 | Display name |
| `email` | `string` | ✓ | Valid email format | Unique email address |
| `is_guest` | `boolean` | ✓ | - | Guest flag (always `false` for registered) |
| `created_at` | `string` | ✓ | ISO 8601 | Registration timestamp |
| `total_games` | `number` | ✓ | >= 0 | Total games participated |
| `total_wins` | `number` | ✓ | >= 0 | Total games won |
| `win_rate` | `number` | ✓ | 0.0 - 1.0 | Win percentage (computed: wins/games) |

**Relationships**:
- Extends `GuestPlayer` (converts via upgrade API)
- Has many `GameSession` (participation history)
- Has one `PublicProfile` (publicly visible subset)

**State Transitions**:
```
GuestPlayer → [/api/v1/players/register] → RegisteredPlayer
```

**Validation Rules** (from FR-002, FR-003, FR-004):
- Username: 3-20 characters, alphanumeric + underscore + 中文
- Email: RFC 5322 format, unique in database
- Password: Minimum 8 characters (validated on backend, not stored in frontend model)
- `win_rate`: Recomputed on every game completion

**Usage in Frontend**:
- Stored in `authStore.currentPlayer` (Pinia)
- Displayed in `ProfileView.vue` (full details)
- Passed to `ProfileEditor.vue` for edit operations

---

### 2. PublicProfile

**Purpose**: Sanitized player profile visible to other users (excludes private data)

**Source**: REST API `GET /api/v1/players/{id}/profile`

**Fields**:
| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `id` | `number` | ✓ | > 0 | Player ID |
| `username` | `string` | ✓ | - | Display name |
| `created_at` | `string` | ✓ | ISO 8601 | Registration timestamp |
| `total_games` | `number` | ✓ | >= 0 | Total games participated |
| `total_wins` | `number` | ✓ | >= 0 | Total games won |
| `win_rate` | `number` | ✓ | 0.0 - 1.0 | Win percentage |

**Relationships**:
- Derived from `RegisteredPlayer` (subset without `email`)

**Privacy Rules** (from FR-007):
- **Excluded Fields**: `email`, `password_hash`, internal IDs
- **Included Fields**: Public stats and timestamps

**Usage in Frontend**:
- Displayed in `ProfileCard.vue` component
- Shown in player tooltips on game board
- Cached in `profileStore` for repeated access

---

### 3. RoomFilter

**Purpose**: Query parameters for room list filtering

**Source**: Local UI state (not from API)

**Fields**:
| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `status` | `string \| null` | ✗ | "Waiting" \| "In Progress" \| "Completed" | Room status filter |
| `game_type` | `string \| null` | ✗ | "Crime Scene" \| etc. | Game type filter |
| `limit` | `number` | ✗ | 1-100 | Max results (default: 20) |
| `offset` | `number` | ✗ | >= 0 | Pagination offset (default: 0) |

**Relationships**:
- Used by `GET /api/v1/rooms?status={status}&game_type={game_type}`
- Stored in `roomStore.filters` (Pinia)

**Validation Rules** (from FR-009, FR-010, FR-011):
- Multiple filters applied via AND logic
- Empty filters = no filtering (show all)
- Invalid filter values ignored by backend

**Usage in Frontend**:
- Bound to `RoomFilter.vue` component inputs
- Passed to `roomsApi.getRooms(filters)` service method
- Reset via "Clear Filters" button (FR-012)

---

### 4. GameAction

**Purpose**: Player action submission during game turn

**Source**: Emitted via WebSocket `game_action` event

**Fields**:
| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `action_type` | `string` | ✓ | "investigate" \| "interrogate" \| "accuse" \| "pass" | Action category |
| `target` | `string \| null` | ✗ | - | Target location/suspect ID |
| `parameters` | `object` | ✗ | - | Action-specific data (e.g., evidence for accusation) |
| `timestamp` | `number` | ✓ | Unix epoch ms | Client submission time |

**Relationships**:
- Triggers `game_state_update` event from backend
- Stored in `Investigation.action_history` (game record)

**Action Type Parameters**:
| Action Type | Required `target` | Required `parameters` | Example |
|-------------|-------------------|----------------------|---------|
| `investigate` | Location ID | - | `{ action_type: "investigate", target: "library" }` |
| `interrogate` | Suspect ID | `{ question: "Where were you?" }` | `{ action_type: "interrogate", target: "suspect_1", parameters: { question: "..." } }` |
| `accuse` | Suspect ID | `{ evidence: ["clue_1", "clue_2"] }` | `{ action_type: "accuse", target: "suspect_2", parameters: { evidence: [...] } }` |
| `pass` | - | - | `{ action_type: "pass" }` |

**Validation Rules** (from FR-021):
- Cannot investigate same location twice
- Cannot interrogate without valid question
- Cannot accuse without minimum 2 evidence items
- Backend performs authoritative validation

**Usage in Frontend**:
- Emitted from `ActionPanel.vue` component
- Validated in `useGameActions()` composable before emit
- Optimistically updates UI (rolled back on server rejection)

---

### 5. TurnTimer

**Purpose**: Countdown timer for player turn timeout

**Source**: Managed in frontend composable, synced with backend `turn_changed` event

**Fields**:
| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `total_seconds` | `number` | ✓ | 30-300 | Total turn duration (from room config) |
| `remaining_seconds` | `number` | ✓ | 0 - `total_seconds` | Time left in current turn |
| `warning_thresholds` | `number[]` | ✓ | [30, 10] | Seconds at which to show warnings |
| `is_active` | `boolean` | ✓ | - | Timer running state |
| `current_player_id` | `number` | ✓ | > 0 | Player whose turn it is |

**Relationships**:
- Synced with `game_state.current_turn` from backend
- Resets on `turn_changed` WebSocket event

**State Transitions**:
```
Inactive → [turn_changed event] → Active → [timeout] → Inactive
              ↓                       ↓
         Reset to total_seconds   Decrement every 1s
```

**Validation Rules** (from FR-025, FR-026, FR-027):
- Show yellow warning at 30s remaining
- Show red flashing + sound at 10s remaining
- Auto-submit `pass` action at 0s

**Usage in Frontend**:
- Managed by `useTurnTimer()` composable
- Displayed in `TurnTimer.vue` component
- Triggers `ActionPanel` disable when expired

---

### 6. ClueItem

**Purpose**: Evidence discovered during game investigation

**Source**: Received in `game_state_update` event after `investigate` action

**Fields**:
| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `id` | `string` | ✓ | Unique | Clue identifier (e.g., "clue_bloodstain") |
| `description` | `string` | ✓ | - | Clue text (e.g., "血迹在地板上") |
| `location` | `string` | ✓ | - | Where clue was found |
| `importance` | `number` | ✓ | 1-5 | Relevance to case (1=minor, 5=critical) |
| `related_suspects` | `string[]` | ✗ | - | Suspects connected to this clue |
| `discovered_at` | `string` | ✓ | ISO 8601 | Discovery timestamp |

**Relationships**:
- Belongs to `Investigation.discovered_clues`
- Referenced in `Accusation.evidence`

**Display Rules**:
- Sort by `importance` (descending) then `discovered_at`
- Highlight clues with `importance >= 4` in gold
- Show related suspects as clickable links

**Usage in Frontend**:
- Stored in `gameStore.clues` array (Pinia)
- Displayed in `ClueList.vue` component
- Draggable to `AccuseAction.vue` evidence panel

---

### 7. Suspect

**Purpose**: Non-player character in crime scene game

**Source**: Loaded from backend on game start (`game_started` event)

**Fields**:
| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `id` | `string` | ✓ | Unique | Suspect identifier (e.g., "suspect_butler") |
| `name` | `string` | ✓ | - | Display name (e.g., "管家 李明") |
| `description` | `string` | ✓ | - | Character background |
| `avatar_url` | `string` | ✗ | Valid URL | Character portrait |
| `available_topics` | `string[]` | ✓ | - | Questions player can ask |
| `is_guilty` | `boolean` | ✗ | - | True culprit flag (hidden until game end) |

**Relationships**:
- Has many `ClueItem` (via `related_suspects`)
- Target of `interrogate` and `accuse` actions

**Interrogation Topics**:
| Topic ID | Display Text | Example Response |
|----------|--------------|------------------|
| `alibi` | "你当时在哪里？" | "我在厨房准备晚餐" |
| `motive` | "你有作案动机吗？" | "我没有理由伤害他" |
| `relationship` | "你和受害者什么关系？" | "我为他工作了10年" |

**Usage in Frontend**:
- Stored in `gameStore.suspects` array (Pinia)
- Displayed in `SuspectPanel.vue` component
- Clicked to trigger `InterrogateAction.vue` dialog

---

### 8. Investigation

**Purpose**: Player's cumulative investigation progress

**Source**: Aggregated from `game_state.investigations[player_id]`

**Fields**:
| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `player_id` | `number` | ✓ | > 0 | Investigating player |
| `visited_locations` | `string[]` | ✓ | - | Locations already investigated |
| `discovered_clues` | `ClueItem[]` | ✓ | - | Clues found by this player |
| `interrogation_history` | `object[]` | ✓ | - | Past questions and answers |
| `reasoning_notes` | `string` | ✗ | - | Player's deduction notes (future feature) |
| `accusations_remaining` | `number` | ✓ | >= 0 | Accusation attempts left |

**Relationships**:
- Belongs to one `RegisteredPlayer`
- Has many `ClueItem`
- Has many `Accusation` attempts

**State Transitions**:
```
Empty Investigation → [investigate actions] → Clues Collected → [accuse] → Resolved
```

**Usage in Frontend**:
- Stored in `gameStore.myInvestigation` (current player)
- Displayed in `InvestigationPanel.vue` component
- Updated on every `game_state_update` event

---

### 9. Accusation

**Purpose**: Player's attempt to solve the crime

**Source**: Emitted via WebSocket `game_action` with type `accuse`

**Fields**:
| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `accused_suspect_id` | `string` | ✓ | Valid suspect ID | Accused character |
| `evidence_ids` | `string[]` | ✓ | Min 2 clues | Supporting evidence |
| `reasoning` | `string` | ✗ | Max 500 chars | Player's explanation |
| `is_correct` | `boolean` | ✗ | - | Verification result (returned by backend) |
| `timestamp` | `number` | ✓ | Unix epoch ms | Accusation time |

**Relationships**:
- References one `Suspect`
- References multiple `ClueItem`
- Belongs to one `Investigation`

**Validation Rules** (from FR-046, FR-047):
- Must provide at least 2 evidence items
- Evidence must be from `discovered_clues` (cannot fabricate)
- Only one accusation per turn (unless incorrect)
- Backend validates correctness, returns `is_correct` flag

**Result Handling**:
| `is_correct` | Frontend Behavior |
|--------------|-------------------|
| `true` | Show victory modal, end game, reveal truth |
| `false` | Decrement `accusations_remaining`, show failure toast, continue game |

**Usage in Frontend**:
- Submitted from `AccuseAction.vue` component
- Validated in `useGameActions()` composable
- Result displayed in `GameResultModal.vue`

---

## Data Flow Diagrams

### Registration Flow
```
User Input → RegisterForm.vue → api.registerPlayer()
    ↓
POST /api/v1/players/register
    ↓
{ id, username, email, ... } ← Backend
    ↓
authStore.setPlayer(registeredPlayer)
    ↓
Router.push('/lobby') + Auto-login
```

### Game Action Flow
```
User Click → ActionPanel.vue → useGameActions().submitAction()
    ↓
Optimistic UI update (gameStore.pendingAction = action)
    ↓
websocket.emit('game_action', gameAction)
    ↓
Backend processes → websocket.on('game_state_update')
    ↓
gameStore.updateState(newState) → Merge with optimistic update
    ↓
UI automatically updates (Vue reactivity)
```

### Reconnection Flow
```
Connection Lost → sessionStorage.setItem('disconnect_timestamp', Date.now())
    ↓
User Refreshes Browser → restoreSessionState()
    ↓
if (Date.now() - disconnect_timestamp < 5 minutes)
    ↓
websocket.connect() → Backend
    ↓
websocket.on('reconnect') → emit('rejoin_room', roomCode)
    ↓
Backend → websocket.emit('game_state_update', fullSnapshot)
    ↓
gameStore.replaceState(fullSnapshot) → UI synced
```

---

## Validation Summary

All models validated against:
- ✅ **FR-001 to FR-049**: All functional requirements covered
- ✅ **Constitution §III**: Type safety via JSDoc (see research.md RQ-006)
- ✅ **Backend APIs**: Matches OpenAPI contracts (to be documented in Phase 1)
- ✅ **Test-First Principle**: Each model testable in isolation (unit tests in Phase 2)

**Next Steps**: Generate API contracts (`contracts/api-rest.yaml`, `contracts/api-websocket.yaml`) to document exact request/response schemas.
