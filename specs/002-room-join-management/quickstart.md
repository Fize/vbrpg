# Quick Start: Multiplayer Room Join & AI Agent Management

**Feature**: 002-room-join-management  
**Date**: 2025-11-09  
**Target Audience**: Developers implementing this feature

## Prerequisites

- Feature 001-ai-game-platform fully implemented and working
- Backend server running on http://localhost:8000
- Frontend dev server running on http://localhost:5173
- Database migrated to latest version
- At least one game type configured (e.g., Crime Scene)

## Setup Instructions

### 1. Database Migration

Run the Alembic migration to add lobby management columns:

```bash
cd backend
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows

# Create and run migration
alembic revision --autogenerate -m "add_lobby_management_columns"
alembic upgrade head

# Verify schema
sqlite3 data/vbrpg.db ".schema game_rooms"
sqlite3 data/vbrpg.db ".schema game_room_participants"
```

**Expected new columns**:
- `game_rooms`: `owner_id`, `current_participant_count`, `ai_agent_counter`
- `game_room_participants`: `is_owner`, `join_timestamp`

### 2. Backend Implementation

Install dependencies (if not already installed):

```bash
cd backend
pip install -r requirements.txt
```

Run backend server:

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Verify new endpoints:
- Visit http://localhost:8000/docs
- Check for new endpoints:
  - `POST /api/v1/rooms/{code}/join`
  - `DELETE /api/v1/rooms/{code}/participants/{player_id}`
  - `POST /api/v1/rooms/{code}/ai-agents`
  - `DELETE /api/v1/rooms/{code}/ai-agents/{agent_id}`

### 3. Frontend Implementation

Install dependencies:

```bash
cd frontend
npm install
```

Run frontend dev server:

```bash
npm run dev
```

Open http://localhost:5173 in your browser.

## Testing the Feature

### Manual Testing Flow

#### Test 1: Join Room (Happy Path)

1. **Player A** (Browser 1):
   ```
   - Open http://localhost:5173
   - Click "Create Game"
   - Select game type: "Crime Scene"
   - Set max players: 4
   - Click "Create Room"
   - Note the 6-character room code displayed (e.g., "ABC123")
   ```

2. **Player B** (Browser 2 / Incognito):
   ```
   - Open http://localhost:5173
   - Click "Join Game"
   - Enter room code: "ABC123"
   - Click "Join"
   - Verify: You see Player A in the lobby
   - Verify: Player A sees you join (real-time update)
   ```

3. **Verification**:
   - Both players see each other in participant list
   - Player A has "Owner" badge
   - Participant count shows "2/4"

#### Test 2: AI Agent Management

1. **Player A** (Room Owner):
   ```
   - In lobby, click "Add AI Agent" button
   - Verify: "AI玩家1" appears in participant list with AI icon
   - Verify: Player B sees AI agent appear instantly
   - Click "Add AI Agent" again
   - Verify: "AI玩家2" appears
   - Click "Remove" on "AI玩家1"
   - Verify: AI玩家1 disappears, AI玩家2 remains
   ```

2. **Player B** (Not Owner):
   ```
   - Verify: You do NOT see "Add AI Agent" button (owner-only)
   - Verify: You see all AI agent add/remove actions in real-time
   ```

#### Test 3: Room Full Scenario

1. **Players A, B, C, D** (4 players, max capacity):
   ```
   - Player A creates room (max 4)
   - Players B, C, D successfully join
   - Participant count: "4/4"
   ```

2. **Player E** tries to join:
   ```
   - Enter same room code
   - Click "Join"
   - Verify: Error message "Room is full (4/4 players)"
   - Verify: Player E is NOT added to participant list
   ```

#### Test 4: Ownership Transfer

1. **Setup** (Room with Player A (owner), Player B, AI玩家1):
   ```
   - Player A creates room
   - Player B joins
   - Player A adds AI agent
   - Current owner: Player A
   ```

2. **Player A leaves**:
   ```
   - Player A clicks "Leave Room"
   - Verify: Player A returns to main screen
   ```

3. **Player B sees**:
   ```
   - Player A disappears from list
   - Notification: "You are now the room owner"
   - "Add AI Agent" button appears (now has owner permissions)
   - Participant count: "2/4" (Player B + AI玩家1)
   ```

#### Test 5: Room Dissolution

1. **Setup** (Room with Player A (owner), AI玩家1, AI玩家2):
   ```
   - Player A creates room
   - Player A adds 2 AI agents
   - No other human players
   ```

2. **Player A leaves**:
   ```
   - Player A clicks "Leave Room"
   - Verify: Room is deleted from database
   - Verify: Attempting to join with room code shows "Room not found"
   ```

#### Test 6: Concurrent Join (Race Condition)

1. **Setup** (Room with 3/4 players):
   ```
   - Player A creates room (max 4)
   - Players B, C join
   - 1 slot remaining
   ```

2. **Players D and E join simultaneously**:
   ```
   - On exact same second, both click "Join" with same room code
   - Expected: One succeeds, one gets "Room is full" error
   - Verify: Final participant count is 4/4 (not 5/4)
   - Verify: Database has exactly 4 participants for this room
   ```

#### Test 7: Disconnection & Rejoin

1. **Player B in lobby**:
   ```
   - Close browser tab / kill browser process
   - Verify: Player A sees "Player B left the room"
   - Verify: Participant count decreases
   ```

