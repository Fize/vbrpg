# WebSocket Events Contract

**Protocol**: Socket.IO
**Namespace**: `/game` (default namespace)
**Transport**: WebSocket with long-polling fallback

## Connection

### Client → Server: Connect

```javascript
// Automatic on socket.io-client initialization
const socket = io('http://localhost:8000', {
  withCredentials: true, // Include session cookie
  reconnection: true,
  reconnectionAttempts: 60, // 5 minutes (5 seconds between attempts)
  reconnectionDelay: 5000
});
```

**Authentication**: Session cookie from REST API login

---

## Room Management

### Client → Server: `join_room`

Join a game room to receive real-time updates.

**Payload**:
```json
{
  "room_code": "ABCD1234"
}
```

**Response** (via acknowledgment):
```json
{
  "success": true,
  "room_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Error Response**:
```json
{
  "success": false,
  "error": "Room not found",
  "code": "ROOM_NOT_FOUND"
}
```

---

### Client → Server: `leave_room`

Leave a game room and stop receiving updates.

**Payload**:
```json
{
  "room_code": "ABCD1234"
}
```

**Response**:
```json
{
  "success": true
}
```

---

## Game State Updates

### Server → Client: `player_joined`

Broadcast when a player joins the room.

**Payload**:
```json
{
  "room_code": "ABCD1234",
  "participant": {
    "id": "uuid",
    "player": {
      "id": "uuid",
      "username": "玩家小明"
    },
    "is_ai_agent": false,
    "joined_at": "2025-11-08T10:30:00Z"
  },
  "current_player_count": 3
}
```

---

### Server → Client: `player_left`

Broadcast when a player disconnects or leaves.

**Payload**:
```json
{
  "room_code": "ABCD1234",
  "participant_id": "uuid",
  "player_id": "uuid",
  "left_at": "2025-11-08T10:35:00Z",
  "reconnection_window_seconds": 300,
  "current_player_count": 2
}
```

---

### Server → Client: `player_replaced_by_ai`

Broadcast when disconnected player's grace period expires.

**Payload**:
```json
{
  "room_code": "ABCD1234",
  "replaced_player_id": "uuid",
  "ai_agent": {
    "id": "uuid",
    "is_ai_agent": true,
    "ai_personality": "cautious_investigator",
    "joined_at": "2025-11-08T10:40:00Z"
  },
  "reason": "Player reconnection timeout"
}
```

---

### Server → Client: `game_started`

Broadcast when game transitions from Waiting to In Progress.

**Payload**:
```json
{
  "room_code": "ABCD1234",
  "started_at": "2025-11-08T10:45:00Z",
  "participants": [
    {
      "id": "uuid",
      "player": {...},
      "is_ai_agent": false,
      "seat_number": 1
    },
    {
      "id": "uuid",
      "is_ai_agent": true,
      "ai_personality": "analytical_detective",
      "seat_number": 2
    }
  ],
  "initial_state": {
    "phase": "Setup",
    "current_turn": 1,
    "current_player_id": "uuid"
  }
}
```

---

### Server → Client: `game_state_update`

Broadcast game state changes (player moves, phase transitions).

**Payload**:
```json
{
  "room_code": "ABCD1234",
  "state_version": 42,
  "updated_at": "2025-11-08T10:50:00Z",
  "changes": {
    "type": "player_action",
    "player_id": "uuid",
    "action": {
      "type": "reveal_clue",
      "clue_id": "clue_001",
      "location": "library"
    }
  },
  "current_state": {
    "phase": "Investigation",
    "turn_number": 5,
    "current_turn_player_id": "uuid",
    "clues_revealed": ["clue_001", "clue_002"],
    "next_action_required": "roll_dice"
  }
}
```

---

### Server → Client: `turn_changed`

Broadcast when turn passes to next player.

**Payload**:
```json
{
  "room_code": "ABCD1234",
  "turn_number": 6,
  "current_turn_player_id": "uuid",
  "is_ai_turn": false,
  "time_limit_seconds": 120
}
```

---

## Gameplay Actions

### Client → Server: `game_action`

Submit a gameplay action.

**Payload**:
```json
{
  "room_code": "ABCD1234",
  "action": {
    "type": "move_character",
    "character_id": "detective_1",
    "from_location": "hallway",
    "to_location": "library"
  }
}
```

**Response** (via acknowledgment):
```json
{
  "success": true,
  "state_version": 43
}
```

**Error Response**:
```json
{
  "success": false,
  "error": "Invalid move: location is occupied",
  "code": "INVALID_ACTION"
}
```

---

### Server → Client: `ai_thinking`

Indicate AI agent is processing its turn.

**Payload**:
```json
{
  "room_code": "ABCD1234",
  "ai_agent_id": "uuid",
  "ai_personality": "analytical_detective",
  "estimated_duration_seconds": 5
}
```

**UI Guidance**: Display loading spinner with "AI正在思考..." message

---

### Server → Client: `ai_action`

Broadcast AI agent's completed action.

**Payload**:
```json
{
  "room_code": "ABCD1234",
  "ai_agent_id": "uuid",
  "action": {
    "type": "investigate_location",
    "location": "study",
    "reasoning": "This location has the most unchecked evidence."
  },
  "state_version": 44
}
```

---

## Game Completion

### Server → Client: `game_ended`

Broadcast when game completes.

**Payload**:
```json
{
  "room_code": "ABCD1234",
  "completed_at": "2025-11-08T11:30:00Z",
  "winner": {
    "player_id": "uuid",
    "username": "玩家小明"
  },
  "final_state": {
    "phase": "Resolution",
    "solution": {
      "killer": "Professor Plum",
      "weapon": "Candlestick",
      "location": "Library"
    }
  },
  "game_session_id": "uuid"
}
```

---

## Error Handling

### Server → Client: `game_error`

Broadcast game errors or service failures.

**Payload**:
```json
{
  "room_code": "ABCD1234",
  "error": "LLM service unavailable",
  "code": "LLM_SERVICE_ERROR",
  "severity": "critical",
  "action_required": "game_paused",
  "message": "游戏已暂停，AI服务暂时不可用。请稍候..."
}
```

**Error Codes**:
- `LLM_SERVICE_ERROR`: LLM service failure (game paused/terminated)
- `INVALID_ACTION`: Invalid game move
- `TIMEOUT`: Player action timeout
- `STATE_SYNC_ERROR`: State synchronization issue

---

### Server → Client: `game_terminated`

Broadcast when game is forcefully terminated.

**Payload**:
```json
{
  "room_code": "ABCD1234",
  "reason": "LLM service unavailable for 2 minutes",
  "terminated_at": "2025-11-08T11:00:00Z",
  "partial_game_session_id": "uuid"
}
```

---

## Connection State

### Server → Client: `reconnected`

Sent after successful reconnection within 5-minute window.

**Payload**:
```json
{
  "player_id": "uuid",
  "reconnected_at": "2025-11-08T10:38:00Z",
  "active_rooms": ["ABCD1234"],
  "message": "欢迎回来！正在重新同步游戏状态..."
}
```

**Behavior**: Server sends full state update after reconnection

---

### Server → Client: `connection_state`

Periodic connection health check.

**Payload**:
```json
{
  "status": "connected",
  "latency_ms": 45,
  "server_time": "2025-11-08T11:00:00Z"
}
```

**Frequency**: Every 30 seconds (heartbeat)

---

## Client-Side Event Handling Example

```javascript
import { io } from 'socket.io-client';

