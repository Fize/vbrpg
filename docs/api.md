# API Documentation

**Base URL**: `http://localhost:8000` (development) | `https://your-domain.com` (production)

**API Version**: v1

**Protocol**: REST (HTTP) + WebSocket (Socket.IO)

## Table of Contents

1. [Authentication](#authentication)
2. [REST API Endpoints](#rest-api-endpoints)
3. [WebSocket Events](#websocket-events)
4. [Data Models](#data-models)
5. [Error Handling](#error-handling)

---

## Authentication

### Session-Based Authentication

The platform uses cookie-based sessions for authentication:

- **Cookie Name**: `vbrpg_session`
- **Cookie Attributes**: HttpOnly, SameSite=Lax, Max-Age=30 days
- **Session ID Format**: 32-character hexadecimal string

Sessions are created automatically when:
- Creating a guest account
- Registering a new account
- Logging in with existing credentials

---

## REST API Endpoints

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Health & Monitoring

#### GET `/health`

Health check endpoint.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2025-11-08T12:00:00Z",
  "version": "1.0.0"
}
```

#### GET `/metrics`

System metrics (Prometheus format).

**Response** (200 OK):
```text
# HELP active_games Number of active game sessions
# TYPE active_games gauge
active_games 42

# HELP total_players Total connected players
# TYPE total_players gauge
total_players 156
```

---

### Player Management

#### POST `/api/players/guest`

Create a new guest player account.

**Request Body**: None required

**Response** (201 Created):
```json
{
  "player_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "Guest_快乐_熊猫",
  "is_guest": true,
  "session_id": "a1b2c3d4e5f6...",
  "created_at": "2025-11-08T12:00:00Z"
}
```

**Set-Cookie Header**:
```
vbrpg_session=a1b2c3d4e5f6...; HttpOnly; SameSite=Lax; Max-Age=2592000; Path=/
```

**Error Responses**:
- `500` - Server error creating guest account

---

#### POST `/api/players/register`

Register a new player account (upgrade from guest or create new).

**Request Body**:
```json
{
  "username": "player123",
  "email": "player@example.com",
  "password": "SecurePassword123!"
}
```

**Validation Rules**:
- `username`: 3-20 characters, alphanumeric + underscore + Chinese characters
- `email`: Valid email format
- `password`: Minimum 8 characters

**Response** (201 Created):
```json
{
  "player_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "player123",
  "email": "player@example.com",
  "is_guest": false,
  "created_at": "2025-11-08T12:00:00Z"
}
```

**Error Responses**:
- `400` - Validation error (invalid username/email/password)
- `409` - Username or email already exists

---

#### GET `/api/players/me`

Get current player's profile.

**Authentication**: Required (session cookie)

**Response** (200 OK):
```json
{
  "player_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "player123",
  "email": "player@example.com",
  "is_guest": false,
  "total_games": 15,
  "total_wins": 8,
  "created_at": "2025-11-01T10:00:00Z",
  "last_seen": "2025-11-08T12:00:00Z"
}
```

**Error Responses**:
- `401` - Not authenticated

---

#### GET `/api/players/{player_id}`

Get player profile by ID.

**Path Parameters**:
- `player_id`: UUID of the player

**Response** (200 OK):
```json
{
  "player_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "player123",
  "total_games": 15,
  "total_wins": 8,
  "created_at": "2025-11-01T10:00:00Z"
}
```

**Note**: Email and sensitive data excluded from public profile

**Error Responses**:
- `404` - Player not found

---

### Game Room Management

#### POST `/api/rooms/create`

Create a new game room.

**Authentication**: Required (session cookie)

**Request Body**:
```json
{
  "max_players": 4,
  "difficulty": "medium",
  "turn_time_limit": 60,
  "use_ai_narrator": true
}
```

**Validation Rules**:
- `max_players`: 2-6
- `difficulty`: "easy" | "medium" | "hard"
- `turn_time_limit`: 30-300 seconds
- `use_ai_narrator`: boolean

**Response** (201 Created):
```json
{
  "room_id": "660e8400-e29b-41d4-a716-446655440001",
  "room_code": "ABC123",
  "creator_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "waiting",
  "max_players": 4,
  "current_players": 1,
  "difficulty": "medium",
  "turn_time_limit": 60,
  "use_ai_narrator": true,
  "created_at": "2025-11-08T12:00:00Z"
}
```

**Error Responses**:
- `400` - Invalid room configuration
- `401` - Not authenticated

---

#### POST `/api/rooms/join`

Join an existing game room.

**Authentication**: Required (session cookie)

**Request Body**:
```json
{
  "room_code": "ABC123"
}
```

**Response** (200 OK):
```json
{
  "room_id": "660e8400-e29b-41d4-a716-446655440001",
  "room_code": "ABC123",
  "status": "waiting",
  "max_players": 4,
  "current_players": 2,
  "players": [
    {
      "player_id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "player123",
      "is_creator": true
    },
    {
      "player_id": "550e8400-e29b-41d4-a716-446655440002",
      "username": "player456",
      "is_creator": false
    }
  ]
}
```

**Error Responses**:
- `400` - Invalid room code format
- `404` - Room not found
- `409` - Room is full or game already started

---

#### POST `/api/rooms/{code}/join`

Join an existing game room using the room code path parameter (Feature 002).

**Authentication**: Required (session cookie)

**Path Parameters**:
- `code`: 6-character alphanumeric room code (case-insensitive)

**Request Body**:
```json
{
  "player_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response** (200 OK):
```json
{
  "room": {
    "id": 42,
    "code": "ABC123",
    "game_type_id": 1,
    "status": "Waiting",
    "max_players": 4,
    "current_participant_count": 2,
    "owner_id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2025-11-08T12:00:00Z",
    "started_at": null,
    "completed_at": null
  },
  "participants": [
    {
      "id": 1,
      "player_id": "550e8400-e29b-41d4-a716-446655440000",
      "player_name": "Alice",
      "avatar_url": "https://example.com/avatars/alice.png",
      "participant_type": "human",
      "is_owner": true,
      "join_timestamp": "2025-11-08T12:00:00Z"
    },
    {
      "id": 2,
      "player_id": "660e9500-f30c-52e5-b827-557766551111",
      "player_name": "Bob",
      "avatar_url": null,
      "participant_type": "human",
      "is_owner": false,
      "join_timestamp": "2025-11-08T12:01:00Z"
    }
  ],
  "is_owner": false
}
```

**Error Responses**:
- `400` - Invalid room code format or duplicate join
  ```json
  {
    "error": "INVALID_ROOM_CODE",
    "message": "Room code must be 6 alphanumeric characters"
  }
  ```
  ```json
  {
    "error": "DUPLICATE_JOIN",
    "message": "Player already in this room"
  }
  ```
- `404` - Room not found
  ```json
  {
    "error": "ROOM_NOT_FOUND",
    "message": "No room exists with code ABC123"
  }
  ```
- `409` - Room is full or game already started
  ```json
  {
    "error": "ROOM_FULL",
    "message": "This room is at maximum capacity (4/4 players)"
  }
  ```
  ```json
  {
    "error": "GAME_ALREADY_STARTED",
    "message": "Cannot join room - game is already in progress"
  }
  ```

---

#### DELETE `/api/rooms/{code}/participants/{player_id}`

Leave a game room (Feature 002).

**Authentication**: Required (session cookie)

**Path Parameters**:
- `code`: 6-character alphanumeric room code
- `player_id`: UUID of the player leaving

**Behavior**:
- If the player is the owner, ownership transfers to the next earliest-joined human player
- If only AI agents remain after owner leaves, the room is dissolved
- Cannot leave while game is in progress

**Response** (204 No Content): Empty response body on success

**Error Responses**:
- `404` - Room or player not found
  ```json
  {
    "error": "ROOM_NOT_FOUND",
    "message": "No room exists with code ABC123"
  }
  ```
  ```json
  {
    "error": "PLAYER_NOT_IN_ROOM",
    "message": "Player is not a participant in this room"
  }
  ```
- `409` - Cannot leave while game is in progress
  ```json
  {
    "error": "GAME_IN_PROGRESS",
    "message": "Cannot leave room while game is active"
  }
  ```

---

#### POST `/api/rooms/{code}/ai-agents`

Add an AI agent to the room (Feature 002, owner only).

**Authentication**: Required (must be room owner)

**Path Parameters**:
- `code`: 6-character alphanumeric room code

**Request Body**:
```json
{
  "owner_player_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response** (201 Created):
```json
{
  "ai_agent": {
    "id": 3,
    "player_id": "a1b2c3d4-e5f6-4g7h-8i9j-0k1l2m3n4o5p",
    "player_name": "AI玩家1",
    "avatar_url": null,
    "participant_type": "ai",
    "is_owner": false,
    "join_timestamp": "2025-11-08T12:02:00Z"
  },
  "room_code": "ABC123"
}
```

**Error Responses**:
- `403` - Not the room owner
  ```json
  {
    "error": "NOT_ROOM_OWNER",
    "message": "Only the room owner can add AI agents"
  }
  ```
- `404` - Room not found
- `409` - Room is full or game already started
  ```json
  {
    "error": "ROOM_FULL",
    "message": "Cannot add AI agent - room is at maximum capacity"
  }
  ```
  ```json
  {
    "error": "GAME_ALREADY_STARTED",
    "message": "Cannot modify participants after game starts"
  }
  ```

---

#### DELETE `/api/rooms/{code}/ai-agents/{agent_id}`

Remove an AI agent from the room (Feature 002, owner only).

**Authentication**: Required (must be room owner)

**Path Parameters**:
- `code`: 6-character alphanumeric room code
- `agent_id`: UUID of the AI agent to remove

**Request Body**:
```json
{
  "owner_player_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response** (204 No Content): Empty response body on success

**Error Responses**:
- `403` - Not the room owner
- `404` - Room or AI agent not found
  ```json
  {
    "error": "AI_AGENT_NOT_FOUND",
    "message": "No AI agent with ID exists in this room"
  }
  ```
- `409` - Game already started

---

#### GET `/api/rooms/{room_code}`

Get room details.

**Path Parameters**:
- `room_code`: 6-character room code

**Response** (200 OK):
```json
{
  "room_id": "660e8400-e29b-41d4-a716-446655440001",
  "room_code": "ABC123",
  "status": "in_progress",
  "max_players": 4,
  "current_players": 4,
  "difficulty": "medium",
  "turn_time_limit": 60,
  "use_ai_narrator": true,
  "started_at": "2025-11-08T12:05:00Z"
}
```

**Error Responses**:
- `404` - Room not found

---

#### POST `/api/rooms/{room_code}/start`

Start the game (room creator only).

**Authentication**: Required (must be room creator)

**Path Parameters**:
- `room_code`: 6-character room code

**Response** (200 OK):
```json
{
  "room_id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "in_progress",
  "started_at": "2025-11-08T12:05:00Z",
  "game_state_id": "770e8400-e29b-41d4-a716-446655440003"
}
```

**Error Responses**:
- `403` - Not the room creator
- `409` - Not enough players (minimum 2 required)

---

## WebSocket Events

### Connection

**URL**: `ws://localhost:8000/socket.io/`

**Protocol**: Socket.IO

**Authentication**: Include session cookie in connection headers

### Client → Server Events

#### `join_room`

Join a game room WebSocket channel.

**Payload**:
```json
{
  "room_code": "ABC123"
}
```

**Server Response**: `room_joined` or `error`

---

#### `player_action`

Submit a player action during the game.

**Payload**:
```json
{
  "room_code": "ABC123",
  "action": {
    "type": "investigate",
    "location": "library",
    "details": "searching for clues"
  }
}
```

**Action Types**:
- `investigate`: Examine a location
- `question`: Ask another character
- `accuse`: Make an accusation
- `move`: Move to a new location
- `examine`: Inspect an object
- `use_item`: Use an inventory item
- `speak`: General dialogue

**Server Response**: `action_processed` or `error`

---

#### `chat_message`

Send a chat message to other players.

**Payload**:
```json
{
  "room_code": "ABC123",
  "message": "I found something interesting!"
}
```

**Server Response**: Broadcasts `chat_message` to all players in room

---

### Server → Client Events

#### `room_joined`

Confirmation of joining a room.

**Payload**:
```json
{
  "room_code": "ABC123",
  "player_id": "550e8400-e29b-41d4-a716-446655440000",
  "players": [...]
}
```

---

#### `player_joined`

Another player joined the room.

**Payload**:
```json
{
  "player_id": "550e8400-e29b-41d4-a716-446655440002",
  "username": "player456",
  "current_players": 3
}
```

---

#### `player_joined` (Feature 002 - Lobby Updates)

Broadcast when a human player joins the room lobby.

**Channel**: `lobby:{room_code}`

**Payload**:
```json
{
  "room_code": "ABC123",
  "player": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Alice",
    "avatar_url": "https://example.com/avatars/alice.png",
    "participant_type": "human",
    "is_owner": false,
    "join_timestamp": "2025-11-09T10:30:00Z"
  },
  "timestamp": "2025-11-09T10:30:00Z"
}
```

---

#### `player_left`

A player left the room.

**Payload**:
```json
{
  "player_id": "550e8400-e29b-41d4-a716-446655440002",
  "current_players": 2
}
```

---

#### `player_left` (Feature 002 - Lobby Updates)

Broadcast when a player leaves the room lobby.

**Channel**: `lobby:{room_code}`

**Payload**:
```json
{
  "room_code": "ABC123",
  "player_id": "550e8400-e29b-41d4-a716-446655440000",
  "player_name": "Alice",
  "timestamp": "2025-11-09T10:35:00Z"
}
```

---

#### `ai_agent_added` (Feature 002)

Broadcast when the room owner manually adds an AI agent.

**Channel**: `lobby:{room_code}`

**Payload**:
```json
{
  "room_code": "ABC123",
  "ai_agent": {
    "id": "a1b2c3d4-e5f6-4g7h-8i9j-0k1l2m3n4o5p",
    "name": "AI玩家1",
    "participant_type": "ai",
    "is_owner": false,
    "join_timestamp": "2025-11-09T10:32:00Z"
  },
  "added_by": "550e8400-e29b-41d4-a716-446655440000",
  "added_by_name": "Bob",
  "timestamp": "2025-11-09T10:32:00Z"
}
```

**Notes**:
- AI agents are auto-named sequentially (AI玩家1, AI玩家2, etc.)
- `is_owner` is always `false` for AI agents
- Only room owner can add AI agents

---

#### `ai_agent_removed` (Feature 002)

Broadcast when the room owner removes an AI agent.

**Channel**: `lobby:{room_code}`

**Payload**:
```json
{
  "room_code": "ABC123",
  "ai_agent_id": "a1b2c3d4-e5f6-4g7h-8i9j-0k1l2m3n4o5p",
  "ai_agent_name": "AI玩家1",
  "removed_by": "550e8400-e29b-41d4-a716-446655440000",
  "removed_by_name": "Bob",
  "timestamp": "2025-11-09T10:33:00Z"
}
```

---

#### `ownership_transferred` (Feature 002)

Broadcast when room ownership changes (owner leaves or manual transfer).

**Channel**: `lobby:{room_code}`

**Payload**:
```json
{
  "room_code": "ABC123",
  "previous_owner_id": "550e8400-e29b-41d4-a716-446655440000",
  "previous_owner_name": "Bob",
  "new_owner_id": "660e9500-f30c-52e5-b827-557766551111",
  "new_owner_name": "Charlie",
  "reason": "owner_left",
  "timestamp": "2025-11-09T10:36:00Z"
}
```

**Reason Values**:
- `owner_left` - Previous owner left the room
- `manual_transfer` - Owner manually transferred ownership

**Notes**:
- Ownership transfers to earliest-joined human player
- AI agents are never eligible to become room owners
- New owner gains AI management controls

---

#### `room_dissolved` (Feature 002)

Broadcast when the room is dissolved and no longer exists.

**Channel**: `lobby:{room_code}`

**Payload**:
```json
{
  "room_code": "ABC123",
  "reason": "no_human_players_remaining",
  "timestamp": "2025-11-09T10:37:00Z"
}
```

**Reason Values**:
- `no_human_players_remaining` - Last human player left, only AI agents remained
- `timeout` - Room inactive for extended period
- `manual_deletion` - Admin or owner manually deleted room

**Notes**:
- All connected clients are disconnected from the lobby channel
- Room cannot be rejoined (returns 404)
- Game rooms with only AI agents cannot exist

---

#### `game_started`

The game has begun.

**Payload**:
```json
{
  "room_code": "ABC123",
  "game_state_id": "770e8400-e29b-41d4-a716-446655440003",
  "current_turn_player_id": "550e8400-e29b-41d4-a716-446655440000",
  "turn_number": 1,
  "phase": "investigation"
}
```

---

#### `game_state_updated`

Game state changed after an action.

**Payload**:
```json
{
  "game_state_id": "770e8400-e29b-41d4-a716-446655440003",
  "turn_number": 5,
  "phase": "investigation",
  "current_turn_player_id": "550e8400-e29b-41d4-a716-446655440002",
  "game_data": {
    "locations": [...],
    "characters": [...],
    "clues_found": [...]
  }
}
```

---

#### `turn_timeout`

Player's turn expired.

**Payload**:
```json
{
  "player_id": "550e8400-e29b-41d4-a716-446655440000",
  "turn_number": 5
}
```

---

#### `game_completed`

Game has ended.

**Payload**:
```json
{
  "room_code": "ABC123",
  "winner_id": "550e8400-e29b-41d4-a716-446655440000",
  "winner_username": "player123",
  "final_state": {
    "solution": "Colonel Mustard in the Library with the Candlestick",
    "turns_taken": 25
  }
}
```

---

#### `player_reconnected`

A disconnected player reconnected.

**Payload**:
```json
{
  "player_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "player123"
}
```

---

#### `game_error`

Recoverable error occurred.

**Payload**:
```json
{
  "error_type": "llm_timeout",
  "message": "AI response timed out, retrying...",
  "recoverable": true,
  "timestamp": "2025-11-08T12:10:00Z"
}
```

---

#### `game_terminated`

Unrecoverable error, game terminated.

**Payload**:
```json
{
  "reason": "llm_failure",
  "message": "Unable to connect to AI service, game terminated",
  "terminated_at": "2025-11-08T12:15:00Z"
}
```

---

#### `chat_message`

Chat message from another player.

**Payload**:
```json
{
  "player_id": "550e8400-e29b-41d4-a716-446655440002",
  "username": "player456",
  "message": "Great find!",
  "timestamp": "2025-11-08T12:10:00Z"
}
```

---

## Data Models

### Player

```typescript
{
  player_id: string;         // UUID
  username: string;          // 3-20 chars, alphanumeric + _ + Chinese
  email?: string;            // Only for registered accounts
  is_guest: boolean;
  total_games: number;
  total_wins: number;
  created_at: string;        // ISO 8601
  last_seen: string;         // ISO 8601
}
```

### GameRoom

```typescript
{
  room_id: string;           // UUID
  room_code: string;         // 6-char uppercase alphanumeric
  creator_id: string;        // UUID
  status: "waiting" | "in_progress" | "completed";
  max_players: number;       // 2-6
  current_players: number;
  difficulty: "easy" | "medium" | "hard";
  turn_time_limit: number;   // seconds, 30-300
  use_ai_narrator: boolean;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}
```

### GameAction

```typescript
{
  type: "investigate" | "question" | "accuse" | "move" | "examine" | "use_item" | "speak";
  location?: string;         // For investigate, move
  target?: string;           // For question, accuse
  question?: string;         // For question
  evidence?: string;         // For accuse
  object?: string;           // For examine
  item?: string;             // For use_item
  details?: string;          // Additional context
}
```

---

## Error Handling

### Error Response Format

All API errors return:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "Additional context"
    }
  }
}
```

### HTTP Status Codes

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid input/validation error
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: Authenticated but not authorized
- `404 Not Found`: Resource doesn't exist
- `409 Conflict`: Resource conflict (e.g., username taken, room full)
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

### Common Error Codes

- `VALIDATION_ERROR`: Input validation failed
- `NOT_FOUND`: Resource not found
- `UNAUTHORIZED`: Authentication required
- `FORBIDDEN`: Insufficient permissions
- `CONFLICT`: Resource conflict
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `LLM_TIMEOUT`: AI service timeout
- `LLM_ERROR`: AI service error
- `DATABASE_ERROR`: Database operation failed

---

## Rate Limiting

Default rate limits:
- **Authentication endpoints**: 5 requests/minute per IP
- **Room creation**: 10 requests/hour per user
- **API calls**: 100 requests/minute per user
- **WebSocket messages**: 60 messages/minute per connection

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699459200
```

---

## Versioning

API versioning through URL path:
- Current: `/api/...` (implied v1)
- Future: `/api/v2/...`

Breaking changes will increment version number. Non-breaking changes (new fields, new endpoints) added to current version.

---

## Support

For API questions or issues:
- GitHub Issues: https://github.com/yourusername/vbrpg/issues
- API Docs: http://localhost:8000/docs