2. **Player B rejoins**:
   ```
   - Open browser, go to http://localhost:5173
   - Click "Join Game", enter same room code
   - Verify: Successfully rejoins (treated as new join)
   - Verify: join_timestamp is updated to new time
   ```

### Automated Testing

Run backend tests:

```bash
cd backend
pytest tests/unit/test_game_room_service.py -v
pytest tests/integration/test_rooms_api.py -v
pytest tests/integration/test_lobby_websocket.py -v
pytest tests/contract/test_lobby_contracts.py -v
```

Run frontend tests:

```bash
cd frontend
npm run test:unit
npm run test:e2e
```

### API Testing with cURL

**Join Room**:
```bash
curl -X POST http://localhost:8000/api/v1/rooms/ABC123/join \
  -H "Content-Type: application/json" \
  -d '{"player_id": "550e8400-e29b-41d4-a716-446655440000"}'
```

**Leave Room**:
```bash
curl -X DELETE http://localhost:8000/api/v1/rooms/ABC123/participants/550e8400-e29b-41d4-a716-446655440000
```

**Add AI Agent** (requires owner authentication):
```bash
curl -X POST http://localhost:8000/api/v1/rooms/ABC123/ai-agents \
  -H "Content-Type: application/json" \
  -d '{"owner_player_id": "550e8400-e29b-41d4-a716-446655440000"}'
```

**Remove AI Agent**:
```bash
curl -X DELETE http://localhost:8000/api/v1/rooms/ABC123/ai-agents/a1b2c3d4-e5f6-4g7h-8i9j-0k1l2m3n4o5p \
  -H "Content-Type: application/json" \
  -d '{"owner_player_id": "550e8400-e29b-41d4-a716-446655440000"}'
```

### WebSocket Event Testing

Use browser console to monitor events:

```javascript
// Open browser DevTools Console on http://localhost:5173

// Join room (replace with actual room code)
const socket = io('http://localhost:8000')
socket.emit('join_lobby', {room_code: 'ABC123'})

// Listen to events
socket.on('player_joined', (data) => {
  console.log('Player joined:', data)
})

socket.on('ai_agent_added', (data) => {
  console.log('AI agent added:', data)
})

socket.on('ownership_transferred', (data) => {
  console.log('Ownership transferred:', data)
})
```

## Troubleshooting

### Issue: "Room not found" error when joining

**Possible causes**:
- Room code typo (case-sensitive: "abc123" vs "ABC123")
- Room already dissolved
- Database connection issue

**Debug**:
```bash
sqlite3 data/vbrpg.db "SELECT * FROM game_rooms WHERE code='ABC123';"
```

### Issue: AI agent not appearing in list

**Possible causes**:
- Not room owner (permission denied)
- Room full
- WebSocket disconnected

**Debug**:
- Check browser console for errors
- Verify WebSocket connection: `socket.connected` should be `true`
- Check backend logs for emit errors

### Issue: Ownership not transferring

**Possible causes**:
- No other human players in room (room dissolved instead)
- join_timestamp not set correctly

**Debug**:
```bash
sqlite3 data/vbrpg.db "SELECT player_id, participant_type, is_owner, join_timestamp FROM game_room_participants WHERE room_id=(SELECT id FROM game_rooms WHERE code='ABC123');"
```

### Issue: Concurrent join both succeed (race condition)

**Possible causes**:
- Database transaction isolation not working
- WAL mode not enabled on SQLite

**Debug**:
```bash
sqlite3 data/vbrpg.db "PRAGMA journal_mode;"
# Should return: wal

sqlite3 data/vbrpg.db "SELECT current_participant_count, max_players FROM game_rooms WHERE code='ABC123';"
# If current > max, race condition occurred
```

## Performance Validation

### Lobby Update Latency

Measure time from action to UI update:

```javascript
// In browser console
const start = performance.now()
socket.emit('add_ai_agent', {room_code: 'ABC123', owner_player_id: 'xxx'})
socket.once('ai_agent_added', () => {
  const latency = performance.now() - start
  console.log(`Latency: ${latency}ms`)  // Should be < 1000ms
})
```

### Concurrent Room Load

Test with 50 concurrent rooms:

```bash
cd backend
pytest tests/load/test_concurrent_lobbies.py -v
```

Expected: No errors, all operations < 5 seconds

## Success Criteria Checklist

- [ ] Players can join rooms using 6-character codes
- [ ] Join operations complete in < 5 seconds
- [ ] Room full errors displayed correctly
- [ ] Owner can add AI agents (< 3 seconds)
- [ ] Owner can remove AI agents
- [ ] Non-owners cannot manage AI agents
- [ ] Real-time updates appear within 1 second
- [ ] Ownership transfers when owner leaves
- [ ] Room dissolves when only AI remain
- [ ] Concurrent joins resolve without race conditions
- [ ] Disconnected players can rejoin if space available
- [ ] All WebSocket events broadcast correctly
- [ ] Database migrations run without errors
- [ ] Test coverage ≥ 53%

## Next Steps

After this feature is complete and tested:
1. Run `/speckit.tasks` to generate task breakdown
2. Begin Phase 2 implementation (TDD cycle)
3. Monitor performance metrics in production
4. Gather user feedback on lobby UX