const socket = io('http://localhost:8000', {
  withCredentials: true,
  reconnection: true,
  reconnectionAttempts: 60,
  reconnectionDelay: 5000
});

// Connection events
socket.on('connect', () => {
  console.log('Connected to game server');
});

socket.on('disconnect', (reason) => {
  console.warn('Disconnected:', reason);
  // Show reconnection UI
});

// Join room
socket.emit('join_room', { room_code: 'ABCD1234' }, (response) => {
  if (response.success) {
    console.log('Joined room:', response.room_id);
  } else {
    console.error('Failed to join:', response.error);
  }
});

// Game state updates
socket.on('game_state_update', (data) => {
  // Update Vue store with new state
  gameStore.updateState(data.current_state);
});

socket.on('player_joined', (data) => {
  gameStore.addParticipant(data.participant);
  showNotification(`${data.participant.player.username} 加入了游戏`);
});

socket.on('ai_thinking', (data) => {
  gameStore.setAIThinking(data.ai_agent_id, true);
});

socket.on('ai_action', (data) => {
  gameStore.setAIThinking(data.ai_agent_id, false);
  gameStore.applyAction(data.action);
  showAIActionMessage(data.action.reasoning);
});

// Player actions
function makeMove(action) {
  socket.emit('game_action', {
    room_code: currentRoom.value,
    action
  }, (response) => {
    if (!response.success) {
      showError(response.error);
    }
  });
}

// Error handling
socket.on('game_error', (data) => {
  if (data.severity === 'critical') {
    showCriticalError(data.message);
    if (data.action_required === 'game_paused') {
      gameStore.pauseGame();
    }
  }
});

socket.on('game_terminated', (data) => {
  showGameTerminatedDialog(data.reason);
  router.push('/');
});
```

---

## Server-Side Socket.IO Setup Example

```python
from socketio import AsyncServer
from fastapi import FastAPI

# Initialize Socket.IO server
sio = AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',  # Configure for production
    logger=True,
    engineio_logger=True
)

# Attach to FastAPI app
app = FastAPI()
socket_app = socketio.ASGIApp(sio, app)

# Event handlers
@sio.event
async def join_room(sid, data):
    room_code = data['room_code']
    
    # Validate room exists and player is authenticated
    room = await get_room(room_code)
    if not room:
        return {'success': False, 'error': 'Room not found', 'code': 'ROOM_NOT_FOUND'}
    
    # Join Socket.IO room
    await sio.enter_room(sid, room_code)
    
    # Broadcast to other players
    await sio.emit('player_joined', {
        'room_code': room_code,
        'participant': participant_data,
        'current_player_count': room.participant_count
    }, room=room_code, skip_sid=sid)
    
    return {'success': True, 'room_id': str(room.id)}

@sio.event
async def game_action(sid, data):
    room_code = data['room_code']
    action = data['action']
    
    # Validate and apply action
    try:
        new_state = await game_service.apply_action(room_code, action)
        
        # Broadcast state update to all players
        await sio.emit('game_state_update', {
            'room_code': room_code,
            'state_version': new_state.version,
            'updated_at': new_state.updated_at.isoformat(),
            'changes': {'type': 'player_action', 'action': action},
            'current_state': new_state.to_dict()
        }, room=room_code)
        
        return {'success': True, 'state_version': new_state.version}
    
    except InvalidActionError as e:
        return {'success': False, 'error': str(e), 'code': 'INVALID_ACTION'}
```

---

## Event Flow Diagrams

### Game Start Flow
```
Player A creates room → [REST: POST /rooms]
Player A joins via WS → [WS: join_room]
Player B joins via WS → [WS: join_room]
  └→ [WS: player_joined] → Broadcast to room
AI agents fill slots → [WS: player_joined] → Broadcast × N
Player A starts game → [REST: POST /rooms/{code}/start]
  └→ [WS: game_started] → Broadcast to room
```

### Turn Flow
```
[WS: turn_changed] → Broadcast current turn player
Player makes move → [WS: game_action]
  └→ Validate action
  └→ Update state
  └→ [WS: game_state_update] → Broadcast
  └→ [WS: turn_changed] → Next player
```

### AI Turn Flow
```
[WS: turn_changed] → AI agent's turn
[WS: ai_thinking] → Broadcast AI processing
  └→ Call LLM service (timeout: 10s)
  └→ If success: [WS: ai_action] → Broadcast
  └→ If timeout: [WS: game_error] → Broadcast
  └→ If critical: [WS: game_terminated] → Broadcast
```

### Disconnection Flow
```
Player disconnects → Socket.IO detects
  └→ [WS: player_left] → Broadcast (with reconnection window)
  └→ Start 5-minute timer
If reconnects within 5 min:
  └→ [WS: reconnected] → Send to player
  └→ Sync full state
If timeout expires:
  └→ Create AI agent
  └→ [WS: player_replaced_by_ai] → Broadcast
```

---

## Testing WebSocket Events

### Unit Tests (pytest)
```python
import pytest
from socketio import AsyncClient

@pytest.mark.asyncio
async def test_join_room():
    sio = AsyncClient()
    await sio.connect('http://localhost:8000')
    
    response = await sio.emit('join_room', {
        'room_code': 'TEST1234'
    }, callback=True)
    
    assert response['success'] == True
    await sio.disconnect()
```

### E2E Tests (Playwright)
```javascript
test('multiplayer game flow', async ({ page, context }) => {
  // Create second page for Player 2
  const page2 = await context.newPage();
  
  // Player 1 creates room
  await page.goto('/games/crime-scene');
  await page.click('button:has-text("创建游戏")');
  const roomCode = await page.locator('.room-code').textContent();
  
  // Player 2 joins
  await page2.goto(`/rooms/${roomCode}`);
  
  // Wait for player joined event
  await page.waitForSelector('.player-list .player-item:nth-child(2)');
  
  // Verify both players see each other
  await expect(page.locator('.player-list')).toContainText('Player 2');
  await expect(page2.locator('.player-list')).toContainText('Player 1');
});
```

---

## Summary

**Total Events**: 15 events (7 client→server, 8 server→client)
**Primary Patterns**: Request-response (with acknowledgments), Broadcast to room
**State Management**: Server authoritative, optimistic client updates
**Error Handling**: Graceful degradation with user feedback
**Reconnection**: Automatic with 5-minute window

**Next Step**: Create quickstart guide for developers.
